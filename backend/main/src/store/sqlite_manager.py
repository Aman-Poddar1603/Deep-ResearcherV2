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
        """
        Yields a database connection and ensures it is closed after use.
        """
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

    def _build_where_clause(self, where: Dict[str, Any] = None) -> Tuple[str, Tuple]:
        """Helper to build SQL WHERE clause and parameters from a dictionary."""
        if not where:
            return "", ()
        conditions = [f"{key} = ?" for key in where.keys()]
        clause = "WHERE " + " AND ".join(conditions)
        return clause, tuple(where.values())

    def create_table(self, table_name: str, schema: Dict[str, str]) -> Dict[str, Any]:
        """
        Creates a table with the given schema.
        :param schema: A dictionary defining columns and types, e.g., {"id": "INTEGER PRIMARY KEY", "name": "TEXT"}
        """
        if not isinstance(schema, dict):
             return {"success": False, "message": "Schema must be a dictionary", "data": None}
             
        columns_def = ', '.join([f"{col} {dtype}" for col, dtype in schema.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def})"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
            logger.info(f"Table '{table_name}' ensured to exist.")
            return {"success": True, "message": f"Table '{table_name}' created or already exists", "data": None}
        except sqlite3.Error as e:
            logger.error(f"Error creating table {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserts a single record into the table.
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
                return {"success": True, "message": "Record inserted successfully", "data": {"id": cursor.lastrowid}}
        except sqlite3.Error as e:
            logger.error(f"Error inserting into {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def fetch_all(self, table_name: str, where: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes a SELECT * query with optional WHERE clause and returns all results."""
        try:
            where_clause, params = self._build_where_clause(where)
            query = f"SELECT * FROM {table_name} {where_clause}"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
                return {"success": True, "message": "Fetched successfully", "data": data}
        except sqlite3.Error as e:
            logger.error(f"Error fetching all from {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def fetch_one(self, table_name: str, where: Dict[str, Any] = None) -> Dict[str, Any]:
        """Executes a SELECT * query with optional WHERE clause and returns a single result."""
        try:
            where_clause, params = self._build_where_clause(where)
            query = f"SELECT * FROM {table_name} {where_clause}"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                row = cursor.fetchone()
                data = dict(row) if row else None
                return {"success": True, "message": "Fetched successfully", "data": data}
        except sqlite3.Error as e:
            logger.error(f"Error fetching one from {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def update(self, table_name: str, data: Dict[str, Any], where: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates records in the table.
        """
        if not where: # Error handling for missing where clause to prevent accidental bulk updates
             return {"success": False, "message": "Update operation requires a where clause", "data": None}
             
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        where_clause, where_params = self._build_where_clause(where)
        query = f"UPDATE {table_name} SET {set_clause} {where_clause}"
        params = tuple(data.values()) + where_params
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return {"success": True, "message": "Record(s) updated successfully", "data": {"rowcount": cursor.rowcount}}
        except sqlite3.Error as e:
            logger.error(f"Error updating {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

    def delete(self, table_name: str, where: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deletes records from the table.
        """
        if not where:
             return {"success": False, "message": "Delete operation requires a where clause", "data": None}

        where_clause, params = self._build_where_clause(where)
        query = f"DELETE FROM {table_name} {where_clause}"
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return {"success": True, "message": "Record(s) deleted successfully", "data": {"rowcount": cursor.rowcount}}
        except sqlite3.Error as e:
            logger.error(f"Error deleting from {table_name}: {e}")
            return {"success": False, "message": str(e), "data": None}

