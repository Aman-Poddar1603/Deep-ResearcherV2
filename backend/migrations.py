import logging
from typing import Literal

from main.src.store.DBManager import (
    buckets_db_manager,
    chats_db_manager,
    history_db_manager,
    main_db_manager,
    researches_db_manager,
    scrapes_db_manager,
)
from main.src.utils.DRLogger import dr_logger
from main.src.utils.version_constants import get_raw_version

LOG_SOURCE = "system"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_system_migrations_event(
    message: str,
    level: Literal["success", "error", "warning", "info"] = "info",
    urgency: Literal["none", "moderate", "critical"] = "none",
) -> None:
    """
    ## Description

    metadata. Ensures all secret-related operations are tracked with appropriate
    Internal utility function for logging secret management events with structured
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
        module="MIGRATIONS",
        app_version=get_raw_version(),
    )


# WORKSPACE MANAGEMENT


def create_workspace_tables() -> None:
    """
    Creates the workspace tables in the main database.

    Tables created:
    - `workspaces`: Stores core workspace information.
    - `workspace_connected_research`: Stores information about the connected researches.
    - `workspace_connected_chats`: Stores information about the connected chats.
    - `workspace_connected_resources`: Stores information about the connected resources including files and links.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            message="Creating workspace tables",
            urgency="none",
        )
        logger.info("Creating workspace tables...")
        main_db_manager.create_table(
            "workspaces",
            schema={
                "id": "TEXT PRIMARY KEY NOT NULL",
                "name": "TEXT NOT NULL",
                "desc": "TEXT NOT NULL",
                "icon": "TEXT",
                "accent_clr": "TEXT",
                "banner_img": "TEXT",
                "connected_bucket_id": "TEXT",
                "ai_config": "TEXT",
                "workspace_resources_id": "TEXT",
                "workspace_research_agents": "BOOLEAN DEFAULT 1",
                "workspace_chat_agents": "BOOLEAN DEFAULT 1",
                "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "connected_bucket_id"]],
        )
        logger.info("Created workspace tables...")
        logger.info("Creating workspace connected research table...")
        main_db_manager.create_table(
            "workspace_connected_research",
            schema={
                "id": "TEXT PRIMARY KEY NOT NULL",
                "workspace_id": "TEXT",
                "research_ids": "TEXT",
                "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "workspace_id", "research_ids"]],
        )
        logger.info("Created workspace connected research table...")
        logger.info("Creating workspace connected chats table...")
        main_db_manager.create_table(
            "workspace_connected_chats",
            schema={
                "id": "TEXT PRIMARY KEY NOT NULL",
                "workspace_id": "TEXT",
                "chat_session_id": "TEXT",
                "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "workspace_id", "chat_session_id"]],
        )
        logger.info("Created workspace connected chats table...")
        logger.info("Creating workspace connected resources table...")
        main_db_manager.create_table(
            "workspace_connected_resources",
            schema={
                "id": "TEXT PRIMARY KEY NOT NULL",
                "connected_bucket_id": "TEXT",
                "resource_ids": "TEXT",
                "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "connected_bucket_id"]],
        )
        logger.info("Created workspace connected resources table...")
        logger.info("Workspace tables created successfully!")

    except Exception as e:
        _log_system_migrations_event(
            message=f"Failed to create workspace tables: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.error(f"Failed to create workspace tables: {str(e)}", stack_info=True)


# HISTORY MANAGEMENT


def create_history_tables() -> None:
    """
    Creates the history tables in the history database.

    Tables created:
    - `user_usage_history`: Stores basic usage information.
    - `chat_history`: Stores recent chat history.
    - `research_history`: Stores recent research history.
    - `version_history`: Stores information about the version changes.
    - `token_count`: Stores information about the tokens used in an chat or research.
    - `ai_summaries`: Stores information about the summaries generated by AI.
    - `bucket_history`: Stores information about the Bucket history.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            message="Creating history tables...",
            level="info",
            urgency="moderate",
        )

        logger.info("Creating user_usage_history table...")
        history_db_manager.create_table(
            "user_usage_history",
            {
                "id": "TEXT PRIMARY KEY NOT NULL",
                "user_id": "TEXT",
                "workspace_id": "TEXT",
                "activity": "TEXT",
                "type": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "last_seen": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "actions": "TEXT",
                "url": "TEXT",
            },
            indexes=[["id", "user_id", "workspace_id"]],
        )
        logger.info("Created user_usage_history table")
        logger.info("Creating chat_history table...")
        history_db_manager.create_table(
            "chat_history",
            {
                "id": "TEXT PRIMARY KEY NOT NULL",
                "chat_thread_id": "TEXT",
                "workspace_id": "TEXT",
                "activity": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "last_seen": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "actions": "TEXT",
                "url": "TEXT",
            },
            indexes=[["id", "chat_thread_id", "workspace_id"]],
        )
        logger.info("Created chat_history table")
        logger.info("Creating research_history table...")
        history_db_manager.create_table(
            "research_history",
            {
                "id": "TEXT PRIMARY KEY NOT NULL",
                "research_id": "TEXT",
                "workspace_id": "TEXT",
                "activity": "TEXT",
                "status": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "last_seen": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "actions": "TEXT",
                "url": "TEXT",
            },
            indexes=[["id", "research_id", "workspace_id"]],
        )
        logger.info("Created research_history table")
        logger.info("Creating version_history table...")
        history_db_manager.create_table(
            "version_history",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "version": "TEXT NOT NULL UNIQUE",
                "changes": "TEXT NOT NULL",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id"]],
        )
        logger.info("Created version_history table")
        logger.info("Creating token_count table...")
        history_db_manager.create_table(
            "token_count",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "workspace_id": "TEXT",
                "chat_or_research_id": "TEXT",
                "chat_or_research_type": "TEXT",
                "token_type": "TEXT",
                "count": "INTEGER",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "workspace_id", "chat_or_research_id"]],
        )
        logger.info("Created token_count table")
        logger.info("Creating ai_summaries table...")
        history_db_manager.create_table(
            "ai_summaries",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "workspace_id": "TEXT",
                "prompt": "TEXT",
                "model": "TEXT",
                "time_taken_sec": "INTEGER",
                "status": "TEXT",
                "tokens_used": "INTEGER",
                "original_test": "TEXT",
                "summary": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "workspace_id", "research_id"], ["original_test", "id"]],
        )
        logger.info("Created ai_summaries table")
        logger.info("Creating bucket_history table...")
        history_db_manager.create_table(
            "bucket_history",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "workspace_id": "TEXT",
                "bucket_id": "TEXT",
                "activity": "TEXT",
                "file_path": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP",
            },
            indexes=[["id", "workspace_id", "bucket_id"], ["activity", "bucket_id"]],
        )
        logger.info("Created bucket_history table")
    except Exception as e:
        _log_system_migrations_event(
            message=f"Failed to create history tables: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.error(f"Failed to create history tables: {str(e)}", stack_info=True)


# CHAT MANAGEMENT


def create_chat_tables() -> None:
    """
    Creates the chat tables in the chat database.

    Tables created:
    - `chat_threads`: Stores all the chat threads.
    - `chat_messages`: Stores all the chat messages.
    - `chat_attachments`: Stores all the chat attachments.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            message="Creating chat tables...",
            level="info",
            urgency="moderate",
        )
        logger.info("Creating chat_threads table...")
        chats_db_manager.create_table(
            "chat_threads",
            {
                "thread_id": "TEXT PRIMARY KEY",
                "thread_title": "TEXT",
                "workspace_id": "TEXT",
                "user_id": "TEXT",
                "metadata": "TEXT",
                "token_count": "INTEGER",
                "is_pinned": "BOOLEAN",
                "pinned_at": "DATETIME",
                "pinned_order": "INTEGER",
                "created_by": "TEXT",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
            },
            indexes=[["thread_id"]],
        )
        logger.info("Created chat_threads table!")
        logger.info("Creating chat_messages table...")
        chats_db_manager.create_table(
            "chat_messages",
            {
                "message_id": "TEXT PRIMARY KEY",
                "thread_id": "TEXT",
                "message_seq": "INTEGER",
                "parent_id": "TEXT",
                "role": "TEXT",
                "content": "TEXT",
                "citations": "TEXT",
                "token_count": "INTEGER",
                "attachments": "TEXT",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
            },
            indexes=[["thread_id", "message_seq"]],
        )
        logger.info("Created chat_messages table!")
        logger.info("Creating chat_attachments table...")
        chats_db_manager.create_table(
            "chat_attachments",
            {
                "attachment_id": "TEXT PRIMARY KEY",
                "message_id": "TEXT",
                "attachment_type": "TEXT",
                "attachment_path": "TEXT",  # may be external file, links or internal research
                "attachment_size": "INTEGER",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
            },
            indexes=[["message_id"]],
        )
        logger.info("Created chat_attachments table!")
    except Exception as e:
        _log_system_migrations_event(
            message=f"Failed to create chat tables: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info("Failed to create chat_attachments table!")


# RESEARCH MANAGEMENT


def create_research_tables() -> None:
    """
    Creates the Research tables in the research database.

    Tables created:
    - `researches`: Stores all the core research information.
    - `research_templates`: Stores information about the research templates.
    - `research_plans`: Stores information about the research plans.
    - `research_workflow`: Stores information about the reserch workflow per research.
    - `research_metadata`: Stores information about the additional metadata for researches.
    - `research_sources`: Stores information about the research sources.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            "Creating researches table!!!",
            level="info",
            urgency="none",
        )
        logger.info("Creating researches table")
        researches_db_manager.create_table(
            "researches",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "title": "TEXT",
                "desc": "TEXT",
                "prompt": "TEXT",
                "sources": "TEXT",
                "workspace_id": "TEXT",
                "artifacts": "TEXT",
                "chat_access": "BOOLEAN DEFAULT TRUE",
                "background_processing": "BOOLEAN DEFAULT TRUE",
                "research_template_id": "TEXT",
                "custom_instructions": "TEXT",
                "prompt_order": "TEXT",
            },
            indexes=[["id", "workspace_id"]],
        )
        logger.info("Created researches table..")
        logger.info("Creating research_templates table...")
        researches_db_manager.create_table(
            "research_templates",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "title": "TEXT",
                "desc": "TEXT",
                "template": "TEXT",
                "total_researches": "INTEGER DEFAULT 0",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "workspace_id"]],
        )
        logger.info("Created research_templates table...")
        logger.info("Creating research_plans table...")
        researches_db_manager.create_table(
            "research_plans",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "title": "TEXT",
                "desc": "TEXT",
                "plan": "TEXT",
                "workflow": "TEXT",
                "workspace_id": "TEXT",
                "research_template_id": "TEXT",
                "prompt_order": "TEXT",
            },
        )
        logger.info("Created research_plans table...")
        logger.info("Creating research_workflow table...")
        history_db_manager.create_table(
            "research_workflow",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "workspace_id": "TEXT",
                "research_id": "TEXT",
                "workflow": "TEXT",
                "steps": "INTEGER",
                "tokens_used": "INTEGER",
                "resources_used": "INTEGER",
                "time_taken_sec": "INTEGER",
                "success": "BOOLEAN",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
            indexes=[["id", "workspace_id", "research_id"]],
        )
        logger.info("Created research_workflow table")
        logger.info("Creating research_metadata table...")
        researches_db_manager.create_table(
            "research_metadata",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "models": "TEXT",
                "workspace_id": "TEXT",
                "research_id": "TEXT",
                "connected_bucket": "TEXT",
                "time_taken_sec": "INTEGER",
                "token_count": "INTEGER",
                "source_count": "INTEGER",
                "websites_count": "INTEGER",
                "file_count": "INTEGER",
                "citations": "TEXT",
                "exported": "TEXT",
                "status": "BOOLEAN",
                "chats_referenced": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        )
        logger.info("Created research_metadata table...")
        logger.info("Creating research_sources table...")
        researches_db_manager.create_table(
            "research_sources",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "research_id": "TEXT",
                "source_type": "TEXT",
                "source_url": "TEXT",
                "source_content": "TEXT",
                "source_citations": "TEXT",
                "source_vector_id": "TEXT",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        )
        logger.info("Created research_sources table...")

    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create research tables: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create research tables: {str(e)}")


# FILE MANAGEMENT


def create_bucket_tables() -> None:
    """
    Creates the Bucket tables in the bucket database.

    Tables created:
    - `buckets`: Stores core bucket information.
    - `bucket_items`: Stores information about the bucket connected items.

    Returns: None
    """

    try:
        _log_system_migrations_event(
            "Creating bucket tables...",
            level="info",
            urgency="none",
        )
        logger.info("Creating bucket tables...")
        buckets_db_manager.create_table(
            "buckets",
            schema={
                "id": "TEXT PRIMARY KEY",
                "name": "TEXT NOT NULL",
                "allowed_file_types": "TEXT NOT NULL",
                "description": "TEXT",
                "deletable": "BOOLEAN DEFAULT TRUE NOT NULL",
                "status": "BOOLEAN DEFAULT TRUE NOT NULL",
                "total_files": "INTEGER DEFAULT 0 NOT NULL",
                "total_size": "INTEGER DEFAULT 0 NOT NULL",
                "created_by": "TEXT NOT NULL",
                "created_at": "DATETIME NOT NULL",
                "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL",
            },
            indexes=[["id", "name"], ["allowed_file_types"]],
        )
        logger.info("Created buckets table")
        logger.info("Creating bucket items table...")
        buckets_db_manager.create_table(
            "bucket_items",
            schema={
                "id": "TEXT PRIMARY KEY",
                "bucket_id": "TEXT NOT NULL",
                "connected_workspace_ids": "TEXT",
                "source": "TEXT",
                "file_name": "TEXT NOT NULL",
                "file_path": "TEXT NOT NULL",
                "file_format": "TEXT NOT NULL",
                "file_size": "INTEGER NOT NULL",
                "summary": "TEXT",
                "is_deleted": "BOOLEAN DEFAULT FALSE NOT NULL",
                "created_by": "TEXT NOT NULL",
                "created_at": "DATETIME NOT NULL",
                "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL",
            },
            indexes=[["id", "bucket_id"], ["created_by"]],
        )
        logger.info("Created bucket items table")

    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create bucket tables: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create bucket tables: {str(e)}")


# SETTINGS


def create_settings_table() -> None:
    """
    Creates the Settings tables in the main database.

    Tables created:
    - `settings`: Stores core settings information to manage the Deep Research internal Workflow.

    Returns: None
    """

    try:
        _log_system_migrations_event(
            "Creating settings table...",
            level="info",
            urgency="none",
        )
        logger.info("Creating settings table...")
        main_db_manager.create_table(
            "settings",
            {
                # User settings
                "user_name": "TEXT",
                "user_email": "TEXT",
                "user_bio": "TEXT",
                # Appearance settings
                "theme": "TEXT",
                "color_mode": "TEXT",
                # Web Crawling settings
                "max_depth_search": "INTEGER",
                # Report settings
                "default_report_fmt": "TEXT",
                "default_research_template": "TEXT",
                "default_bucket": "TEXT",
                # Notification settings
                "notification_on_complete_research": "BOOLEAN DEFAULT TRUE",
                "show_error_on_alerts": "BOOLEAN DEFAULT TRUE",
                "sound_effect": "BOOLEAN DEFAULT TRUE",
                # AI Settings
                "default_model": "TEXT",
                "ai_name": "TEXT",
                "ai_personality": "TEXT",
                "ai_custom_prompt": "TEXT",
                "stream_response": "BOOLEAN DEFAULT TRUE",
                "show_citations": "BOOLEAN DEFAULT TRUE",
                "thinking_in_chats": "BOOLEAN DEFAULT TRUE",
                # Data Settings:
                "keep_backup": "BOOLEAN DEFAULT TRUE",
                "temperory_data_retention": "INTEGER DEFAULT 30",
            },
        )
        logger.info("Settings table created successfully.")
    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create settings table: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create settings table: {str(e)}")


# DBMS


def create_scrapes_database() -> None:
    """
    Creates the Scrapes tables in the main database.

    Tables created:
    - `scrapes`: Stores the crawling information information.
    - `scrapes_metadata`: Stores the metadata of the crawling process.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            "Creating Scapes table...",
            level="info",
            urgency="none",
        )
        logger.info("Creating Scapes table...")
        scrapes_db_manager.create_table(
            "scrapes",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "url": "TEXT",
                "title": "TEXT",
                "favicon": "TEXT",
                "content": "TEXT",
                "metadata": "TEXT",
                "is_vector_stored": "BOOLEAN DEFAULT FALSE",
                "origin_research_id": "TEXT",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            },
            indexes=[["origin_research_id", "id"], ["url", "title", "id"]],
        )
        logger.info("Scapes table created successfully")
        logger.info("Creating scrapes_metadata table...")
        scrapes_db_manager.create_table(
            "scrapes_metadata",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "search_engine": "TEXT DEFAULT 'SearXNG'",
                "clawler": "TEXT DEFAULT 'crawl4ai'",
                "clawling_time_sec": "NUMBER DEFAULT 0",
                "scrape_id": "TEXT",
                "no_words": "NUMBER",
                "chats_cited": "TEXT",
                "research_cited": "TEXT",
                "num_crawls": "NUMBER",
                "num_cited": "NUMBER",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            },
            indexes=[["id"]],
        )
        logger.info("Scrapes_metadata table created successfully")

    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create settings table: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create settings table: {str(e)}")


def create_database_stats_tables() -> None:
    """
    Creates the database stats tables in the main database.

    Tables created:
    - `db_stats`: Stores the database statistics.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            "Creating db_stats table",
            level="info",
            urgency="none",
        )
        logger.info("Creating db_stats table")
        main_db_manager.create_table(
            "db_stats",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "name": "TEXT NOT NULL",
                "desc": "TEXT",
                "type": "TEXT NOT NULL",
                "total_tables": "INTEGER NOT NULL",
                "total_rows": "INTEGER NOT NULL",
                "total_disk_size": "INTEGER NOT NULL",
                "created_at": "TEXT NOT NULL",
                "updated_at": "TEXT NOT NULL",
                "status": "TEXT NOT NULL",
            },
        )
        logger.info("db_stats table created successfully")

    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create db_stats table: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create db_stats table: {str(e)}")


# SEARCH MANAGEMENT


def create_search_tables() -> None:
    """
    Creates the search tables in the history database.

    Tables created:
    - `searches`: Stores the search information.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            "Creating searches table",
            level="info",
            urgency="none",
        )
        logger.info("Creating searches table")
        history_db_manager.create_table(
            "searches",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "query": "TEXT NOT NULL",
                "is_aimode": "BOOLEAN NOT NULL DEFAULT 1",
                "ai_summary": "TEXT",
                "ai_citations": "TEXT",
                "total_results": "INTEGER DEFAULT 0",
                "results": "TEXT NOT NULL",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        )
        logger.info("searches table created successfully")

    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create searches table: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create searches table: {str(e)}")


# Utilities
def create_backgraound_running_task_table() -> None:
    """
    Creates the search tables in the history database.

    Tables created:
    - `bg_process`: Stores the background running task information.

    Returns: None
    """
    try:
        _log_system_migrations_event(
            "Creating bg_process table",
            level="info",
            urgency="none",
        )
        logger.info("Creating bg_process table")
        main_db_manager.create_table(
            "bg_process",
            {
                "id": "TEXT PRIMARY KEY UNIQUE",
                "task": "TEXT NOT NULL",
                "workspace_id": "TEXT NOT NULL",
                "status": "TEXT NOT NULL",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            },
        )
        logger.info("bg_process table created successfully")

    except Exception as e:
        _log_system_migrations_event(
            f"Failed to create bg_process table: {str(e)}",
            level="error",
            urgency="critical",
        )
        logger.info(f"Failed to create bg_process table: {str(e)}")


if __name__ == "__main__":
    logger.info("Starting database migrations...")

    create_workspace_tables()
    create_history_tables()
    create_chat_tables()
    create_research_tables()
    create_bucket_tables()
    create_settings_table()
    create_scrapes_database()
    create_database_stats_tables()
    create_search_tables()
    create_backgraound_running_task_table()

    logger.info("Database migrations completed.")
