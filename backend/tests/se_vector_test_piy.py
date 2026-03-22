"""
search_engine_usage.py — Deep Researcher v2
=============================================
Comprehensive usage examples for SearchEngine metadata filtering.

ChromaDB WHERE clause operators
--------------------------------
Equality          : {"key": {"$eq": "value"}}       — exact match
Inequality        : {"key": {"$ne": "value"}}        — not equal
Numeric range     : {"key": {"$gt": 5}}              — greater than
                    {"key": {"$gte": 5}}             — greater than or equal
                    {"key": {"$lt": 10}}             — less than
                    {"key": {"$lte": 10}}            — less than or equal
Set membership    : {"key": {"$in": ["a", "b"]}}     — value in list
Set exclusion     : {"key": {"$nin": ["a", "b"]}}    — value not in list
Logical AND       : {"$and": [{...}, {...}]}          — all conditions must match
Logical OR        : {"$or":  [{...}, {...}]}          — any condition must match

All metadata values must be str / int / float / bool.
Nested dicts are not supported by ChromaDB's filter engine.
"""

import asyncio
from main.src.store.vector import ingestion_service, search_engine


# ===========================================================================
# 1.  INGEST SAMPLE DATA (run once to populate collections)
# ===========================================================================


async def seed_sample_data() -> None:
    """
    Seed the four collections with representative documents so the search
    examples below have data to work with.

    Injects:
        - 3 website articles with ``domain`` and ``language`` metadata
        - 2 PDF research papers with ``year`` and ``author`` metadata
        - 2 images        with ``category`` and ``resolution`` metadata
        - 2 custom notes  with ``project`` and ``priority`` metadata
    """
    await ingestion_service.start(num_workers=2)

    # ── Websites ────────────────────────────────────────────────────────────
    await ingestion_service.ingest_website(
        url="https://example.com/transformers",
        content="""# Transformer Architecture
The transformer model was introduced in 'Attention is All You Need'.

## Self-Attention
Self-attention allows the model to relate different positions of a sequence.

## Multi-Head Attention
Running attention in parallel across multiple heads captures richer patterns.
""",
        extra_meta={"domain": "ml", "language": "en", "year": 2024},
    )

    await ingestion_service.ingest_website(
        url="https://example.com/diffusion",
        content="""# Diffusion Models
Diffusion models iteratively denoise a signal to generate images.

## DDPM
Denoising Diffusion Probabilistic Models define a forward noising process.
""",
        extra_meta={"domain": "cv", "language": "en", "year": 2023},
    )

    await ingestion_service.ingest_website(
        url="https://ejemplo.com/redes",
        content="""# Redes Neuronales
Las redes neuronales son inspiradas por el cerebro humano.
""",
        extra_meta={"domain": "ml", "language": "es", "year": 2022},
    )

    # ── PDFs ────────────────────────────────────────────────────────────────
    # (Normally you'd pass a real file path; we ingest pre-split text here
    #  by using ingest_custom routed to the pdfs collection directly via
    #  the low-level API for demo purposes.)
    await ingestion_service.ingest_custom(
        text="Scaling laws for neural language models suggest loss scales as a power law with compute.",
        source="scaling_laws.pdf",
        extra_meta={
            "collection_override": "pdfs",
            "author": "Kaplan",
            "year": 2020,
            "pages": 20,
        },
    )

    await ingestion_service.ingest_custom(
        text="Constitutional AI aligns language models using a set of principles rather than human feedback.",
        source="cai_paper.pdf",
        extra_meta={
            "collection_override": "pdfs",
            "author": "Anthropic",
            "year": 2022,
            "pages": 35,
        },
    )

    # ── Custom notes ────────────────────────────────────────────────────────
    await ingestion_service.ingest_custom(
        text="Meeting notes: discussed retrieval-augmented generation pipeline for v2 release.",
        source="notes",
        extra_meta={"project": "deep-researcher", "priority": 1, "tag": "rag"},
    )

    await ingestion_service.ingest_custom(
        text="TODO: benchmark SigLIP vs CLIP embeddings on internal image dataset.",
        source="notes",
        extra_meta={"project": "deep-researcher", "priority": 2, "tag": "embeddings"},
    )

    # Allow workers to drain
    await asyncio.sleep(3)
    await ingestion_service.stop()
    print("✅  Sample data seeded.")


