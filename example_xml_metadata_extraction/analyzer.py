#!/usr/bin/env python

"""
Voicemail transcription analysis system for apartment management communications.

This module provides functionality to analyze transcribed voicemail messages using
natural language processing to extract key insights including:
- Sentiment analysis
- Message categorization
- Urgency assessment
- Caller type classification
- Language detection
"""

import os
import sys
import re
import tempfile
import uuid
import datetime
import logging
import xml.etree.ElementTree as ET
from collections import defaultdict
import traceback
import time
import argparse
import signal
from pathlib import Path
import mysql.connector
from mysql.connector import Error as MySqlError
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
from contextlib import contextmanager
from typing import Any
from collections.abc import Generator
from dotenv import find_dotenv, load_dotenv

from lwe.core.config import Config
from lwe.backends.api.backend import ApiBackend

from .constants import (
    DEFAULT_DATABASE_HOST,
    DEFAULT_DATABASE_PORT,
    DEFAULT_DATABASE_NAME,
    ANALYSIZER_TEMPLATE,
    BACKUP_PRESET,
    COMMA_SEPARATED_HEADERS,
    EXCLUDED_RECORD_IDS,
    BATCH_SIZE,
)

load_dotenv(find_dotenv(usecwd=True))
from .config import set_environment_variables
from .logger import Logger


class ParserError(ValueError):
    pass


class AnalyzerError(RuntimeError):
    pass


class MysqlDataError(MySqlError):
    """Custom exception for MySQL data validation errors (like invalid enum values)."""
    pass


def check_mysql_data_error(error: MySqlError) -> None:
    """
    Check if a MySQL error is a data validation error and raise MysqlDataError if it is.

    :param error: The MySQL error to check
    :type error: MySqlError
    :raises MysqlDataError: If the error is a data validation error (invalid enum value)
    """
    if error.errno == 1265:  # Data truncated error (invalid enum value)
        raise MysqlDataError(str(error))
    # Let other MySQL errors pass through unchanged
    raise error


@contextmanager
def db_connection(
    host: str, port: int, database: str, username: str, password: str
) -> Generator[PooledMySQLConnection | MySQLConnectionAbstract, None, None]:
    """
    Create and manage a MySQL database connection using context manager.

    :param host: Database server hostname
    :type host: str
    :param port: Database server port
    :type port: int
    :param database: Name of the database to connect to
    :type database: str
    :param username: Database user username
    :type username: str
    :param password: Database user password
    :type password: str
    :return: MySQL connection object
    :raises MySqlError: If connection cannot be established
    """
    conn = mysql.connector.connect(
        host=host,
        port=port,
        database=database,
        user=username,
        password=password,
        connect_timeout=120,
    )
    try:
        yield conn
    finally:
        if conn.is_connected():
            _ = conn.close()


