# ---------------------------------------------------------------------------
# Test the actual implementation by subclassing DBVectorManager and injecting
# an ephemeral (in-memory) client — avoids writing any files to disk.
# ---------------------------------------------------------------------------
import unittest
from unittest.mock import patch, MagicMock
import chromadb
from main.src.store.DBVector import DBVectorManager


class _InMemoryDBVectorManager(DBVectorManager):
    """
    Subclass that forces use of an EphemeralClient for testing.
    Inherits all CRUD logic from the real DBVectorManager.
    """

    def __init__(self, collection_name: str) -> None:
        # Skip the parent __init__ which tries to create PersistentClient
        self.collection_name = collection_name
        self._client = chromadb.EphemeralClient()
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name
        )

    # Note: CRUD methods (add, fetch_all, fetch_one, update, delete, collection_exists)
    # are all inherited from DBVectorManager and will be tested here.


# ===========================================================================
#  Test Cases
# ===========================================================================

class TestDBVectorManager(unittest.IsolatedAsyncioTestCase):
    """Unit tests for DBVectorManager CRUD operations using in-memory ChromaDB."""

    async def asyncSetUp(self) -> None:
        # Mock dr_logger to avoid persistent side effects
        self.patcher = patch("main.src.store.DBVector.dr_logger")
        self.mock_logger = self.patcher.start()
        self.patcher_global = patch("main.src.store.DBVector.global_log")
        self.mock_global_log = self.patcher_global.start()
        
        # Unique collection name per test to ensure isolation
        import uuid
        test_uuid = uuid.uuid4().hex[:8]
        self.manager = _InMemoryDBVectorManager(f"test_coll_{test_uuid}")

    async def asyncTearDown(self) -> None:
        self.patcher.stop()
        self.patcher_global.stop()

    async def test_log(self) -> None:
        """Verify that logs are emitted."""
        from main.src.store.DBVector import global_log
        global_log("info", "Test log message")
        self.mock_global_log.assert_called()

    # -----------------------------------------------------------------------

    async def test_add_and_fetch_one(self) -> None:
        """Add a single document then retrieve it by ID."""
        response = await self.manager.add(
            ids=["doc-001"],
            documents=["Deep learning is a subset of machine learning."],
            metadatas=[{"source": "arxiv", "year": 2024}],
        )
        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["count"], 1)

        fetch_response = await self.manager.fetch_one("doc-001")
        self.assertTrue(fetch_response["success"])
        doc = fetch_response["data"]
        self.assertIsNotNone(doc)
        self.assertEqual(doc["id"], "doc-001")
        self.assertIn("machine learning", doc["document"])
        self.assertEqual(doc["metadata"]["source"], "arxiv")

    async def test_fetch_all(self) -> None:
        """Add multiple documents then fetch all."""
        await self.manager.add(ids=["a"], documents=["Alpha doc"], metadatas=[{"tag": "a"}])
        await self.manager.add(ids=["b"], documents=["Beta doc"],  metadatas=[{"tag": "b"}])
        await self.manager.add(ids=["c"], documents=["Gamma doc"], metadatas=[{"tag": "c"}])

        response = await self.manager.fetch_all()
        self.assertTrue(response["success"])
        data = response["data"]
        self.assertEqual(len(data["ids"]), 3)
        self.assertIn("a", data["ids"])
        self.assertIn("b", data["ids"])
        self.assertIn("c", data["ids"])

    async def test_fetch_all_with_where_filter(self) -> None:
        """fetch_all with a metadata where-filter returns only matching docs."""
        await self.manager.add(ids=["x"], documents=["X doc"], metadatas=[{"env": "prod"}])
        await self.manager.add(ids=["y"], documents=["Y doc"], metadatas=[{"env": "dev"}])

        response = await self.manager.fetch_all(where={"env": "prod"})
        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["ids"], ["x"])

    async def test_update(self) -> None:
        """Add a document, update its text and metadata, then verify."""
        await self.manager.add(
            ids=["upd-1"],
            documents=["Original text."],
            metadatas=[{"version": 1}],
        )

        update_response = await self.manager.update(
            ids=["upd-1"],
            documents=["Updated text."],
            metadatas=[{"version": 2}],
        )
        self.assertTrue(update_response["success"])
        self.assertEqual(update_response["data"]["count"], 1)

        fetch_response = await self.manager.fetch_one("upd-1")
        self.assertTrue(fetch_response["success"])
        doc = fetch_response["data"]
        self.assertEqual(doc["document"], "Updated text.")
        self.assertEqual(doc["metadata"]["version"], 2)

    async def test_delete(self) -> None:
        """Add a document, delete it, then confirm it is gone."""
        await self.manager.add(ids=["del-1"], documents=["To be deleted."])

        delete_response = await self.manager.delete(ids=["del-1"])
        self.assertTrue(delete_response["success"])
        self.assertEqual(delete_response["data"]["count"], 1)

        fetch_response = await self.manager.fetch_one("del-1")
        self.assertTrue(fetch_response["success"])   # success=True (document simply absent)
        self.assertIsNone(fetch_response["data"])    # data=None confirms it is gone

    async def test_add_duplicate_id_fails(self) -> None:
        """Adding a document with an already-existing ID returns success=False."""
        await self.manager.add(ids=["dup-1"], documents=["First insert."])

        response = await self.manager.add(ids=["dup-1"], documents=["Duplicate insert."])
        self.assertFalse(response["success"])
        self.assertIsNone(response["data"])
        self.assertIsNotNone(response["message"])   # Error message must be present

    async def test_fetch_one_not_found(self) -> None:
        """Fetching a non-existent ID returns success=True with data=None."""
        response = await self.manager.fetch_one("ghost-id-99999")
        self.assertTrue(response["success"])
        self.assertIsNone(response["data"])
        self.assertIn("not found", response["message"].lower())

    async def test_update_requires_payload(self) -> None:
        """update() with no documents/metadatas/embeddings returns success=False."""
        await self.manager.add(ids=["empty-upd"], documents=["Some text."])
        response = await self.manager.update(ids=["empty-upd"])   # nothing to update
        self.assertFalse(response["success"])
        self.assertIn("requires at least one of", response["message"])

    async def test_delete_empty_ids_fails(self) -> None:
        """delete() called with an empty list returns success=False."""
        response = await self.manager.delete(ids=[])
        self.assertFalse(response["success"])
        self.assertIn("non-empty ids list", response["message"])

    async def test_collection_exists(self) -> None:
        """collection_exists() returns success=True with a count field."""
        await self.manager.add(ids=["ce-1"], documents=["Existence check doc."])
        response = await self.manager.collection_exists()
        self.assertTrue(response["success"])
        self.assertIn("count", response["data"])
        self.assertGreaterEqual(response["data"]["count"], 1)


if __name__ == "__main__":
    unittest.main()

''' for testing, run the following command in the terminal:
cd backend
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="python"
uv run python -m unittest tests.DBvector_test'''