# ===========================================================================
# 2.  BASIC TEXT SEARCH  (no metadata filter)
# ===========================================================================


async def example_basic_search() -> None:
    """
    Run a plain text similarity search across the default collections
    (websites, pdfs, custom) with no metadata constraints.

    Returns the top-5 most semantically similar chunks, ranked by
    cosine similarity score descending.
    """
    ctx = await search_engine.search(
        query="attention mechanism in transformers",
        n_results=5,
    )

    print(f"\n[Basic Search]  total hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  [{hit['collection']:8}]  score={hit['score']:.3f}  id={hit['id'][:16]}…"
        )
        print(f"            doc='{(hit['document'] or '')[:80]}…'")


# ===========================================================================
# 3.  EQUALITY FILTER  — match one exact metadata value
# ===========================================================================


async def example_filter_by_domain() -> None:
    """
    Search only within website chunks whose ``domain`` metadata equals ``'ml'``.

    Useful when you want to restrict results to a topic vertical without
    knowing the exact document IDs ahead of time.

    WHERE clause: ``{"domain": {"$eq": "ml"}}``
    """
    ctx = await search_engine.search(
        query="neural network training",
        collections=["websites"],
        n_results=10,
        where={"domain": {"$eq": "ml"}},
    )

    print(f"\n[domain == 'ml']  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  score={hit['score']:.3f}  domain={hit['metadata'].get('domain')}  url={hit['metadata'].get('source_uri', '')[:50]}"
        )


# ===========================================================================
# 4.  INEQUALITY FILTER  — exclude a value
# ===========================================================================


