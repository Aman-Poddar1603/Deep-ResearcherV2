"""
RAG setup using LangChain's ChromaDB wrapper + OllamaEmbeddings.

Per-research collection: research_{research_id}
Chunks include metadata: research_id, step_index, source_url, partial
"""

import logging

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.tools.retriever import create_retriever_tool
from langchain_core.documents import Document
from langchain_core.tools import BaseTool

from research.config import settings

logger = logging.getLogger(__name__)


def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.OLLAMA_EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


def get_vectorstore(research_id: str, read_only: bool = False) -> Chroma:
    return Chroma(
        collection_name=f"research_{research_id}",
        embedding_function=get_embeddings(),
        persist_directory=settings.CHROMA_PATH,
    )


def get_retriever_tool(research_id: str) -> BaseTool:
    vectorstore = get_vectorstore(research_id)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.RAG_TOP_K},
    )
    return create_retriever_tool(
        retriever=retriever,
        name="rag_search",
        description=(
            "Search the gathered knowledge base for relevant information "
            "collected so far in this research session."
        ),
    )


def make_splitter() -> RecursiveCharacterTextSplitter:
    """
    Semantic-recursive splitter:
    - Tries natural boundaries first (double newline, newline, sentence, word)
    - Falls back to character splits if needed
    - 15% token overlap to preserve cross-chunk context
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )


def chunk_and_index(
    research_id: str,
    text: str,
    source_url: str,
    step_index: int,
    partial: bool = False,
) -> int:
    """
    Chunk text and add to ChromaDB. Returns number of vectors written.
    This is called from BG workers — it's synchronous (ChromaDB is sync).
    """
    splitter = make_splitter()
    chunks = splitter.split_text(text)
    if not chunks:
        return 0

    docs = [
        Document(
            page_content=chunk,
            metadata={
                "research_id": research_id,
                "step_index": step_index,
                "source_url": source_url,
                "partial": partial,
            },
        )
        for chunk in chunks
    ]

    vectorstore = get_vectorstore(research_id)
    vectorstore.add_documents(docs)
    logger.info(
        "[rag] Indexed %d chunks for research=%s step=%d source=%s",
        len(docs),
        research_id,
        step_index,
        source_url,
    )
    return len(docs)


def retrieve_for_coverage_check(research_id: str, query: str) -> list[Document]:
    """Used by Orc2 to verify plan step coverage."""
    vectorstore = get_vectorstore(research_id)
    return vectorstore.similarity_search(query, k=settings.RAG_TOP_K)
