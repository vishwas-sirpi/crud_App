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
        cls.token1 = ""
        cls.token2 = ""

    def test_00_register_and_login(self):
        # Register user 1
        resp = self.client.post("/auth/register", json={"email": "test@example.com", "password": "password123"})
        self.assertEqual(resp.status_code, 201)
        
        # Login user 1
        resp = self.client.post("/auth/login", data={"username": "test@example.com", "password": "password123"})
        self.assertEqual(resp.status_code, 200)
        TestCRUD.token1 = resp.json()["access_token"]
        
        # Register and login user 2
        self.client.post("/auth/register", json={"email": "user2@example.com", "password": "password123"})
        resp = self.client.post("/auth/login", data={"username": "user2@example.com", "password": "password123"})
        TestCRUD.token2 = resp.json()["access_token"]

    def test_01_create_item_success(self):
        # Unauthenticated request -> 401
        resp = self.client.post("/items", json={"name": "Book A", "price": 10.99})
        self.assertEqual(resp.status_code, 401)
        
        # Authenticated request
        headers = {"Authorization": f"Bearer {self.token1}"}
        response = self.client.post(
            "/items",
            json={"name": "Book A", "description": "First Book", "price": 10.99, "quantity": 5},
            headers=headers
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "Book A")
        self.assertEqual(data["price"], 10.99)
        self.assertIn("id", data)
        self.assertEqual(data["user_id"], 1)

    def test_02_create_item_validation_fail(self):
        headers = {"Authorization": f"Bearer {self.token1}"}
        response = self.client.post("/items", json={"name": "Book B", "price": -5.0}, headers=headers)
        self.assertEqual(response.status_code, 422)

    def test_03_read_items(self):
        headers = {"Authorization": f"Bearer {self.token1}"}
        response = self.client.post("/items", json={"name": "Book B", "price": 15.0, "quantity": 2}, headers=headers)
        self.assertEqual(response.status_code, 201)
        
        # Read list (public)
        response = self.client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["skip"], 0)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(len(data["items"]), 2)

    def test_04_read_item_by_id(self):
        response = self.client.get("/items/1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Book A")

    def test_05_update_item(self):
        headers1 = {"Authorization": f"Bearer {self.token1}"}
        headers2 = {"Authorization": f"Bearer {self.token2}"}
        
        # User 1 updates their own item -> success
        response = self.client.put("/items/1", json={"price": 12.50, "quantity": 10}, headers=headers1)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["price"], 12.50)

        # User 2 tries to update User 1's item -> 403
        response = self.client.put("/items/1", json={"price": 9.99}, headers=headers2)
        self.assertEqual(response.status_code, 403)

    def test_06_delete_item(self):
        headers1 = {"Authorization": f"Bearer {self.token1}"}
        headers2 = {"Authorization": f"Bearer {self.token2}"}
        
        # User 2 tries to delete User 1's item -> 403
        response = self.client.delete("/items/2", headers=headers2)
        self.assertEqual(response.status_code, 403)
        
        # User 1 deletes their own item -> 200
        response = self.client.delete("/items/2", headers=headers1)
        self.assertEqual(response.status_code, 200)
        
        # Verify Book B is deleted
        response = self.client.get("/items/2")
        self.assertEqual(response.status_code, 404)

    def test_07_get_user_items(self):
        headers = {"Authorization": f"Bearer {self.token1}"}
        response = self.client.get("/users/me/items", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Item 1 is still there
        self.assertEqual(len(data), 1)

    def test_08_create_items_for_querying(self):
        headers = {"Authorization": f"Bearer {self.token1}"}
        items = [
            {"name": "Dragon Story", "price": 20.0, "quantity": 4, "category": "fiction", "description": "A dragon adventure"},
            {"name": "Science Journal", "price": 35.0, "quantity": 1, "category": "non-fiction", "description": "Research papers"},
            {"name": "Fictional Tales", "price": 15.0, "quantity": 2, "category": "fiction", "description": "Short stories of fantasy"},
        ]
        for item in items:
            response = self.client.post("/items", json=item, headers=headers)
            self.assertEqual(response.status_code, 201)

    def test_09_filter_by_category(self):
        response = self.client.get("/items?category=fiction")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["skip"], 0)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(len(data["items"]), 2)
        for item in data["items"]:
            self.assertEqual(item["category"], "fiction")

    def test_10_search_items(self):
        response = self.client.get("/items?search=dragon")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["name"], "Dragon Story")

    def test_11_sort_items(self):
        response = self.client.get("/items?sort_by=price&order=asc")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        prices = [item["price"] for item in data["items"]]
        self.assertEqual(prices, sorted(prices))

        response = self.client.get("/items?sort_by=price&order=desc")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        prices = [item["price"] for item in data["items"]]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_12_combined_query_params(self):
        response = self.client.get("/items?category=fiction&search=dragon&sort_by=price&order=desc&skip=0&limit=10")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["name"], "Dragon Story")

    def test_13_invalid_sort_by(self):
        response = self.client.get("/items?sort_by=invalid_field")
        self.assertEqual(response.status_code, 422)
        self.assertIn("sort_by must be one of", response.json()["detail"])

    def test_14_limit_above_max(self):
        response = self.client.get("/items?limit=101")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "limit must not exceed 100")

if __name__ == "__main__":
    unittest.main()