async def example_exclude_language() -> None:
    """
    Search websites but exclude non-English content by filtering out
    chunks where ``language != 'en'``.

    WHERE clause: ``{"language": {"$ne": "es"}}``
    """
    ctx = await search_engine.search(
        query="deep learning models",
        collections=["websites"],
        n_results=10,
        where={"language": {"$ne": "es"}},
    )

    print(f"\n[language != 'es']  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(f"  score={hit['score']:.3f}  language={hit['metadata'].get('language')}")


# ===========================================================================
# 5.  NUMERIC RANGE FILTER  — year >= 2023
# ===========================================================================


async def example_filter_recent_content() -> None:
    """
    Retrieve only content published in 2023 or later by filtering on
    the integer ``year`` metadata field.

    Suitable for time-sensitive research where stale information is
    less useful.

    WHERE clause: ``{"year": {"$gte": 2023}}``
    """
    ctx = await search_engine.search(
        query="generative AI image synthesis",
        collections=["websites", "pdfs"],
        n_results=10,
        where={"year": {"$gte": 2023}},
    )

    print(f"\n[year >= 2023]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  score={hit['score']:.3f}  year={hit['metadata'].get('year')}  coll={hit['collection']}"
        )


# ===========================================================================
# 6.  NUMERIC RANGE — between two values (combined $gte / $lte)
# ===========================================================================


async def example_filter_year_range() -> None:
    """
    Search PDFs published between 2020 and 2022 (inclusive) by combining
    ``$gte`` and ``$lte`` operators inside a ``$and`` clause.

    WHERE clause::

        {
            "$and": [
                {"year": {"$gte": 2020}},
                {"year": {"$lte": 2022}}
            ]
        }
    """
    ctx = await search_engine.search(
        query="language model alignment safety",
        collections=["pdfs"],
        n_results=10,
        where={
            "$and": [
                {"year": {"$gte": 2020}},
                {"year": {"$lte": 2022}},
            ]
        },
    )

    print(f"\n[2020 <= year <= 2022 in pdfs]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  score={hit['score']:.3f}  author={hit['metadata'].get('author')}  year={hit['metadata'].get('year')}"
        )


# ===========================================================================
# 7.  SET MEMBERSHIP  — $in operator
# ===========================================================================


async def example_filter_specific_authors() -> None:
    """
    Search PDF chunks authored by either ``'Kaplan'`` or ``'Anthropic'``
    using the ``$in`` operator.

    Equivalent to SQL:  WHERE author IN ('Kaplan', 'Anthropic')

    WHERE clause: ``{"author": {"$in": ["Kaplan", "Anthropic"]}}``
    """
    ctx = await search_engine.search(
        query="training compute optimal models",
        collections=["pdfs"],
        n_results=10,
        where={"author": {"$in": ["Kaplan", "Anthropic"]}},
    )

    print(f"\n[author in ['Kaplan','Anthropic']]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(f"  score={hit['score']:.3f}  author={hit['metadata'].get('author')}")


# ===========================================================================
# 8.  SET EXCLUSION  — $nin operator
# ===========================================================================


async def example_exclude_projects() -> None:
    """
    Fetch custom notes that do NOT belong to the ``'deep-researcher'``
    project using the ``$nin`` (not-in) operator.

    WHERE clause: ``{"project": {"$nin": ["deep-researcher"]}}``
    """
    ctx = await search_engine.search(
        query="embedding benchmarks",
        collections=["custom"],
        n_results=10,
        where={"project": {"$nin": ["deep-researcher"]}},
    )

    print(f"\n[project NOT IN ['deep-researcher']]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(f"  score={hit['score']:.3f}  project={hit['metadata'].get('project')}")


# ===========================================================================
# 9.  LOGICAL AND  — multiple conditions must all be true
# ===========================================================================


async def example_and_filter() -> None:
    """
    Search website chunks that are BOTH in the ``'ml'`` domain AND written
    in English (``language == 'en'``).

    Uses the ``$and`` logical operator to combine two independent conditions.
    All sub-conditions must be satisfied for a document to qualify.

    WHERE clause::

        {
            "$and": [
                {"domain":   {"$eq": "ml"}},
                {"language": {"$eq": "en"}}
            ]
        }
    """
    ctx = await search_engine.search(
        query="self-attention mechanism",
        collections=["websites"],
        n_results=10,
        where={
            "$and": [
                {"domain": {"$eq": "ml"}},
                {"language": {"$eq": "en"}},
            ]
        },
    )

    print(f"\n[domain='ml' AND language='en']  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  score={hit['score']:.3f}  domain={hit['metadata'].get('domain')}  lang={hit['metadata'].get('language')}"
        )


# ===========================================================================
# 10.  LOGICAL OR  — any condition may be true
# ===========================================================================


async def example_or_filter() -> None:
    """
    Search across websites where the domain is either ``'ml'`` OR ``'cv'``.

    Uses the ``$or`` logical operator — a document matches if at least one
    sub-condition is satisfied.

    WHERE clause::

        {
            "$or": [
                {"domain": {"$eq": "ml"}},
                {"domain": {"$eq": "cv"}}
            ]
        }
    """
    ctx = await search_engine.search(
        query="image generation neural networks",
        collections=["websites"],
        n_results=10,
        where={
            "$or": [
                {"domain": {"$eq": "ml"}},
                {"domain": {"$eq": "cv"}},
            ]
        },
    )

    print(f"\n[domain='ml' OR domain='cv']  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(f"  score={hit['score']:.3f}  domain={hit['metadata'].get('domain')}")


# ===========================================================================
# 11.  COMPLEX COMPOUND  — AND + OR nested together
# ===========================================================================


async def example_compound_filter() -> None:
    """
    Demonstrate a nested compound filter combining ``$and`` and ``$or``.

    Retrieves website chunks that satisfy ALL of:
        1. Written in English
        2. Either domain is 'ml' OR the year is >= 2024

    This pattern is useful for building dynamic filter UIs where multiple
    independent facets (language, topic, recency) must be respected at once.

    WHERE clause::

        {
            "$and": [
                {"language": {"$eq": "en"}},
                {
                    "$or": [
                        {"domain": {"$eq": "ml"}},
                        {"year":   {"$gte": 2024}}
                    ]
                }
            ]
        }
    """
    ctx = await search_engine.search(
        query="attention is all you need",
        collections=["websites"],
        n_results=10,
        where={
            "$and": [
                {"language": {"$eq": "en"}},
                {
                    "$or": [
                        {"domain": {"$eq": "ml"}},
                        {"year": {"$gte": 2024}},
                    ]
                },
            ]
        },
    )

    print(f"\n[language='en' AND (domain='ml' OR year>=2024)]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        meta = hit["metadata"]
        print(
            f"  score={hit['score']:.3f}  lang={meta.get('language')}  domain={meta.get('domain')}  year={meta.get('year')}"
        )


# ===========================================================================
# 12.  PRIORITY FILTER  — numeric ordering on custom notes
# ===========================================================================


async def example_high_priority_notes() -> None:
    """
    Retrieve only high-priority custom notes where ``priority <= 1``.

    Demonstrates numeric ``$lte`` filtering on an integer metadata field —
    useful for task/note management integrations where urgency is encoded
    numerically (1 = highest priority).

    WHERE clause: ``{"priority": {"$lte": 1}}``
    """
    ctx = await search_engine.search(
        query="RAG pipeline retrieval",
        collections=["custom"],
        n_results=10,
        where={"priority": {"$lte": 1}},
    )

    print(f"\n[priority <= 1 in custom]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  score={hit['score']:.3f}  priority={hit['metadata'].get('priority')}  tag={hit['metadata'].get('tag')}"
        )


# ===========================================================================
# 13.  IMAGE SEARCH  (no metadata filtering — images use SigLIP embeddings)
# ===========================================================================


async def example_image_search() -> None:
    """
    Perform visual similarity search against the ``images`` collection.

    Image search does NOT support ``where`` metadata filtering through the
    same interface — SigLIP embeddings live in a separate cosine space.
    Pass a local image file path; the engine embeds it via the SigLIP ONNX
    model in a background thread and returns the nearest stored images.

    Note
    ----
    Replace the path below with a real image file to test locally.
    """
    ctx = await search_engine.search_by_image(
        file_path="/tmp/query_diagram.png",
        n_results=5,
    )

    print(f"\n[Image Search]  hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  score={hit['score']:.3f}  label={hit['metadata'].get('label')}  source={hit['metadata'].get('source_uri', '')[:50]}"
        )


# ===========================================================================
# 14.  SEARCH ALL COLLECTIONS  — single query, every collection at once
# ===========================================================================


async def example_search_all() -> None:
    """
    Broadcast a single query across ALL text collections simultaneously
    (websites, pdfs, custom) using ``asyncio.gather`` under the hood.

    Results from every collection are merged into one ranked list ordered
    by cosine similarity score.  Useful for general-purpose research agents
    that should not be scoped to a specific content type.
    """
    ctx = await search_engine.search_all_collections(
        query="scaling laws compute optimal training",
        n_results=5,
    )

    print(f"\n[All Collections]  total merged hits: {ctx['total']}")
    for hit in ctx["hits"]:
        print(
            f"  [{hit['collection']:8}]  score={hit['score']:.3f}  doc='{(hit['document'] or '')[:70]}…'"
        )


# ===========================================================================
# Entry point
# ===========================================================================


async def main() -> None:
    """
    Run all search examples in sequence.

    In a real application you would call only the examples relevant to
    your feature, not all of them sequentially.
    """
    # Uncomment the line below to populate collections first:
    # await seed_sample_data()

    await example_basic_search()
    await example_filter_by_domain()
    await example_exclude_language()
    await example_filter_recent_content()
    await example_filter_year_range()
    await example_filter_specific_authors()
    await example_exclude_projects()
    await example_and_filter()
    await example_or_filter()
    await example_compound_filter()
    await example_high_priority_notes()
    await example_image_search()
    await example_search_all()

    await search_engine.close()


if __name__ == "__main__":
    asyncio.run(main())
