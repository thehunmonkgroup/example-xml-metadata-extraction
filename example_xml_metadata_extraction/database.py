"""Handles database operations for the shock wave counter."""

import sqlite3
from pathlib import Path
from typing import Any


class Database:
    """
    Manages interactions with the SQLite database for storing analysis data.
    """

    def __init__(self, db_path: str | Path) -> None:
        """
        Initializes the Database object and ensures the database and table exist.

        :param db_path: The path to the SQLite database file.
        :type db_path: Union[str, Path]
        """
        self.db_path: Path = Path(db_path)
        self._initialize_db()

    def _initialize_db(self) -> None:
        """
        Creates the database directory and the strike_log table if they don't exist.
        """
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT,
                entity_class TEXT CHECK(entity_class IN ('person', 'country', 'city', 'historical_event', 'holiday', 'concept', 'biological_species', 'organization', 'work_of_art', 'technology', 'other')),
                geo_focus TEXT CHECK(geo_focus IN ('global', 'continent', 'country', 'sub_national', 'local', 'none')),
                temporal_era TEXT CHECK(temporal_era IN ('pre_history', 'classical', 'medieval', 'early_modern', 'modern', 'contemporary', 'none')),
                domain TEXT CHECK(domain IN ('geography', 'politics', 'science', 'arts', 'religion', 'technology', 'economics', 'sports', 'history', 'culture', 'other')),
                contains_dates TEXT CHECK(contains_dates IN ('yes', 'no')),
                contains_coordinates TEXT CHECK(contains_coordinates IN ('yes', 'no')),
                has_see_also TEXT CHECK(has_see_also IN ('yes', 'no'))
            )
            """
        )
        conn.commit()
        conn.close()

    def add_analysis_entry(
        self,
        data: dict[str, Any],
    ) -> None:
        """
        Adds a new analysis entry to the database.

        :param data: Dictionary of data to be inserted.
        :type data: dict[str, Any]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO analysis_data (model, entity_class, geo_focus, temporal_era, domain, contains_dates, contains_coordinates, has_see_also) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data["model"], data["entity_class"], data["geo_focus"], data["temporal_era"], data["domain"], data["contains_dates"], data["contains_coordinates"], data["has_see_also"]),
        )
        conn.commit()
        conn.close()
