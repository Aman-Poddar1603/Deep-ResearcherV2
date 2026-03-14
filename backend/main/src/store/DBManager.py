import logging
import re
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from main.src.utils.DRLogger import dr_logger
from main.src.utils.version_constants import get_raw_version

BASE_DIR = Path(__file__).parent
src_dir = BASE_DIR.parent
if str(src_dir) not in sys.path:
    sys.path.append(str(src_dir))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOG_SOURCE = "system"


def _log_db_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
):
    """
    ## Description

    Internal utility function for logging secret management events with structured
    metadata. Ensures all secret-related operations are tracked with appropriate
    urgency levels and log sources.

    ## Parameters

    - `level` (`Literal["success", "error", "warning", "info"]`)
      - Description: Log severity level indicating the nature of the event.
      - Constraints: Must be one of: "success", "error", "warning", "info".
      - Example: "error"

    - `message` (`str`)
      - Description: Human-readable description of the secret event.
      - Constraints: Must be non-empty. Should not contain sensitive data (API keys, tokens).
      - Example: ".env file not found at /path/to/.env"

    - `urgency` (`Literal["none", "moderate", "critical"]`, optional)
      - Description: Priority indicator for the logged event.
      - Constraints: Must be one of: "none", "moderate", "critical".
      - Default: "none"
      - Example: "critical"

    ## Returns

    `None`

    ## Side Effects

    - Writes log entry to the DRLogger system.
    - Includes application version in all log entries.
    - Tags all events with "SECRETS_MANAGEMENT" for filtering.

    ## Debug Notes

    - Ensure messages do NOT contain sensitive information (API keys, tokens).
    - Use appropriate urgency levels: "critical" for missing keys, "moderate" for fallbacks.
    - Check logger output in application logs directory.

    ## Customization

    To change log source or tags globally, modify the module-level constants:
    - `LOG_SOURCE`: Change from "system" to custom value
    """
    dr_logger.log(
        log_type=level,
        message=message,
        origin=LOG_SOURCE,
        urgency=urgency,
        module="DB",
        app_version=get_raw_version(),
    )


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
            _log_db_event(
                f"Invalid identifier: '{identifier}'. Identifiers must be alphanumeric/underscore.",
                level="warning",
                urgency="moderate",
            )
            raise ValueError(
                f"Invalid identifier: '{identifier}'. Identifiers must be alphanumeric/underscore."
            )
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
            conn.execute(
                "PRAGMA journal_mode = WAL;"
            )  # Better performance and concurrency
            conn.execute(
                "PRAGMA synchronous = NORMAL;"
            )  # Performance optimization with WAL
            conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache

            yield conn
        except sqlite3.Error as e:
            _log_db_event(
                f"Error connecting to database at {self.db_path}: {e}",
                "error",
                "critical",
            )
            raise
        finally:
            if conn:
                conn.close()

    def _build_where_clause(
        self, where: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Tuple]:
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

    def create_table(
        self,
        table_name: str,
        schema: Dict[str, str],
        indexes: Optional[List[Union[str, List[str]]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a SQLite table dynamically and optionally create indexes.

        This function builds a `CREATE TABLE` statement using the provided
        schema dictionary and executes it. After the table is created,
        optional indexes may also be created.

        Foreign keys are enforced because the connection enables
        `PRAGMA foreign_keys = ON`.

        Args:
            table_name (str):
                Name of the table to create. Must match the identifier regex
                `^[a-zA-Z0-9_]+$`.

            schema (Dict[str, str]):
                Mapping of column names to SQLite column definitions
                (type + constraints). The SQL definition is inserted directly
                into the query.

                Example:
                ```python
                {
                    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                    "user_id": "INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE",
                    "title": "TEXT",
                    "body": "TEXT"
                }
                ```

            indexes (Optional[List[Union[str, List[str], Dict[str, Any]]]]):
                Optional index definitions.

                Supported formats:

                - Single column index:
                    `"user_id"`

                - Compound index:
                    `["user_id", "created_at"]`

                - Descriptor dictionary:
                    ```python
                    {
                        "cols": ["user_id", "title"],
                        "unique": True,
                        "name": "uq_posts_user_title"
                    }
                    ```

                Descriptor fields:
                    - cols (`List[str]`): Columns included in the index.
                    - name (`Optional[str]`): Custom index name.
                    - unique (`Optional[bool]`): Whether the index is UNIQUE.

        Returns:
            `Dict[str, Any]`: Dictionary containing the execution result.

            Structure:
                ```python
                {
                    "success": bool,
                    "message": str,
                    "data": None
                }
                ```

        Notes:
            - SQLite has limited ALTER TABLE support. Changing foreign keys
              often requires recreating the table.
            - Column definitions are used as provided and must be valid SQL.
            - Index creation failures are logged but do not cause the table
              creation to fail.

        Examples:
            Create table with indexes:
                ```python
                sqlite_mgr.create_table(
                    "posts",
                    {
                        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                        "user_id": "INTEGER",
                        "title": "TEXT",
                        "body": "TEXT"
                    },
                    indexes=["user_id", "title"]
                )
                ```

            Create table with compound index:
                ```python
                sqlite_mgr.create_table(
                    "events",
                    {
                        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
                        "user_id": "INTEGER",
                        "created_at": "INTEGER"
                    },
                    indexes=[["user_id", "created_at"]]
                )
                ```
        """
        if not isinstance(schema, dict):
            return {
                "success": False,
                "message": "Schema must be a dictionary",
                "data": None,
            }

        try:
            valid_table = self._validate_identifier(table_name)
            columns_def = ", ".join(
                [
                    f"{self._validate_identifier(col)} {dtype}"
                    for col, dtype in schema.items()
                ]
            )
            query = f"CREATE TABLE IF NOT EXISTS {valid_table} ({columns_def})"

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()

                # Create indexes if provided
                if indexes:
                    for idx_entry in indexes:
                        # Normalize to list of columns
                        cols = (
                            [idx_entry]
                            if isinstance(idx_entry, str)
                            else list(idx_entry)
                        )
                        if not cols:
                            continue
                        # Validate column names
                        try:
                            valid_cols = [self._validate_identifier(c) for c in cols]
                        except ValueError as e:
                            _log_db_event(
                                f"Invalid index column in indexes for table '{valid_table}': {e}",
                                "warning",
                                urgency="moderate",
                            )
                            continue
                        # Build index name deterministically and validate
                        index_name = f"idx_{valid_table}_" + "_".join(valid_cols)
                        try:
                            index_name = self._validate_identifier(index_name)
                        except ValueError:
                            # fallback: a safe sanitized index name (replace non-alnum with underscore)
                            index_name = re.sub(r"[^a-zA-Z0-9_]+", "_", index_name)

                        index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {valid_table} ({', '.join(valid_cols)})"
                        try:
                            cursor.execute(index_sql)
                        except sqlite3.Error as e:
                            # Log index creation failure but do not fail the whole operation
                            _log_db_event(
                                f"Failed to create index {index_name} on {valid_table}: {e}",
                                "error",
                                urgency="moderate",
                            )
                    conn.commit()

            _log_db_event(
                f"Table '{valid_table}' ensured to exist.", "info", urgency="none"
            )
            return {
                "success": True,
                "message": f"Table '{valid_table}' created or already exists",
                "data": None,
            }
        except (ValueError, sqlite3.Error) as e:
            _log_db_event(
                f"Error creating table {table_name}: {e}", "error", urgency="critical"
            )
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

            columns = ", ".join(valid_columns)
            placeholders = ", ".join(["?"] * len(data))
            query = f"INSERT INTO {valid_table} ({columns}) VALUES ({placeholders})"

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
                return {
                    "success": True,
                    "message": "Record inserted successfully",
                    "data": {"id": cursor.lastrowid},
                }
        except (ValueError, sqlite3.Error) as e:
            _log_db_event(
                f"Error inserting into {table_name}: {e}", "error", urgency="critical"
            )
            return {"success": False, "message": str(e), "data": None}

    def fetch_all(
        self, table_name: str, where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
                return {
                    "success": True,
                    "message": "Fetched successfully",
                    "data": data_list,
                }
        except (ValueError, sqlite3.Error) as e:
            _log_db_event(
                f"Error fetching all from {table_name}: {e}",
                "error",
                urgency="critical",
            )
            return {"success": False, "message": str(e), "data": None}

    def fetch_one(
        self, table_name: str, where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
                return {
                    "success": True,
                    "message": "Fetched successfully",
                    "data": data,
                }
        except (ValueError, sqlite3.Error) as e:
            _log_db_event(
                f"Error fetching one from {table_name}: {e}",
                "error",
                urgency="critical",
            )
            return {"success": False, "message": str(e), "data": None}

    def update(
        self, table_name: str, data: Dict[str, Any], where: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        if (
            not where
        ):  # Error handling for missing where clause to prevent accidental bulk updates
            return {
                "success": False,
                "message": "Update operation requires a where clause",
                "data": None,
            }

        try:
            valid_table = self._validate_identifier(table_name)
            set_clauses = [
                f"{self._validate_identifier(key)} = ?" for key in data.keys()
            ]
            set_clause = ", ".join(set_clauses)
            where_clause, where_params = self._build_where_clause(where)

            query = f"UPDATE {valid_table} SET {set_clause} {where_clause}"
            params = tuple(data.values()) + where_params

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return {
                    "success": True,
                    "message": "Record(s) updated successfully",
                    "data": {"rowcount": cursor.rowcount},
                }
        except (ValueError, sqlite3.Error) as e:
            _log_db_event(
                f"Error updating {table_name}: {e}", "error", urgency="critical"
            )
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
            return {
                "success": False,
                "message": "Delete operation requires a where clause",
                "data": None,
            }

        try:
            valid_table = self._validate_identifier(table_name)
            where_clause, params = self._build_where_clause(where)
            query = f"DELETE FROM {valid_table} {where_clause}"

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return {
                    "success": True,
                    "message": "Record(s) deleted successfully",
                    "data": {"rowcount": cursor.rowcount},
                }
        except (ValueError, sqlite3.Error) as e:
            _log_db_event(
                f"Error deleting from {table_name}: {e}", "error", urgency="critical"
            )
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
        "logs.db.sqlite3",
    ]

    # Initialize connection for each database to create the file if it doesn't exist
    for db_name in required_dbs:
        db_path = database_dir / db_name
        try:
            # Connect to create db or ensure accessibility
            with sqlite3.connect(str(db_path), timeout=5):
                pass
            logger.info(f"Database initialized: {db_name}")

            # Avoid recursive loop specifically on the logs DB
            if "logs.db" not in db_name:
                dr_logger.log(
                    "info",
                    f"Database initialized: {db_name}",
                    "system",
                    "DB",
                    "none",
                    "1.0",
                )

        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database {db_name}: {e}")
            if "logs.db" not in db_name:
                dr_logger.log(
                    "error",
                    f"Failed to initialize database {db_name}: {e}",
                    "system",
                    "DB",
                    "moderate",
                    "1.0",
                )


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
