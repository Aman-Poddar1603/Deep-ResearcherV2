from pathlib import Path
import sqlite3
import os
import re
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from contextlib import contextmanager
from pathlib import Path
import sys

BASE_DIR = Path(__file__).parent
src_dir = BASE_DIR.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

from utils.DRLogger import dr_logger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLiteManager:
    """
    A reusable context manager for SQLite3 database operations.
    Handles connection management and provides CRUD helper methods.
    """
    def __init__(self, db_path: Union[str, Path], timeout: int = 30):
        self.db_path = str(db_path)
        self.timeout = timeout

    def _log(self, level: str, message: str, urgency: str = "none") -> None:
        """
        Helper method to log internal database operations safely while 
        avoiding circular recording into the log database itself.
        """
        if level == "error":
            logger.error(message)
        else:
            logger.info(message)
            
        if "logs.db.sqlite3" not in self.db_path:
            try:
                log_type = "error" if level == "error" else "info"
                dr_logger.log(
                    log_type=log_type,
                    message=message,
                    origin="system",
                    module="DB",
                    urgency=urgency,
                    app_version="1.0"
                )
            except Exception as e:
                logger.error(f"DRLogger internal failure in DBManager: {e}")

    @staticmethod
    def _validate_identifier(identifier: str) -> str:
        """Validates table and column names to prevent SQL injection."""
        if not re.match(r"^[a-zA-Z0-9_]+$", identifier):
            raise ValueError(f"Invalid identifier: '{identifier}'. Identifiers must be alphanumeric/underscore.")
        return identifier

    @contextmanager
    def _get_connection(self):
        """
        Yields a database connection and ensures it is closed after use.
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
            
            # Enable Foreign Keys and WAL mode for better concurrency/integrity
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")  # Better performance and concurrency
            conn.execute("PRAGMA synchronous = NORMAL;") # Performance optimization with WAL
            conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
            
            yield conn
        except sqlite3.Error as e:
            self._log("error", f"Error connecting to database at {self.db_path}: {e}", "critical")
            raise
        finally:
            if conn:
                conn.close()

    def _build_where_clause(self, where: Optional[Dict[str, Any]] = None) -> Tuple[str, Tuple]:
        """Helper to build SQL WHERE clause and parameters from a dictionary."""
        if not where:
            return "", ()
        conditions = []
        for key in where.keys():
            valid_key = self._validate_identifier(key)
            conditions.append(f"{valid_key} = ?")
        clause = "WHERE " + " AND ".join(conditions)
        return clause, tuple(where.values())

    def create_table(self, table_name: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Creates a table with the given schema.
        :param schema: A dictionary defining columns and types, e.g., {"id": "INTEGER PRIMARY KEY", "name": "TEXT"}
        """
        if not isinstance(schema, dict):
            return {"success": False, "message": "Schema must be a dictionary", "data": None}
             
        try:
            valid_table = self._validate_identifier(table_name)
            columns_def = ', '.join([f"{self._validate_identifier(col)} {dtype}" for col, dtype in schema.items()])
            query = f"CREATE TABLE IF NOT EXISTS {valid_table} ({columns_def})"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
            self._log("info", f"Table '{valid_table}' ensured to exist.")
            return {"success": True, "message": f"Table '{valid_table}' created or already exists", "data": None}
        except (ValueError, sqlite3.Error) as e:
            self._log("error", f"Error creating table {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a single record into the table.
        """
        try:
            valid_table = self._validate_identifier(table_name)
            valid_columns = [self._validate_identifier(k) for k in data.keys()]
            
            columns = ', '.join(valid_columns)
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO {valid_table} ({columns}) VALUES ({placeholders})"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
                return {"success": True, "message": "Record inserted successfully", "data": {"id": cursor.lastrowid}}
        except (ValueError, sqlite3.Error) as e:
            self._log("error", f"Error inserting into {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def fetch_all(self, table_name: str, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a SELECT * query with optional WHERE clause and returns all results."""
        try:
            valid_table = self._validate_identifier(table_name)
            where_clause, params = self._build_where_clause(where)
            query = f"SELECT * FROM {valid_table} {where_clause}"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                data_list = [dict(row) for row in rows]
                return {"success": True, "message": "Fetched successfully", "data": data_list}
        except (ValueError, sqlite3.Error) as e:
            self._log("error", f"Error fetching all from {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def fetch_one(self, table_name: str, where: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a SELECT * query with optional WHERE clause and returns a single result."""
        try:
            valid_table = self._validate_identifier(table_name)
            where_clause, params = self._build_where_clause(where)
            query = f"SELECT * FROM {valid_table} {where_clause}"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                row = cursor.fetchone()
                data = dict(row) if row else None
                return {"success": True, "message": "Fetched successfully", "data": data}
        except (ValueError, sqlite3.Error) as e:
            self._log("error", f"Error fetching one from {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def update(self, table_name: str, data: Dict[str, Any], where: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates records in the table.
        """
        if not where: # Error handling for missing where clause to prevent accidental bulk updates
             return {"success": False, "message": "Update operation requires a where clause", "data": None}
             
        try:
            valid_table = self._validate_identifier(table_name)
            set_clauses = [f"{self._validate_identifier(key)} = ?" for key in data.keys()]
            set_clause = ', '.join(set_clauses)
            where_clause, where_params = self._build_where_clause(where)
            
            query = f"UPDATE {valid_table} SET {set_clause} {where_clause}"
            params = tuple(data.values()) + where_params
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return {"success": True, "message": "Record(s) updated successfully", "data": {"rowcount": cursor.rowcount}}
        except (ValueError, sqlite3.Error) as e:
            self._log("error", f"Error updating {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def delete(self, table_name: str, where: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deletes records from the table.
        """
        if not where:
             return {"success": False, "message": "Delete operation requires a where clause", "data": None}

        try:
            valid_table = self._validate_identifier(table_name)
            where_clause, params = self._build_where_clause(where)
            query = f"DELETE FROM {valid_table} {where_clause}"
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return {"success": True, "message": "Record(s) deleted successfully", "data": {"rowcount": cursor.rowcount}}
        except (ValueError, sqlite3.Error) as e:
            self._log("error", f"Error deleting from {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}


def _initialize_store():
    """
    Ensures that the required directories and SQLite databases exist.
    """
    database_dir = BASE_DIR / "database"
    bucket_dir = BASE_DIR / "bucket"
    
    # Create directories if they do not exist
    database_dir.mkdir(parents=True, exist_ok=True)
    bucket_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Ensured directories exist: {database_dir} and {bucket_dir}")

    required_dbs = [
        "main.db.sqlite3",
        "history.db.sqlite3",
        "scrapes.db.sqlite3",
        "buckets.db.sqlite3",
        "researches.db.sqlite3",
        "chats.db.sqlite3",
        "logs.db.sqlite3"
    ]
    
    # Initialize connection for each database to create the file if it doesn't exist
    for db_name in required_dbs:
        db_path = database_dir / db_name
        try:
            # Connect to create db or ensure accessibility
            with sqlite3.connect(str(db_path), timeout=5) as conn:
                pass 
            logger.info(f"Database initialized: {db_name}")
            
            # Avoid recursive loop specifically on the logs DB
            if "logs.db" not in db_name:
                dr_logger.log("info", f"Database initialized: {db_name}", "system", "DB", "none", "1.0")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database {db_name}: {e}")
            if "logs.db" not in db_name:
                dr_logger.log("error", f"Failed to initialize database {db_name}: {e}", "system", "DB", "moderate", "1.0")

# Run initialization upon module import
_initialize_store()

# Keep instance for direct logs exports if needed anywhere else
logs_db_path = BASE_DIR / "database" / "logs.db.sqlite3"
logs_db_manager = SQLiteManager(logs_db_path)

