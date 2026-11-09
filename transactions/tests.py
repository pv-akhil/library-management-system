from decimal import Decimal
from django.conf import settings
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from library.models import Book, BookCopy, Category
from transactions.models import Fine, Transaction


class CirculationAndFineTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.librarian = User.objects.create_user(
            username='lib_staff', password='Password123!', role=User.Role.LIBRARIAN
        )
        self.student = User.objects.create_user(
            username='stu_borrower', password='Password123!', role=User.Role.STUDENT
        )

        self.category = Category.objects.create(name='Technology')
        self.book = Book.objects.create(
            isbn='978-0131103627',
            title='The C Programming Language',
            category=self.category
        )
        self.copy1 = BookCopy.objects.create(
            book=self.book,
            barcode='BC-C-001',
            status=BookCopy.Status.AVAILABLE
        )
        self.copy2 = BookCopy.objects.create(
            book=self.book,
            barcode='BC-C-002',
            status=BookCopy.Status.AVAILABLE
        )

    def test_issue_book_success(self):
        """Staff issues available book copy to student."""
        self.client.login(username='lib_staff', password='Password123!')
        response = self.client.post(reverse('transactions:issue_book'), {
            'member': self.student.id,
            'barcode': 'BC-C-001',
            'due_days': 14,
            'remarks': 'Test issue'
        })
        self.assertEqual(response.status_code, 302)

        # Check transaction created
        trans = Transaction.objects.filter(book_copy=self.copy1, user=self.student).first()
        self.assertIsNotNone(trans)
        self.assertEqual(trans.status, Transaction.Status.ISSUED)

        # Check copy status updated
        self.copy1.refresh_from_db()
        self.assertEqual(self.copy1.status, BookCopy.Status.ISSUED)

    def test_return_book_on_time_no_fine(self):
        """Return book within due date incurs zero fines."""
        trans = Transaction.objects.create(
            user=self.student,
            book_copy=self.copy1,
            due_date=timezone.now() + timezone.timedelta(days=7),
            status=Transaction.Status.ISSUED
        )
        self.copy1.status = BookCopy.Status.ISSUED
        self.copy1.save()

        self.client.login(username='lib_staff', password='Password123!')
        response = self.client.post(reverse('transactions:return_book'), {
            'barcode': 'BC-C-001',
            'condition': 'GOOD',
            'remarks': 'Returned in fine shape'
        })
        self.assertEqual(response.status_code, 302)

        trans.refresh_from_db()
        self.assertEqual(trans.status, Transaction.Status.RETURNED)
        self.assertIsNotNone(trans.return_date)

        self.copy1.refresh_from_db()
        self.assertEqual(self.copy1.status, BookCopy.Status.AVAILABLE)

        # Ensure no fine was created
        self.assertFalse(Fine.objects.filter(transaction=trans).exists())

    def test_return_overdue_book_generates_fine(self):
        """Returning an overdue book automatically generates a fine."""
        past_due = timezone.now() - timezone.timedelta(days=5)
        trans = Transaction.objects.create(
            user=self.student,
            book_copy=self.copy1,
            issue_date=timezone.now() - timezone.timedelta(days=20),
            due_date=past_due,
            status=Transaction.Status.OVERDUE
        )
        self.copy1.status = BookCopy.Status.ISSUED
        self.copy1.save()

        self.client.login(username='lib_staff', password='Password123!')
        response = self.client.post(reverse('transactions:return_book'), {
            'barcode': 'BC-C-001',
            'condition': 'GOOD'
        })
        self.assertEqual(response.status_code, 302)

        fine = Fine.objects.filter(transaction=trans).first()
        self.assertIsNotNone(fine)
        self.assertFalse(fine.is_paid)
        # 5 days overdue * $1.00 fine per day = $5.00
        self.assertEqual(fine.amount, Decimal('5.00'))

    def test_record_fine_payment(self):
        """Staff marks fine as paid."""
        trans = Transaction.objects.create(
            user=self.student,
            book_copy=self.copy1,
            due_date=timezone.now() - timezone.timedelta(days=2),
            status=Transaction.Status.OVERDUE
        )
        fine = Fine.objects.create(transaction=trans, amount=Decimal('2.00'))

        self.client.login(username='lib_staff', password='Password123!')
        response = self.client.post(reverse('transactions:pay_fine', args=[fine.id]), {
            'payment_method': Fine.PaymentMethod.CASH,
            'notes': 'Receipt #9872'
        })
        self.assertEqual(response.status_code, 302)

        fine.refresh_from_db()
        self.assertTrue(fine.is_paid)
        self.assertEqual(fine.payment_method, Fine.PaymentMethod.CASH)
        self.assertIsNotNone(fine.paid_at)
