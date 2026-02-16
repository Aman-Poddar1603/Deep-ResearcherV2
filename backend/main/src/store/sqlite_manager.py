import sqlite3
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLiteManager:
    """
    A reusable context manager for SQLite3 database operations.
    Handles connection management and provides CRUD helper methods.
    """
    def __init__(self, db_path: str, timeout: int = 30):
        self.db_path = db_path
        self.timeout = timeout

    @contextmanager
    def _get_connection(self):
        """Yields a database connection and ensures it is closed after use."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=self.timeout)
            conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
            
            # Enable Foreign Keys and WAL mode for better concurrency/integrity
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database at {self.db_path}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Tuple = ()) -> None:
        """
        Executes a raw SQL query (INSERT, UPDATE, DELETE, CREATE, etc.).
        Note: Does not return a cursor as the connection is closed immediately.
        Use fetch_all or fetch_one for SELECT queries.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error executing query: {query} with params {params}. Error: {e}")
            raise

    def fetch_all(self, query: str, params: Tuple = ()) -> List[dict]:
        """Executes a query and returns all results as a list of dictionaries."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error fetching all: {query} with params {params}. Error: {e}")
            raise

    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[dict]:
        """Executes a query and returns a single result as a dictionary."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching one: {query} with params {params}. Error: {e}")
            raise

    def create_table(self, table_name: str, schema: str):
        """
        Creates a table with the given schema.
        :param schema: A string defining columns and types, e.g., "id INTEGER PRIMARY KEY, name TEXT"
        """
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})"
        self.execute_query(query)
        logger.info(f"Table '{table_name}' ensured to exist.")

    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Inserts a single record into the table.
        Returns the ID of the inserted row.
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Error inserting into {table_name}: {e}")
            raise

    def update(self, table_name: str, data: Dict[str, Any], where_clause: str, where_params: Tuple = ()):
        """
        Updates records in the table.
        :param where_clause: SQL condition string (e.g., "id = ?")
        :param where_params: Tuple of values for variables in where_clause
        """
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        params = tuple(data.values()) + where_params
        self.execute_query(query, params)
        logger.info(f"Updated record(s) in {table_name} where {where_clause}")

    def delete(self, table_name: str, where_clause: str, where_params: Tuple = ()):
        """
        Deletes records from the table.
        """
        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        self.execute_query(query, where_params)
        logger.info(f"Deleted record(s) from {table_name} where {where_clause}")

