from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User
from library.models import Book, BookCopy, Category
from reservations.models import Reservation
from transactions.models import Transaction


class RestApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.librarian = User.objects.create_user(
            username='api_librarian',
            password='Password123!',
            email='lib@api.org',
            role=User.Role.LIBRARIAN
        )
        self.student = User.objects.create_user(
            username='api_student',
            password='Password123!',
            email='student@api.org',
            role=User.Role.STUDENT
        )

        self.category = Category.objects.create(name='Computer Architecture')
        self.book = Book.objects.create(
            isbn='978-0128119051',
            title='Computer Organization and Design',
            category=self.category
        )
        self.copy = BookCopy.objects.create(
            book=self.book,
            barcode='BC-ARCH-001',
            status=BookCopy.Status.AVAILABLE
        )

    def test_jwt_token_obtain(self):
        """Test JWT token pair creation."""
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_student',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_books_list_api(self):
        """Test retrieving book catalog via REST API."""
        response = self.client.get('/api/v1/books/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 1)

    def test_circulation_issue_and_return_api(self):
        """Test issue and return endpoints with JWT bearer token."""
        # 1. Login as librarian
        login_res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_librarian',
            'password': 'Password123!'
        })
        token = login_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 2. Issue book via API
        issue_res = self.client.post('/api/v1/circulation/issue/', {
            'user_id': self.student.id,
            'barcode': 'BC-ARCH-001',
            'due_days': 10
        })
        self.assertEqual(issue_res.status_code, status.HTTP_201_CREATED)
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, BookCopy.Status.ISSUED)

        # 3. Return book via API
        return_res = self.client.post('/api/v1/circulation/return/', {
            'barcode': 'BC-ARCH-001',
            'condition': 'GOOD'
        })
        self.assertEqual(return_res.status_code, status.HTTP_200_OK)
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, BookCopy.Status.AVAILABLE)

    def test_reserve_book_api(self):
        """Test student reserving book via API."""
        login_res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_student',
            'password': 'Password123!'
        })
        token = login_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        res = self.client.post('/api/v1/reservations/reserve/', {
            'book_id': self.book.id
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['queue_position'], 1)
