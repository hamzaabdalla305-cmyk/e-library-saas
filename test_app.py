import unittest
from app import app, db


class LibraryTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def test_homepage_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)

    def test_api_register(self):
        response = self.client.post('/api/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123456'
        })
        self.assertEqual(response.status_code, 201)

    def test_api_books_empty(self):
        response = self.client.get('/api/books')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])


if __name__ == '__main__':
    unittest.main()
