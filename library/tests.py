from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from library.models import Author, Book, BookCopy, Category, Publisher


class LibraryCatalogTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.librarian = User.objects.create_user(
            username='lib1', password='Password123!', role=User.Role.LIBRARIAN
        )
        self.student = User.objects.create_user(
            username='stu1', password='Password123!', role=User.Role.STUDENT
        )

        self.category = Category.objects.create(name='Science Fiction', description='Sci-fi books')
        self.author = Author.objects.create(name='Isaac Asimov')
        self.publisher = Publisher.objects.create(name='Gnome Press')

        self.book = Book.objects.create(
            isbn='978-0553293357',
            title='Foundation',
            category=self.category,
            publisher=self.publisher,
            publication_year=1951,
            pages=255,
            summary='The Galactic Empire is falling.'
        )
        self.book.authors.add(self.author)

        self.copy1 = BookCopy.objects.create(
            book=self.book,
            rack_location='Rack SF-01',
            status=BookCopy.Status.AVAILABLE,
            price=Decimal('15.99')
        )
        self.copy2 = BookCopy.objects.create(
            book=self.book,
            rack_location='Rack SF-01',
            status=BookCopy.Status.ISSUED,
            price=Decimal('15.99')
        )

    def test_book_copies_count_properties(self):
        """Verify copy count calculations."""
        self.assertEqual(self.book.total_copies_count, 2)
        self.assertEqual(self.book.available_copies_count, 1)
        self.assertTrue(self.book.is_available)

    def test_barcode_auto_generation(self):
        """Verify copy barcode auto-generation."""
        copy3 = BookCopy.objects.create(book=self.book)
        self.assertTrue(copy3.barcode.startswith('BC-'))

    def test_catalog_search(self):
        """Verify catalog search endpoint returns the matched book."""
        response = self.client.get(reverse('library:catalog'), {'q': 'Foundation'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Foundation')

    def test_librarian_can_add_book(self):
        """Librarian has permissions to create new books."""
        self.client.login(username='lib1', password='Password123!')
        response = self.client.post(reverse('library:book_create'), {
            'title': 'I, Robot',
            'isbn': '978-0553382563',
            'category': self.category.id,
            'authors': [self.author.id],
            'publisher': self.publisher.id,
            'publication_year': 1950,
            'language': 'English',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Book.objects.filter(title='I, Robot').exists())

    def test_student_cannot_add_book(self):
        """Student role must be denied access to book creation."""
        self.client.login(username='stu1', password='Password123!')
        response = self.client.post(reverse('library:book_create'), {
            'title': 'Unauthorized Book',
            'isbn': '978-0000000000',
        })
        self.assertEqual(response.status_code, 302)  # Redirected away with error message
        self.assertFalse(Book.objects.filter(title='Unauthorized Book').exists())
