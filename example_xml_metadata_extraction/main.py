import sys
import re
import argparse
import logging
import os
import tempfile
import uuid
import datetime
import xml.etree.ElementTree as ET
import traceback
import time
import signal
from pathlib import Path
import sqlite3
from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
from typing import Any
from dotenv import find_dotenv, load_dotenv
import datasets

from lwe.core.config import Config
from lwe.backends.api.backend import ApiBackend


from .logger import Logger
from .config import set_environment_variables
from . import constants
from .database import Database

load_dotenv(find_dotenv(usecwd=True))


class ParserError(ValueError):
    pass


class AnalyzerError(RuntimeError):
    pass


class PagesAnalyzer:
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
        self.database: Database = Database(args.database)
        self.template: str = args.template
        self.logfile: str | None = args.logfile
        self.preset: str = args.preset
        self.offset: int = args.offset
        self.limit: int = args.limit
        self.pause: int = args.pause
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

    def analyze_pages(self) -> int:
        """
        Process a batch of pages.

        :return: Number of pages processed
        :rtype: int
        """
        processed = 0
        pages = self.load_pages()
        for page in pages:
            if not self.running:
                break
            self.process_page_try(dict(page)["text"])
            processed += 1
            if self.pause > 0:
                self.log.info(f"Pausing for {self.pause} seconds")
                time.sleep(self.pause)
        return processed

    def load_pages(self) -> datasets.arrow_dataset.Dataset:
        self.log.info(f"Downloading dataset: {constants.HUGGINGFACE_DATASET}")
        dataset: datasets.arrow_dataset.Dataset = datasets.load_dataset(**constants.HUGGINGFACE_DATASET, split="train")  # pyright: ignore[reportAssignmentType, reportArgumentType]
        self.log.info(f"Dataset size: {len(dataset)}")
        if self.debug:
            for i in range(constants.DEBUG_DATASET_SIZE):
                if len(dataset[i]["text"].strip()) > constants.DATA_LENGTH_THRESHOLD:
                    print("")
                    print("")
                    print(f"## Datapoint {i + 1}")
                    print("")
                    print(dataset[i]["text"])
        return dataset.select(range(self.offset, self.offset + self.limit))

    def process_page_try(
        self,
        text: str,
    ) -> dict[str, Any] | None:
        """
        Process a single page through the analysis pipeline.

        :param text: Page text
        :type text: str
        :return: Dictionary containing analysis results
        :rtype: dict[str, Any]
        """
        try:
            results = self.process_page(text)
            if results is not None:
                self.insert_analysis(results)
            else:
                self.log.error(f"Analysis failed using model {self.preset}")
        except RetryError as e:
            if isinstance(e.last_attempt.exception(), (ParserError, AnalyzerError, sqlite3.DatabaseError)):
                self.log.error(f"Analysis failed using model {self.preset}. Original error: {e.last_attempt.exception()}")
            else:
                raise

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(5))
    def process_page(
        self, text: str,
    ) -> dict[str, Any] | None:
        """
        Process a single page through the analysis pipeline.

        :param text: Page text
        :type text: str
        :return: Dictionary containing analysis results
        :rtype: dict[str, Any]
        :raises ParserError: If analysis response cannot be parsed
        :raises AnalyzerError: If analysis fails
        :raises sqlite3.DatabaseError: If database data insertion fails
        """
        try:
            response = self.perform_analysis(text)
            parsed_results = self.parse_analysis(response)
            self.log_analysis(parsed_results)
            return parsed_results
        except (ParserError, AnalyzerError, sqlite3.DatabaseError) as e:
            self.log.error(f"Error processing page: {e}")
            _ = traceback.format_exc()
            raise

    def log_analysis(
        self, results: dict[str, Any]
    ) -> None:
        """
        Log the analysis results to a file if logging is enabled.

        :param results: Dictionary containing analysis results
        :type results: dict[str, Any]
        :return: None
        :rtype: None
        """
        if self.logfile:
            self.log.debug(f"Logging analysis for page to {self.logfile}")
            reasoning = results.get("reasoning", "")
            metadata = {}
            for m_type in constants.DATA_COLUMNS:
                metadata[m_type] = results.get(m_type, "")
            with Path(self.logfile).open("a") as f:
                output = f"""
###############################################################################
Reasoning:
{reasoning}

Metadata:
{metadata}
###############################################################################
"""
                _ = f.write(output)

    def perform_analysis(self, text: str) -> str:
        """
        Run the analysis template on a page.

        :param text: Page text
        :type text: str
        :return: Raw analysis response text
        :rtype: str
        :raises AnalyzerError: If template execution fails
        """
        identifier = uuid.uuid4().hex[:8]
        template_vars = {"article_text": text, "identifier": identifier}
        overrides = {
            "request_overrides": {
                "preset": self.preset,
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
        return str(response)

    def escape_xml_content(self, xml_content: str) -> str:
        """
        Escape XML content by wrapping text in CDATA sections.

        :param xml_content: Raw XML content to escape
        :type xml_content: str
        :return: Escaped XML content with CDATA sections
        :rtype: str
        """

        def replace_text(match: re.Match[str]) -> str:
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
        metadata = {}
        for child in root:
            key_lower = child.tag.lower().replace("-", "_")
            value = child.text.strip() if child.text else ""
            if key_lower in constants.DATA_COLUMNS and value:
                metadata[key_lower] = value
        self.log.debug(f"Parsed headers: {metadata}")
        if set(metadata.keys()) != set(constants.DATA_COLUMNS):
            raise ParserError(f"Missing required headers in analysis XML: {[item for item in metadata.keys() if item not in constants.DATA_COLUMNS]}")
        return metadata

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    def insert_analysis(
        self, results: dict[str, Any]
    ) -> None:
        """
        Insert analysis results into the database for a page.

        :param results: Dictionary containing analysis results
        :type results: dict[str, Any]
        :return: None
        :rtype: None
        :raises sqlite3.DatabaseError: If database operations fail
        """
        try:
            self.insert_analysis_results(results)
            self.log.info(
                f"Page committed for preset: {self.preset}"
            )
        except sqlite3.DatabaseError as e:
            self.log.info(
                f"Page error for preset: {self.preset}. Error: {e}"
            )
            if self.debug:
                traceback.print_exc()

    def insert_analysis_results(self, results: dict[str, Any]):
        results["model"] = self.preset
        self.database.add_analysis_entry(results)

    def process_batches(self) -> int:
        """
        Process multiple batches of pages up to the specified limit.

        :return: Number of pages processed
        :rtype: int
        """
        total_processed = 0
        while True:
            processed = self.analyze_pages()
            total_processed += processed
            if not self.running or processed == 0 or (self.limit > 0 and total_processed >= self.limit):
                self.log.info(f"Processed {total_processed} pages.")
                break
        return total_processed

    def run_single(self) -> int:
        """
        Process a single batch of pages up to the specified limit.

        :return: Number of pages processed
        :rtype: int
        """
        self.running = True
        self.log.info("Starting analysis run")
        total_processed = self.process_batches()
        return total_processed

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
        "--database",
        default=os.environ.get("ANALYZER_DB_NAME", constants.DEFAULT_DATABASE_NAME),
        help="Database name, default: environment variable ANALYZER_DB_NAME or %(default)s",
    )
    parser.add_argument(
        "--template",
        default=constants.ANALYSIZER_TEMPLATE,
        help="Analysis template, default: %(default)s",
    )
    parser.add_argument(
        "--logfile", help="Full path to a file to log pages and analyses to"
    )
    parser.add_argument(
        "--preset",
        default=constants.DEFAULT_PRESET,
        type=str,
        help="LWE preset to use for performing the analysis, default: %(default)s",
    )
    parser.add_argument(
        "--offset",
        default=0,
        type=int,
        help="Offset for the first page to use in the dataset, default: %(default)s",
    )
    parser.add_argument(
        "--limit",
        default=constants.DEFAULT_LIMIT,
        type=int,
        help="Limit number of pages to analyze, default: %(default)s",
    )
    parser.add_argument(
        "--pause",
        default=0,
        type=float,
        help="Pause this number of seconds between analyses, default: no pause",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    return args


def signal_handler(sig: int, _frame: Any, analyzer: PagesAnalyzer) -> None:
    """
    Handle interrupt signals to gracefully stop continuous mode.

    :param sig: Signal number
    :type sig: int
    :param frame: Current stack frame
    :type frame: frame
    :param analyzer: The PagesAnalyzer instance
    :type analyzer: PagesAnalyzer
    :return: None
    :rtype: None
    """
    if sig == signal.SIGINT:
        analyzer.log.info("Received interrupt signal, stopping gracefully...")
        analyzer.running = False

def main() -> None:
    """
    Main entry point for the pages analyzer.

    Initializes the analyzer, sets up logging, and processes pages
    in batches according to command line arguments.

    :return: None
    :rtype: None
    :raises SystemExit: If logfile cannot be opened
    """
    args = parse_arguments()
    analyzer = PagesAnalyzer(args)
    analyzer.setup_analysis_logfile(args.logfile)

    # Set up signal handler for graceful interruption
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, analyzer))

    analyzer.run_single()


if __name__ == "__main__":
    main()
