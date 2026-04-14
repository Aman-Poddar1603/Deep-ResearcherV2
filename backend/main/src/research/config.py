import os
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class ResearchSettings(BaseSettings):
    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_BASE_URL", "OLLAMA_HOST"),
    )
    OLLAMA_MODEL: str = Field(
        default="gemma4:e2b",
        validation_alias=AliasChoices("OLLAMA_MODEL", "CHAT_MODEL"),
    )
    OLLAMA_EMBED_MODEL: str = Field(
        default="embeddinggemma:latest",
        validation_alias=AliasChoices("OLLAMA_EMBED_MODEL", "EMBED_MODEL"),
    )
    OLLAMA_VISION_MODEL: str = Field(
        default="",
        validation_alias=AliasChoices("OLLAMA_VISION_MODEL", "VISION_MODEL"),
    )

    # Groq Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Gemini Configuration
    GEMINI_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    GEMINI_ARTIFACT_MODEL: str = "models/gemini-2.0-flash-lite"
    GEMINI_EMBED_MODEL: str = "models/text-embedding-004"

    # MCP Configuration
    MCP_SERVER_URL: str = "http://localhost:8001/mcp"
    MCP_TRANSPORT: str = "http"
    MCP_TIMEOUT_SECONDS: int = 86400
    MCP_SERVER_COMMAND: str = ""
    MCP_SERVER_ARGS: str = ""
    MCP_SERVER_CWD: str = ""

    # Storage Configuration
    CHROMA_PATH: str = "./main/src/store/vector/chroma"
    REDIS_URL: str = "redis://localhost:6379"
    TEMP_RESEARCH_BASE_DIR: str = ".temp"

    # Research Loop Configuration
    MAX_QA_ROUNDS: int = 7
    MAX_PLAN_REFACTOR_ROUNDS: int = 3
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    RAG_TOP_K: int = 6
    SYNTHESIS_UPDATE_INTERVAL: int = 5
    SYNTHESIS_PREVIEW_CHARS: int = 320

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = ResearchSettings()