class VoicemailAnalyzer:
    def __init__(self, args: argparse.Namespace) -> None:
        """
        Initialize the VoicemailAnalyzer with command line arguments.

        :param args: Parsed command line arguments
        :type args: argparse.Namespace
        :return: None
        :rtype: None
        """
        self.debug: bool = args.debug
        self.log: logging.Logger = Logger(self.__class__.__name__, debug=self.debug)
        self.host: str = args.host
        self.port: int = args.port
        self.database: str = args.database
        self.username: str = args.username
        self.password: str = args.password
        self.template: str = args.template
        self.logfile: str | None = args.logfile
        self.limit: int = args.limit
        self.pause: float = args.pause
        self.continuous: int | None = args.continuous
        self.failed_analysis_count: int = 0
        self.running: bool = False
        set_environment_variables()
        self.analyzer: ApiBackend = self._initialize_lwe_backend()

    def _initialize_lwe_backend(self) -> ApiBackend:
        """
        Initialize a new LWE backend instance with configuration.

        :return: Configured ApiBackend instance
        :rtype: ApiBackend
        :raises ValueError: If required environment variables are missing
        """
        config_args = {}
        config_dir = os.environ.get("LWE_CONFIG_DIR")
        data_dir = os.environ.get("LWE_DATA_DIR")
        if config_dir:
            config_args["config_dir"] = config_dir
        if data_dir:
            config_args["data_dir"] = data_dir

        self.log.debug(f"Initializing LWE backend with config args: {config_args}")
        config = Config(**config_args)
        config.load_from_file()
        if self.debug:
            config.set("debug.log.enabled", True)
            config.set("debug.log.filepath", "%s/%s" % (tempfile.gettempdir(), "lwe-analyzer-debug.log"))
        backend = ApiBackend(config)
        self.log.debug("LWE backend initialization complete")
        return backend

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    def load_transcriptions(self, batch_size: int) -> list[tuple[int, int, str]]:
        """
        Load a batch of unprocessed transcriptions from the database.

        :param batch_size: Number of transcriptions to load
        :type batch_size: int
        :return: List of tuples containing (id, record_id, transcription)
        :rtype: list[tuple[int, int, str]]
        :raises MySqlError: If database connection or query fails
        """
        with db_connection(
            self.host, self.port, self.database, self.username, self.password
        ) as conn:
            cursor = conn.cursor(buffered=False)
            excluded_ids_placeholder = ", ".join(["%s"] * len(EXCLUDED_RECORD_IDS))
            query = f"""
                SELECT id, record_id, transcription
                FROM apartmentlines.transcriptions
                WHERE context = 'voicemail'
                AND id NOT IN (SELECT DISTINCT transcription_id FROM voicemail_analysis_failed_analysis)
                AND id NOT IN (SELECT DISTINCT transcription_id FROM voicemail_analysis_transcription_categories)
                AND id NOT IN (SELECT DISTINCT transcription_id FROM voicemail_analysis_transcription_categories)
                AND record_id NOT IN ({ excluded_ids_placeholder })
                AND transcription IS NOT NULL
                AND transcription != ''
                ORDER BY id
                LIMIT %s;
            """
            params = (*EXCLUDED_RECORD_IDS, batch_size)
            _ = cursor.execute(query, params)
            return cursor.fetchall()  # pyright: ignore[reportReturnType]

    def analyze_transcriptions(self, batch_size: int, pause: float) -> int:
        """
        Process a batch of transcriptions with sentiment and category analysis.

        :param batch_size: Number of transcriptions to process
        :type batch_size: int
        :param pause: Seconds to pause between processing each transcription
        :type pause: float
        :return: Number of transcriptions processed
        :rtype: int
        """
        processed = 0
        transcriptions = self.load_transcriptions(batch_size)
        for id, record_id, transcription in transcriptions:
            if not self.running:
                break
            self.process_transcription_try(id, record_id, transcription)
            processed += 1
            if pause > 0:
                self.log.info(f"Pausing for {pause} seconds")
                time.sleep(pause)
        return processed

    def process_transcription_try(
        self, id: int, record_id: int, transcription: str
    ) -> dict[str, Any] | None:
        """
        Process a single transcription through the analysis pipeline.

        :param id: Transcription ID
        :type id: int
        :param record_id: Record ID
        :type record_id: int
        :param transcription: Text content of the transcription
        :type transcription: str
        """
        try:
            results = self.process_transcription(id, transcription)
            self.insert_analysis(id, record_id, results)
        except RetryError as e:
            if isinstance(e.last_attempt.exception(), (ParserError, AnalyzerError, MysqlDataError)):
                self.log.error(f"Analysis failed after {self.failed_analysis_count} retries for transcription {id}. Original error: {e.last_attempt.exception()}")
                self.add_failed_analysis(id)
            else:
                raise

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(5))
    def process_transcription(
        self, id: int, transcription: str
    ) -> dict[str, Any] | None:
        """
        Process a single transcription through the analysis pipeline.

        :param id: Transcription ID from database
        :type id: int
        :param transcription: Text content of the transcription
        :type transcription: str
        :return: Dictionary containing analysis results
        :rtype: dict[str, Any]
        :raises ParserError: If analysis response cannot be parsed
        :raises AnalyzerError: If analysis fails
        :raises MysqlDataError: If database data insertion fails
        """
        try:
            response = self.perform_analysis(id, transcription)
            parsed_results = self.parse_analysis(response)
            self.log_analysis(id, transcription, parsed_results)
            self.failed_analysis_count = 0
            return parsed_results
        except (ParserError, AnalyzerError, MysqlDataError) as e:
            self.failed_analysis_count += 1
            self.log.error(f"Error processing transcription {id}: {e}")
            _ = traceback.format_exc()
            raise

    def add_failed_analysis(self, transcription_id: int) -> None:
        """
        Mark a transcription as having failed analysis.

        :param transcription_id: Transcription ID from database
        :type transcription_id: int
        """
        self.log.warning(f"Marking transcription {transcription_id} as having failed analysis")
        with db_connection(
            self.host, self.port, self.database, self.username, self.password
        ) as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("INSERT IGNORE INTO voicemail_analysis_failed_analysis (transcription_id) VALUES (%s)", (transcription_id,))
                conn.commit()
                self.log.debug(f"Successfully marked transcription {transcription_id} as failed")
            except MySqlError as e:
                conn.rollback()
                self.log.error(f"Failed to mark transcription {transcription_id} as failed: {e}")
                raise

    def log_analysis(
        self, id: int, transcription: str, results: dict[str, Any]
    ) -> None:
        """
        Log the analysis results to a file if logging is enabled.

        :param id: Transcription ID from database
        :type id: int
        :param transcription: Original transcription text
        :type transcription: str
        :param results: Dictionary containing analysis results
        :type results: dict[str, Any]
        :return: None
        :rtype: None
        """
        if self.logfile:
            self.log.debug(f"Logging analysis for transcription {id} to {self.logfile}")
            reasoning = results.get("reasoning", "")
            sentiments = ", ".join(results.get("sentiments", []))
            categories = ", ".join(results.get("categories", []))
            urgency = results.get("urgency", "")
            caller_type = results.get("caller_type", "")
            language = results.get("language", "")
            with Path(self.logfile).open("a") as f:
                output = f"""
###############################################################################
ID: {id}

Transcription:
{transcription}

Reasoning:
{reasoning}

Sentiments: {sentiments}
Categories: {categories}
Urgency: {urgency}
Caller type: {caller_type}
Language: {language}
###############################################################################
"""
                _ = f.write(output)

    def perform_analysis(self, id: int, transcription: str) -> str:
        """
        Run the analysis template on a transcription.

        :param id: Transcription ID from database
        :type id: int
        :param transcription: Text content to analyze
        :type transcription: str
        :return: Raw analysis response text
        :rtype: str
        :raises AnalyzerError: If template execution fails
        """
        identifier = uuid.uuid4().hex[:8]
        template_vars = {"transcription": transcription, "identifier": identifier}
        overrides = None
        if self.failed_analysis_count > 1:
            self.log.warning(
                f"Too many failed analysis attempts ({self.failed_analysis_count}) for transcription {id} with default preset, trying backup preset {BACKUP_PRESET}"
            )
            overrides = {
                "request_overrides": {
                    "preset": BACKUP_PRESET,
                },
            }
        success, response, user_message = self.analyzer.run_template(
            self.template, template_vars=template_vars, overrides=overrides
        )
        if not success:
            raise AnalyzerError(
                f"Error running template {self.template}: {user_message}"
            )
        self.log.debug(f"Analysis result: {response}")
        return response

    def escape_xml_content(self, xml_content: str) -> str:
        """
        Escape XML content by wrapping text in CDATA sections.

        :param xml_content: Raw XML content to escape
        :type xml_content: str
        :return: Escaped XML content with CDATA sections
        :rtype: str
        """

        def replace_text(match):
            tag = match.group(1)
            text = match.group(2)
            return f"<{tag}><![CDATA[{text}]]></{tag}>"

        escaped_content = re.sub(
            r"<([^>]+)>(.*?)</\1>", replace_text, xml_content, flags=re.DOTALL
        )
        return escaped_content

    def parse_analysis(self, text: str) -> dict[str, Any]:
        """
        Parse the analysis response text into a structured dictionary.

        :param text: Raw analysis response text containing XML
        :type text: str
        :return: Dictionary of parsed analysis results
        :rtype: dict[str, Any]
        :raises ParserError: If XML parsing fails or required sections are missing
        """
        headers_match = re.search(r"<analysis>(.*?)</analysis>", text, re.DOTALL)
        if not headers_match:
            raise ParserError("No analysis section found in the text")
        xml_content = headers_match.group(1).strip()
        self.log.debug(f"Original XML content: {xml_content}")
        escaped_content = self.escape_xml_content(xml_content)
        self.log.debug(f"Escaped XML content: {escaped_content}")
        wrapped_content = f"<analysis>{escaped_content}</analysis>"
        try:
            root = ET.fromstring(wrapped_content)
        except ET.ParseError as e:
            raise ParserError(f"Error parsing analysis XML: {e}")
        headers_dict = defaultdict(list)
        for child in root:
            key_lower = child.tag.lower().replace("-", "_")
            value = child.text.strip() if child.text else ""
            if value:
                if key_lower in COMMA_SEPARATED_HEADERS:
                    headers_dict[key_lower] = [
                        item.lower().strip() for item in value.split(",")
                    ]
                else:
                    headers_dict[key_lower] = value
        self.log.debug(f"Parsed headers: {headers_dict}")
        return dict(headers_dict)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    def insert_analysis(
        self, transcription_id: int, record_id: int, results: dict[str, Any]
    ) -> None:
        """
        Insert analysis results into the database for a transcription.

        :param transcription_id: ID of the transcription being analyzed
        :type transcription_id: int
        :param record_id: Associated record ID
        :type record_id: int
        :param results: Dictionary containing analysis results
        :type results: dict[str, Any]
        :return: None
        :rtype: None
        :raises MySqlError: If database operations fail
        """
        sentiments = results.get("sentiments", [])
        categories = results.get("categories", [])
        urgency = results.get("urgency", "")
        caller_type = results.get("caller_type", "")
        language = results.get("language", "")
        with db_connection(
            self.host, self.port, self.database, self.username, self.password
        ) as conn:
            try:
                _ = conn.start_transaction()
                if sentiments:
                    self.insert_sentiments(conn, transcription_id, sentiments)
                if categories:
                    self.insert_categories(conn, transcription_id, categories)
                if urgency:
                    self.insert_urgency(conn, transcription_id, urgency)
                if caller_type:
                    self.insert_caller_type(conn, transcription_id, caller_type)
                if language:
                    self.insert_language(conn, transcription_id, language)
                _ = conn.commit()
                self.log.info(
                    f"Transaction committed for record_id: {record_id} and transcription_id: {transcription_id}"
                )
            except MySqlError as e:
                traceback.print_exc()
                try:
                    _ = conn.rollback()
                    self.log.error(
                        f"Transaction rolled back for transcription_id: {transcription_id} due to error: {e}"
                    )
                except MySqlError as rollback_error:
                    traceback.print_exc()
                    self.log.error(
                        f"Failed to rollback transaction for transcription_id: {transcription_id} due to error: {rollback_error}"
                    )
                    raise
                raise

    def insert_sentiments(
        self,
        conn: PooledMySQLConnection | MySQLConnectionAbstract,
        transcription_id: int,
        sentiments: list[str],
    ) -> None:
        """
        Insert sentiment analysis results into the database.

        :param conn: Active database connection
        :type conn: mysql.connector.MySQLConnection
        :param transcription_id: ID of the transcription
        :type transcription_id: int
        :param sentiments: List of sentiment labels
        :type sentiments: list[str]
        :return: None
        :rtype: None
        :raises MySqlError: If database operations fail
        """
        try:
            with conn.cursor() as cursor:
                sentiments = set(sentiments)
                cursor.executemany(
                    "INSERT IGNORE INTO voicemail_analysis_sentiments (sentiment) VALUES (%s)",
                    [(sentiment,) for sentiment in sentiments],
                )
                cursor.execute(
                    f"SELECT id, sentiment FROM voicemail_analysis_sentiments WHERE sentiment IN ({','.join(['%s'] * len(sentiments))})",
                    tuple(sentiments),
                )
                sentiment_id_map = {
                    sentiment: id for id, sentiment in cursor.fetchall()
                }
                cursor.executemany(
                    "INSERT INTO voicemail_analysis_transcription_sentiments (transcription_id, sentiment_id) VALUES (%s, %s)",
                    [
                        (transcription_id, sentiment_id_map[sentiment])
                        for sentiment in sentiments
                    ],
                )
            self.log.info(
                f"Inserted sentiments: {sentiments} for transcription_id: {transcription_id}"
            )
        except MySqlError as e:
            traceback.print_exc()
            self.log.error(
                f"Error inserting sentiments for transcription_id {transcription_id}, sentiments {sentiments}: {e}"
            )
            raise

    def insert_categories(
        self,
        conn: PooledMySQLConnection | MySQLConnectionAbstract,
        transcription_id: int,
        categories: list[str],
    ) -> None:
        """
        Insert category classifications into the database.

        :param conn: Active database connection
        :type conn: mysql.connector.MySQLConnection
        :param transcription_id: ID of the transcription
        :type transcription_id: int
        :param categories: List of category labels
        :type categories: list[str]
        :return: None
        :rtype: None
        :raises MySqlError: If database operations fail
        """
        try:
            with conn.cursor() as cursor:
                categories = set(categories)
                cursor.executemany(
                    "INSERT IGNORE INTO voicemail_analysis_categories (category) VALUES (%s)",
                    [(category,) for category in categories],
                )
                cursor.execute(
                    f"SELECT id, category FROM voicemail_analysis_categories WHERE category IN ({','.join(['%s'] * len(categories))})",
                    tuple(categories),
                )
                category_id_map = {category: id for id, category in cursor.fetchall()}
                cursor.executemany(
                    "INSERT INTO voicemail_analysis_transcription_categories (transcription_id, category_id) VALUES (%s, %s)",
                    [
                        (transcription_id, category_id_map[category])
                        for category in categories
                    ],
                )
            self.log.info(
                f"Inserted categories: {categories} for transcription_id: {transcription_id}"
            )
        except MySqlError as e:
            traceback.print_exc()
            self.log.error(
                f"Error inserting categories for transcription_id {transcription_id}, categories {categories}: {e}"
            )
            raise

    def insert_urgency(
        self,
        conn: PooledMySQLConnection | MySQLConnectionAbstract,
        transcription_id: int,
        urgency: str,
    ) -> None:
        """
        Insert urgency assessment into the database.

        :param conn: Active database connection
        :type conn: mysql.connector.MySQLConnection
        :param transcription_id: ID of the transcription
        :type transcription_id: int
        :param urgency: Urgency level assessment
        :type urgency: str
        :return: None
        :rtype: None
        :raises MySqlError: If database operations fail
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO voicemail_analysis_transcription_urgencies (transcription_id, urgency) VALUES (%s, %s)",
                    (transcription_id, urgency),
                )
            self.log.info(
                f"Inserted urgency: {urgency} for transcription_id: {transcription_id}"
            )
        except MySqlError as e:
            traceback.print_exc()
            self.log.error(
                f"Error inserting urgency for transcription_id {transcription_id}, urgency {urgency}: {e}"
            )
            check_mysql_data_error(e)

    def insert_caller_type(
        self,
        conn: PooledMySQLConnection | MySQLConnectionAbstract,
        transcription_id: int,
        caller_type: str,
    ) -> None:
        """
        Insert caller type classification into the database.

        :param conn: Active database connection
        :type conn: mysql.connector.MySQLConnection
        :param transcription_id: ID of the transcription
        :type transcription_id: int
        :param caller_type: Type of caller classification
        :type caller_type: str
        :return: None
        :rtype: None
        :raises MySqlError: If database operations fail
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO voicemail_analysis_transcription_caller_types (transcription_id, caller_type) VALUES (%s, %s)",
                    (transcription_id, caller_type),
                )
            self.log.info(
                f"Inserted caller type: {caller_type} for transcription_id: {transcription_id}"
            )
        except MySqlError as e:
            traceback.print_exc()
            self.log.error(
                f"Error inserting caller type for transcription_id {transcription_id}, caller type {caller_type}: {e}"
            )
            check_mysql_data_error(e)

    def insert_language(
        self,
        conn: PooledMySQLConnection | MySQLConnectionAbstract,
        transcription_id: int,
        language: str,
    ) -> None:
        """
        Insert language detection result into the database.

        :param conn: Active database connection
        :type conn: mysql.connector.MySQLConnection
        :param transcription_id: ID of the transcription
        :type transcription_id: int
        :param language: Detected language code
        :type language: str
        :return: None
        :rtype: None
        :raises MySqlError: If database operations fail
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO voicemail_analysis_transcription_languages (transcription_id, language) VALUES (%s, %s)",
                    (transcription_id, language),
                )
            self.log.info(
                f"Inserted language: {language} for transcription_id: {transcription_id}"
            )
        except MySqlError as e:
            traceback.print_exc()
            self.log.error(
                f"Error inserting language for transcription_id {transcription_id}, urgency {language}: {e}"
            )
            check_mysql_data_error(e)

    def process_batches(self, limit: int, pause: float) -> int:
        """
        Process multiple batches of transcriptions up to the specified limit.

        :param limit: Maximum number of transcriptions to process (0 for unlimited)
        :type limit: int
        :param pause: Seconds to pause between processing each transcription
        :type pause: float
        :return: Number of transcriptions processed
        :rtype: int
        """
        total_processed = 0
        while True:
            remaining = limit - total_processed if limit > 0 else BATCH_SIZE
            batch_size = min(BATCH_SIZE, remaining)
            processed = self.analyze_transcriptions(batch_size, pause)
            total_processed += processed
            if not self.running or processed == 0 or (limit > 0 and total_processed >= limit):
                self.log.info(f"Processed {total_processed} transcriptions.")
                break
        return total_processed

    def run_single(self, limit: int, pause: float) -> int:
        """
        Process a single batch of transcriptions up to the specified limit.

        :param limit: Maximum number of transcriptions to process (0 for unlimited)
        :type limit: int
        :param pause: Seconds to pause between processing each transcription
        :type pause: float
        :return: Number of transcriptions processed
        :rtype: int
        """
        self.running = True
        self.log.info("Starting single run mode")
        total_processed = self.process_batches(limit, pause)
        return total_processed

    def run_continuous(self, sleep_seconds: int) -> None:
        """
        Run the analyzer continuously, sleeping between cycles.
        Can be interrupted with SIGINT (Ctrl+C).

        :param sleep_seconds: Number of seconds to sleep between processing cycles
        :type sleep_seconds: int
        """
        cycle_count = 0
        self.running = True
        self.log.info(f"Starting continuous mode with {sleep_seconds} second intervals")
        self.log.info("Press Ctrl+C to exit gracefully")
        while self.running:
            cycle_count += 1
            self.process_batches(self.limit, self.pause)
            self.log.debug(f"Sleeping for {sleep_seconds} seconds")
            for _ in range(sleep_seconds):
                if not self.running:
                    break
                time.sleep(1)

    def setup_analysis_logfile(self, logfile: str | None) -> None:
        """
        Initialize the analysis logfile with timestamp header.

        :param logfile: Path to the logfile, or None to disable logging
        :type logfile: str | None
        :return: None
        :rtype: None
        :raises SystemExit: If logfile cannot be opened for writing
        """
        if logfile is not None:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with Path(logfile).open("a") as f:
                    _ = f.write(f"Starting at: {now}\n\n")
                self.log.debug(f"Opened analysis logfile {logfile} at {now}")
            except OSError as e:
                self.log.error(f"Could not open logfile {logfile} for writing: {e}")
                sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the voicemail analyzer.

    :return: Parsed command line arguments
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        default=os.environ.get("ANALYZER_DB_HOST", DEFAULT_DATABASE_HOST),
        help="Database host, default: environment variable ANALYZER_DB_HOST or %(default)s",
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("ANALYZER_DB_PORT", DEFAULT_DATABASE_PORT),
        type=int,
        help="Database port, default: environment variable ANALYZER_DB_PORT or %(default)s",
    )
    parser.add_argument(
        "--database",
        default=os.environ.get("ANALYZER_DB_NAME", DEFAULT_DATABASE_NAME),
        help="Database name, default: environment variable ANALYZER_DB_NAME or %(default)s",
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("ANALYZER_DB_USERNAME", ""),
        help="Database username, default: environment variable ANALYZER_DB_USERNAME"
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("ANALYZER_DB_PASSWORD", ""),
        help="Database password, default: environment variable ANALYZER_DB_PASSWORD"
    )
    parser.add_argument(
        "--template",
        default=ANALYSIZER_TEMPLATE,
        help="Analysis template, default: %(default)s",
    )
    parser.add_argument(
        "--logfile", help="Full path to a file to log transcriptions and analyses to"
    )
    parser.add_argument(
        "--limit",
        default=0,
        type=int,
        help="Limit number of records to analyze, default: no limit",
    )
    parser.add_argument(
        "--pause",
        default=0,
        type=float,
        help="Pause this number of seconds between analyses, default: no pause",
    )
    parser.add_argument(
        "--continuous",
        type=int,
        help="Run continuously, sleeping this many seconds between batch processing cycles",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    return args


def signal_handler(sig, frame, analyzer: VoicemailAnalyzer) -> None:
    """
    Handle interrupt signals to gracefully stop continuous mode.

    :param sig: Signal number
    :type sig: int
    :param frame: Current stack frame
    :type frame: frame
    :param analyzer: The VoicemailAnalyzer instance
    :type analyzer: VoicemailAnalyzer
    :return: None
    :rtype: None
    """
    if sig == signal.SIGINT:
        analyzer.log.info("Received interrupt signal, stopping gracefully...")
        analyzer.running = False

def main() -> None:
    """
    Main entry point for the voicemail analyzer.

    Initializes the analyzer, sets up logging, and processes voicemail transcriptions
    in batches according to command line arguments.

    :return: None
    :rtype: None
    :raises SystemExit: If logfile cannot be opened
    """
    args = parse_arguments()
    analyzer = VoicemailAnalyzer(args)
    analyzer.setup_analysis_logfile(args.logfile)

    # Set up signal handler for graceful interruption
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, analyzer))

    if args.continuous is not None:
        analyzer.run_continuous(args.continuous)
    else:
        analyzer.run_single(args.limit, args.pause)


if __name__ == "__main__":
    main()
