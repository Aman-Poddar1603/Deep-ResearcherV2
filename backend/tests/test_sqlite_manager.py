import unittest
import os
import sqlite3
from backend.main.src.store.sqlite_manager import SQLiteManager

class TestSQLiteManager(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_db.sqlite"
        self.manager = SQLiteManager(self.db_path)
        # Setup initial table
        self.manager.create_table("users", "id INTEGER PRIMARY KEY, name TEXT, age INTEGER")

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_insert_and_fetch_one(self):
        user_id = self.manager.insert("users", {"name": "Alice", "age": 30})
        self.assertIsNotNone(user_id)
        
        user = self.manager.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        self.assertEqual(user['name'], "Alice")
        self.assertEqual(user['age'], 30)

    def test_fetch_all(self):
        self.manager.insert("users", {"name": "Bob", "age": 25})
        self.manager.insert("users", {"name": "Charlie", "age": 35})
        
        users = self.manager.fetch_all("SELECT * FROM users")
        self.assertEqual(len(users), 2)

    def test_update(self):
        user_id = self.manager.insert("users", {"name": "David", "age": 40})
        self.manager.update("users", {"age": 41}, "id = ?", (user_id,))
        
        user = self.manager.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        self.assertEqual(user['age'], 41)

    def test_delete(self):
        user_id = self.manager.insert("users", {"name": "Eve", "age": 20})
        self.manager.delete("users", "id = ?", (user_id,))
        
        user = self.manager.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()
