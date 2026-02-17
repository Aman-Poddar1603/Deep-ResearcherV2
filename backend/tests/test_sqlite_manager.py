import unittest
import os
import sqlite3
from backend.main.src.store.sqlite_manager import SQLiteManager

class TestSQLiteManager(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_db.sqlite"
        self.manager = SQLiteManager(self.db_path)
        # Setup initial table
        self.manager.create_table("users", {
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT",
            "age": "INTEGER"
        })

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_insert_and_fetch_one(self):
        insert_response = self.manager.insert("users", {"name": "Alice", "age": 30})
        self.assertTrue(insert_response['success'])
        user_id = insert_response['data']['id']
        self.assertIsNotNone(user_id)
        
        # New API usage: fetch_one(table_name, where={...})
        response = self.manager.fetch_one("users", where={"id": user_id})
        self.assertTrue(response['success'])
        user = response['data']
        self.assertEqual(user['name'], "Alice")
        self.assertEqual(user['age'], 30)

    def test_fetch_all(self):
        self.manager.insert("users", {"name": "Bob", "age": 25})
        self.manager.insert("users", {"name": "Charlie", "age": 35})
        
        # New API usage: fetch_all(table_name)
        response = self.manager.fetch_all("users")
        self.assertTrue(response['success'])
        users = response['data']
        self.assertEqual(len(users), 2)

    def test_update(self):
        insert_response = self.manager.insert("users", {"name": "David", "age": 40})
        user_id = insert_response['data']['id']

        # New API usage: update(table_name, data, where={...})
        update_response = self.manager.update("users", {"age": 41}, where={"id": user_id})
        self.assertTrue(update_response['success'])
        
        response = self.manager.fetch_one("users", where={"id": user_id})
        user = response['data']
        self.assertEqual(user['age'], 41)

    def test_delete(self):
        insert_response = self.manager.insert("users", {"name": "Eve", "age": 20})
        user_id = insert_response['data']['id']

        # New API usage: delete(table_name, where={...})
        delete_response = self.manager.delete("users", where={"id": user_id})
        self.assertTrue(delete_response['success'])
        
        response = self.manager.fetch_one("users", where={"id": user_id})
        self.assertTrue(response['success'])
        self.assertIsNone(response['data'])

    def test_create_table_error(self):
        """Test error handling when creating a table with invalid schema."""
        # Passing a string instead of dict should fail per our new check (or logic)
        # Or if we want to test SQL syntax error, we pass a valid dict with invalid types
        
        # Case 1: Invalid input type
        response = self.manager.create_table("invalid_table", "not a dict")
        self.assertFalse(response['success'])
        self.assertIn("must be a dictionary", response['message'])

        # Case 2: Invalid SQL syntax generated from dict
        response = self.manager.create_table("bad_syntax", {"col": "INVALID TYPE HERE"})
        # SQLite accepts almost any string as type affinity, so it's hard to force a syntax error 
        # purely via type string unless it contains standard SQL keywords in wrong places.
        # But `create_table` logic just joins them. 
        # A truly invalid schema might be empty dict?
        
        response = self.manager.create_table("empty_schema", {})
        # This generates "CREATE TABLE IF NOT EXISTS empty_schema ()" which is invalid syntax
        self.assertFalse(response['success'])
        self.assertIn("syntax error", response['message'].lower())

    def test_insert_error(self):
        """Test error handling when inserting into a non-existent table."""
        response = self.manager.insert("non_existent_table", {"col": "val"})
        self.assertFalse(response['success'])
        self.assertIsNotNone(response['message'])
        self.assertIsNone(response['data'])

    def test_fetch_error(self):
        """Test error handling when fetching from a non-existent table."""
        response = self.manager.fetch_all("non_existent_table")
        self.assertFalse(response['success'])
        self.assertIsNotNone(response['message'])
        self.assertIsNone(response['data'])


if __name__ == '__main__':
    unittest.main()
