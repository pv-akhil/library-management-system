from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from library.models import Book, BookCopy, Category
from reservations.models import Reservation
from transactions.models import Transaction


class ReservationQueueTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.librarian = User.objects.create_user(
            username='lib_queue', password='Password123!', role=User.Role.LIBRARIAN
        )
        self.student1 = User.objects.create_user(
            username='stu_res1', password='Password123!', role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            username='stu_res2', password='Password123!', role=User.Role.STUDENT
        )

        self.category = Category.objects.create(name='Design')
        self.book = Book.objects.create(
            isbn='978-0201633610',
            title='Design Patterns',
            category=self.category
        )
        self.copy = BookCopy.objects.create(
            book=self.book,
            barcode='BC-DP-001',
            status=BookCopy.Status.ISSUED
        )

    def test_reservation_queue_ordering(self):
        """Sequential reservations increment the queue position correctly."""
        res1 = Reservation.objects.create(book=self.book, user=self.student1)
        res2 = Reservation.objects.create(book=self.book, user=self.student2)

        self.assertEqual(res1.queue_position, 1)
        self.assertEqual(res2.queue_position, 2)

    def test_cancel_reindexes_queue(self):
        """Cancelling position #1 must advance position #2 to #1."""
        res1 = Reservation.objects.create(book=self.book, user=self.student1)
        res2 = Reservation.objects.create(book=self.book, user=self.student2)

        # Student 1 cancels
        res1.cancel(reason="No longer needed")
        res1.refresh_from_db()
        self.assertEqual(res1.status, Reservation.Status.CANCELLED)

        # Student 2 should now be #1
        res2.refresh_from_db()
        self.assertEqual(res2.queue_position, 1)

    def test_book_return_allocates_to_pending_reservation(self):
        """When an issued book is returned, it automatically marks the top reservation as APPROVED."""
        trans = Transaction.objects.create(
            user=self.student1,
            book_copy=self.copy,
            due_date=timezone.now() + timezone.timedelta(days=7),
            status=Transaction.Status.ISSUED
        )

        # Student 2 is waiting in reservation queue
        res = Reservation.objects.create(book=self.book, user=self.student2)
        self.assertEqual(res.status, Reservation.Status.PENDING)

        # Librarian returns copy
        self.client.login(username='lib_queue', password='Password123!')
        response = self.client.post(reverse('transactions:return_book'), {
            'barcode': 'BC-DP-001',
            'condition': 'GOOD'
        })
        self.assertEqual(response.status_code, 302)

        # Copy should now be RESERVED for student 2
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, BookCopy.Status.RESERVED)

        # Reservation should be APPROVED with pickup expiry
        res.refresh_from_db()
        self.assertEqual(res.status, Reservation.Status.APPROVED)
        self.assertIsNotNone(res.expiry_date)
