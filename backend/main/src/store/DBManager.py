from pathlib import Path
import sqlite3
import re
from typing import Dict, Any, Optional, Tuple, Union
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
    ## Description

    A reusable context manager for SQLite3 database operations.
    Handles connection management, prevents SQL injection via identifier 
    validation, and provides CRUD (Create, Read, Update, Delete) helper methods.

    ## Parameters

    - `db_path` (`Union[str, Path]`)
      - Description: The file system path to the SQLite database file.
      - Constraints: Must be a valid path string or Path object.
      - Example: `"/store/database/main.db.sqlite3"`

    - `timeout` (`int`)
      - Description: Timeout in seconds for acquiring the database lock.
      - Constraints: Must be > 0. Defaults to 30.
      - Example: 30

    ## Returns

    `None`
    Instantiates an object.

    ## Raises

    - `None` (Constructor does not raise exceptions directly).

    ## Side Effects

    - Prepares the manager to interface with the database at `db_path`.

    ## Debug Notes

    - Check if `db_path` is correctly resolved by `BASE_DIR`.

    ## Customization

    - Timeout can be adjusted for systems experiencing higher lock contention.
    """
    def __init__(self, db_path: Union[str, Path], timeout: int = 30):
        self.db_path = str(db_path)
        self.timeout = timeout

    def _log(self, level: str, message: str, urgency: str = "none") -> None:
        """
        ## Description

        Helper method to log internal database operations safely while 
        avoiding circular recording into the log database itself.

        ## Parameters

        - `level` (`str`)
          - Description: The logging level to apply.
          - Constraints: Must be `"info"` or `"error"`.
          - Example: `"info"`

        - `message` (`str`)
          - Description: The text describing the event or error.
          - Constraints: Strings only.
          - Example: `"Table users created"`

        - `urgency` (`str`)
          - Description: Determines priority of the log in the standard log table.
          - Constraints: Defaults to `"none"`.
          - Example: `"critical"`

        ## Returns

        `None` (Implicitly)

        ## Raises

        - `None`
          - Fails gracefully, logging failures to console.

        ## Side Effects

        - Prints to terminal via standard python logging.
        - Writes to the `logs.db.sqlite3` via `dr_logger` if not logging about logs itself.

        ## Debug Notes

        - If logging loops, verify `logs.db.sqlite3` check correctly filters out logs DB.

        ## Customization

        - Add support for warning logs if required by changing `log_type` conditional.
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
                    urgency=urgency,  # type: ignore
                    app_version="1.0"
                )
            except Exception as e:
                logger.error(f"DRLogger internal failure in DBManager: {e}")

    @staticmethod
    def _validate_identifier(identifier: str) -> str:
        """
        ## Description

        Validates table and column names to prevent SQL injection.
        SQL parameter binding does not protect table/column names, so this is required.

        ## Parameters

        - `identifier` (`str`)
          - Description: The table or column name to validate.
          - Constraints: Must be alphanumeric and underscores only.
          - Example: `"user_profiles_1"`

        ## Returns

        `str`

        Structure:

        ```python
        # The validated string, unchanged if valid.
        "user_profiles_1"
        ```

        ## Raises

        - `ValueError`
          - When the string contains invalid characters (e.g. spaces, symbols).

        ## Side Effects

        - Halts operations throwing invalid inputs to caller.

        ## Debug Notes

        - Throws exception on quoted queries, ensuring standard naming only.

        ## Customization

        - Modify Regex if standard standard SQL column naming needs to support other chars.
        """
        if not re.match(r"^[a-zA-Z0-9_]+$", identifier):
            raise ValueError(f"Invalid identifier: '{identifier}'. Identifiers must be alphanumeric/underscore.")
        return identifier

    @contextmanager
    def _get_connection(self):
        """
        ## Description

        Yields a database connection and ensures it is closed after use using Context Manager.
        Applies PRAGMA directives for performance optimization.

        ## Parameters

        - `None`

        ## Returns

        `sqlite3.Connection`

        Structure:

        ```python
        # Generated context-managed connection
        <sqlite3.Connection object>
        ```

        ## Raises

        - `sqlite3.Error`
          - When the connection to physical file is blocked or corrupted.

        ## Side Effects

        - Locks file momentarily to acquire context.
        - Overrides PRAGMAS on connection (WAL mode enabled).
        - Closes connection when context exits.

        ## Debug Notes

        - Cache size is set to negative for MB equivalent (-64000 = 64MB).
        - Journal mode WAL supports concurrency but leaves -wal files locally.

        ## Customization

        - Adjust Cache limits depending on VPS/container memory resources.
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
        """
        ## Description

        Helper function to build SQL WHERE clause dynamically and its parameters array.

        ## Parameters

        - `where` (`Optional[Dict[str, Any]]`)
          - Description: Optional constraint dictionary mapping column names to exact equality.
          - Constraints: Keys must pass `_validate_identifier`.
          - Example: `{"status": "active", "id": 5}`

        ## Returns

        `Tuple[str, Tuple]`

        Structure:

        ```python
        # (SQL String, Value Bindings Tuple)
        ("WHERE status = ? AND id = ?", ("active", 5))
        ```

        ## Raises

        - `ValueError`
          - When Dictionary keys contain un-sanitized names.

        ## Side Effects

        - Parses input conditions deterministically.

        ## Debug Notes

        - Only supports standard equality. Will not generate `LIKE`, `IN`, or `<`, `>` statements.

        ## Customization

        - Can be extended to support operators mapping (e.g., `{"age__gt": 18}`).
        """
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
        ## Description

        Creates a table dynamically mapping user-provided dictionary schema 
        to SQLite string constraints.

        ## Parameters

        - `table_name` (`str`)
          - Description: The name of the table to create.
          - Constraints: Must be alphanumeric/underscores only.
          - Example: `"users_info"`

        - `schema` (`Dict[str, str]`)
          - Description: Mapping of columns to SQL Data Types and options.
          - Constraints: Values must be standard SQLite definitions.
          - Example: `{"id": "INTEGER PRIMARY KEY", "name": "TEXT"}`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "success": "true | false",
            "message": "Status description",
            "data": null
        }
        ```

        ## Raises

        - `None` (Catches exceptions internally to return error schema).

        ## Side Effects

        - Updates underlying DDL making new tables available in database.
        - Writes information/error logs on the system logger.

        ## Debug Notes

        - Prints SQL trace into DRLogger upon failures to aid debugging.

        ## Customization

        - Currently uses generic string replacement. For strict type safety, type mapping logic can be defined.
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
        ## Description

        Inserts a single dynamically mapped record into the table. 
        Uses parameterized queries to prevent data injection correctly.

        ## Parameters

        - `table_name` (`str`)
          - Description: Operational table explicitly handling the inserted record.
          - Constraints: RegEx validated string.
          - Example: `"chats"`

        - `data` (`Dict[str, Any]`)
          - Description: Column to Value mapping representing the record.
          - Constraints: Keys must match column names.
          - Example: `{"user_id": 1, "chat_name": "New Chat"}`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "success": "true | false",
            "message": "Outcome descriptor",
            "data": {
                "id": "integer | null"
            }
        }
        ```

        ## Raises

        - `None` (Internally wrapped by Error handers).

        ## Side Effects

        - Persists new row into SQLite DB storage.
        - Logs actions automatically.

        ## Debug Notes

        - Triggers uniqueness violations silently, returning false. Read DRLogger if records don't save.

        ## Customization

        - Does not support Batch inserts natively; must run multiple inserts or extend batch logic.
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
        """
        ## Description

        Executes a SELECT query mapping output rows iteratively into standard dictionaries.
        Supports optional WHERE constraints.

        ## Parameters

        - `table_name` (`str`)
          - Description: The target table.
          - Constraints: Alphanumeric and underscores string only.
          - Example: `"history"`

        - `where` (`Optional[Dict[str, Any]]`)
          - Description: Map filtering result set bounds (e.g. key=val).
          - Constraints: Dict object or None.
          - Example: `{"status": "completed"}`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "success": "true | false",
            "message": "System status",
            "data": [
                {
                   "id": 1,
                   "column_name": "value"
                }
            ]
        }
        ```

        ## Raises

        - `None` (Exceptions captured and reformatted).

        ## Side Effects

        - Executes read locks momentarily while fetching buffers.

        ## Debug Notes

        - Large loads read into standard RAM directly as List, could create OutOfMemory for gigabyte tables.

        ## Customization

        - Implement Generator or LIMIT pagination offsets for heavy row pulls.
        """
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
        """
        ## Description

        Fetches exactly one matching row mapped to a Python dictionary.

        ## Parameters

        - `table_name` (`str`)
          - Description: Source SQL table reference.
          - Constraints: Alphanumeric validation handled.
          - Example: `"logs"`

        - `where` (`Optional[Dict[str, Any]]`)
          - Description: Row condition constraints mapping strictly to single result.
          - Constraints: Provided keys must be valid naming conventions.
          - Example: `{"logId": "unique-uuid"}`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "success": "true | false",
            "message": "Fetch notification string",
            "data": {
                "id": 1,
                "column_name": "data string value"
            } # NULL if no row found.
        }
        ```

        ## Raises

        - `None` (Logs output internally for issues).

        ## Side Effects

        - Minimal read lock duration.

        ## Debug Notes

        - Does not include `LIMIT 1` inherently, takes very first match from SQL query cursor.

        ## Customization

        - Add "OFFSET" arguments explicitly to iterate fetch_one calls.
        """
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
        ## Description

        Replaces content within constrained rows dynamically matched by explicit `where` dictionary maps.

        ## Parameters

        - `table_name` (`str`)
          - Description: Database target name.
          - Constraints: Checked format.
          - Example: `"scrapes"`

        - `data` (`Dict[str, Any]`)
          - Description: Fields intended to overwrite inside matching rows.
          - Constraints: Keys validated. Values dynamically casted.
          - Example: `{"status": "complete", "result": "JSON blob..."}`

        - `where` (`Dict[str, Any]`)
          - Description: Filter dictionary mapping rows to target.
          - Constraints: MUST NOT BE EMPTY/NULL (To avoid catastrophic data resets).
          - Example: `{"id": 24}`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "success": "true | false",
            "message": "Action summary",
            "data": {
                "rowcount": "integer"
            }
        }
        ```

        ## Raises

        - `None` (Reports gracefully through system).

        ## Side Effects

        - Irreversibly alters database info matched into target scope.

        ## Debug Notes

        - If no rows match where parameter, execution succeeds returning `rowcount: 0`.

        ## Customization

        - Adjust the requirement for where clause directly if bulk `UPDATE ALL` behavior is strictly required later.
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
        ## Description

        Executes physical row deletion bounded by conditions securely parameterized.

        ## Parameters

        - `table_name` (`str`)
          - Description: Name of the structure.
          - Constraints: Valid identifier regex matches required.
          - Example: `"buckets"`

        - `where` (`Dict[str, Any]`)
          - Description: Limits the targets of the deletion strictly.
          - Constraints: Strict requirement (cannot be None).
          - Example: `{"storage_id": "900x-09"}`

        ## Returns

        `dict`

        Structure:

        ```json
        {
            "success": "true | false",
            "message": "Action string output",
            "data": {
                "rowcount": "integer count of dropped documents"
            }
        }
        ```

        ## Raises

        - `None` (Logged internally via DRLogger structure).

        ## Side Effects

        - Destroys matching content completely inside physical drive file.

        ## Debug Notes

        - A missing `where` clause aborts method without interacting externally.

        ## Customization

        - Soft-Deletes can be implemented utilizing `update()` call adjusting "deleted_at" timestamp fields.
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
    ## Description

    Ensures that the required directories and SQLite databases exist at the application level.

    ## Parameters

    - `None`

    ## Returns

    `None`

    ## Raises

    - `None` (Continues past file initialization problems after logging).

    ## Side Effects

    - Creates `database/` and `bucket/` folders if completely absent.
    - Generates blank `db_name.sqlite3` objects for standard application usage.

    ## Debug Notes

    - The `_initialize_store` triggers at module import time safely.
    - Emits boot sequences automatically to standard logs table.

    ## Customization

    - Increase database file sets strictly by adding new filenames to the `required_dbs` list.
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

# Keep instances for direct exports if needed anywhere else
db_folder = BASE_DIR / "database"

logs_db_manager = SQLiteManager(db_folder / "logs.db.sqlite3")
main_db_manager = SQLiteManager(db_folder / "main.db.sqlite3")
history_db_manager = SQLiteManager(db_folder / "history.db.sqlite3")
scrapes_db_manager = SQLiteManager(db_folder / "scrapes.db.sqlite3")
buckets_db_manager = SQLiteManager(db_folder / "buckets.db.sqlite3")
researches_db_manager = SQLiteManager(db_folder / "researches.db.sqlite3")
chats_db_manager = SQLiteManager(db_folder / "chats.db.sqlite3")
