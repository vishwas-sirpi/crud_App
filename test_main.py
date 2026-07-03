import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

class TestCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reset database tables to ensure clean, isolated tests
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)

    def test_01_create_item_success(self):
        response = self.client.post(
            "/items",
            json={"name": "Book A", "description": "First Book", "price": 10.99, "quantity": 5}
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "Book A")
        self.assertEqual(data["description"], "First Book")
        self.assertEqual(data["price"], 10.99)
        self.assertEqual(data["quantity"], 5)
        self.assertIn("id", data)
        self.assertEqual(data["id"], 1)

    def test_02_create_item_validation_fail(self):
        # Price must be positive (> 0)
        response = self.client.post(
            "/items",
            json={"name": "Book B", "price": -5.0}
        )
        self.assertEqual(response.status_code, 422)

        # Name must not be empty (min_length=1)
        response = self.client.post(
            "/items",
            json={"name": "", "price": 10.0}
        )
        self.assertEqual(response.status_code, 422)

        # Name missing completely
        response = self.client.post(
            "/items",
            json={"price": 10.0}
        )
        self.assertEqual(response.status_code, 422)

    def test_03_read_items(self):
        # Create second item
        response = self.client.post(
            "/items",
            json={"name": "Book B", "price": 15.0, "quantity": 2}
        )
        self.assertEqual(response.status_code, 201)
        
        # Read list
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        
        # Test pagination: skip=1, limit=1 should only return Book B
        response = self.client.get("/items?skip=1&limit=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Book B")

    def test_04_read_item_by_id(self):
        # Retrieve existing item
        response = self.client.get("/items/1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Book A")

        # Retrieve non-existent item
        response = self.client.get("/items/999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Item with ID 999 not found")

    def test_05_update_item(self):
        # Update existing item (Book A)
        response = self.client.put(
            "/items/1",
            json={"price": 12.50, "quantity": 10}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["price"], 12.50)
        self.assertEqual(data["quantity"], 10)
        self.assertEqual(data["name"], "Book A")  # remains original name

        # Validation during update (price must be positive)
        response = self.client.put(
            "/items/1",
            json={"price": -1.0}
        )
        self.assertEqual(response.status_code, 422)

        # Update non-existent item
        response = self.client.put(
            "/items/999",
            json={"name": "New Name"}
        )
        self.assertEqual(response.status_code, 404)

    def test_06_delete_item(self):
        # Delete Book B (id 2)
        response = self.client.delete("/items/2")
        self.assertEqual(response.status_code, 200)
        
        # Verify Book B is deleted
        response = self.client.get("/items/2")
        self.assertEqual(response.status_code, 404)

        # Delete non-existent item
        response = self.client.delete("/items/999")
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
