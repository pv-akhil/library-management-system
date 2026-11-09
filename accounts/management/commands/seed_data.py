from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from library.models import Author, Book, BookCopy, Category, Publisher
from transactions.models import Fine, Transaction
from reservations.models import Reservation


class Command(BaseCommand):
    help = 'Seeds initial test data (roles, catalog, transactions, and reservations)'

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # 1. Users
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@apexlibrary.org',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('AdminPass123!')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created Admin: admin / AdminPass123!"))

        librarian, created = User.objects.get_or_create(
            username='librarian',
            defaults={
                'email': 'librarian@apexlibrary.org',
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'role': User.Role.LIBRARIAN,
                'is_staff': True,
            }
        )
        if created:
            librarian.set_password('LibPass123!')
            librarian.save()
            self.stdout.write(self.style.SUCCESS("Created Librarian: librarian / LibPass123!"))

        student1, created = User.objects.get_or_create(
            username='student',
            defaults={
                'email': 'student@university.edu',
                'first_name': 'Alex',
                'last_name': 'Taylor',
                'role': User.Role.STUDENT,
            }
        )
        if created:
            student1.set_password('StudentPass123!')
            student1.save()
            self.stdout.write(self.style.SUCCESS("Created Student: student / StudentPass123!"))

        student2, created = User.objects.get_or_create(
            username='emily',
            defaults={
                'email': 'emily.chen@university.edu',
                'first_name': 'Emily',
                'last_name': 'Chen',
                'role': User.Role.STUDENT,
            }
        )
        if created:
            student2.set_password('StudentPass123!')
            student2.save()

        # 2. Categories
        cat_cs, _ = Category.objects.get_or_create(
            name='Computer Science',
            defaults={'description': 'Algorithms, software engineering, databases, and architectures.'}
        )
        cat_lit, _ = Category.objects.get_or_create(
            name='Literature & Fiction',
            defaults={'description': 'Classic, modern, and historical literary works.'}
        )
        cat_ds, _ = Category.objects.get_or_create(
            name='Data Science & AI',
            defaults={'description': 'Machine learning, neural networks, and statistical inference.'}
        )
        cat_math, _ = Category.objects.get_or_create(
            name='Mathematics',
            defaults={'description': 'Discrete mathematics, calculus, and linear algebra.'}
        )

        # 3. Authors
        auth_martin, _ = Author.objects.get_or_create(name='Robert C. Martin', defaults={'biography': 'Uncle Bob - Software craftsman and author.'})
        auth_fowler, _ = Author.objects.get_or_create(name='Martin Fowler', defaults={'biography': 'Chief Scientist at ThoughtWorks.'})
        auth_shelley, _ = Author.objects.get_or_create(name='Mary Shelley', defaults={'biography': 'English novelist, author of Frankenstein.'})
        auth_knuth, _ = Author.objects.get_or_create(name='Donald E. Knuth', defaults={'biography': 'Pioneering computer scientist and professor emeritus at Stanford.'})

        # 4. Publishers
        pub_oreilly, _ = Publisher.objects.get_or_create(name="O'Reilly Media", defaults={'website': 'https://oreilly.com'})
        pub_pearson, _ = Publisher.objects.get_or_create(name="Pearson Education", defaults={'website': 'https://pearson.com'})
        pub_penguin, _ = Publisher.objects.get_or_create(name="Penguin Classics", defaults={'website': 'https://penguinclassics.com'})

        # 5. Books
        book1, created = Book.objects.get_or_create(
            isbn='978-0132350884',
            defaults={
                'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
                'category': cat_cs,
                'publisher': pub_pearson,
                'publication_year': 2008,
                'edition': '1st Edition',
                'pages': 464,
                'language': 'English',
                'summary': 'Even bad code can function. But if code isn’t clean, it can bring a development organization to its knees.',
            }
        )
        book1.authors.set([auth_martin])

        book2, created = Book.objects.get_or_create(
            isbn='978-0201485677',
            defaults={
                'title': 'Refactoring: Improving the Design of Existing Code',
                'category': cat_cs,
                'publisher': pub_pearson,
                'publication_year': 2018,
                'edition': '2nd Edition',
                'pages': 448,
                'language': 'English',
                'summary': 'A guide to refactoring patterns that improve the structural integrity of code without altering its external behavior.',
            }
        )
        book2.authors.set([auth_fowler])

        book3, created = Book.objects.get_or_create(
            isbn='978-0141439471',
            defaults={
                'title': 'Frankenstein; or, The Modern Prometheus',
                'category': cat_lit,
                'publisher': pub_penguin,
                'publication_year': 1818,
                'edition': 'Penguin Classics Edition',
                'pages': 280,
                'language': 'English',
                'summary': 'The iconic gothic novel about Victor Frankenstein and the creature brought to life in an unorthodox scientific experiment.',
            }
        )
        book3.authors.set([auth_shelley])

        book4, created = Book.objects.get_or_create(
            isbn='978-0201896831',
            defaults={
                'title': 'The Art of Computer Programming, Vol. 1',
                'category': cat_math,
                'publisher': pub_pearson,
                'publication_year': 1997,
                'edition': '3rd Edition',
                'pages': 672,
                'language': 'English',
                'summary': 'The seminal computer science reference monograph by Donald Knuth on fundamental algorithms.',
            }
        )
        book4.authors.set([auth_knuth])

        # 6. Book Copies
        copy1_1, _ = BookCopy.objects.get_or_create(
            barcode='BC-CLN-001',
            defaults={
                'book': book1,
                'rack_location': 'Rack CS-01, Shelf 2',
                'status': BookCopy.Status.ISSUED,
                'condition': BookCopy.Condition.EXCELLENT,
                'price': Decimal('38.50'),
            }
        )

        copy1_2, _ = BookCopy.objects.get_or_create(
            barcode='BC-CLN-002',
            defaults={
                'book': book1,
                'rack_location': 'Rack CS-01, Shelf 2',
                'status': BookCopy.Status.AVAILABLE,
                'condition': BookCopy.Condition.GOOD,
                'price': Decimal('38.50'),
            }
        )

        copy2_1, _ = BookCopy.objects.get_or_create(
            barcode='BC-REF-001',
            defaults={
                'book': book2,
                'rack_location': 'Rack CS-02, Shelf 1',
                'status': BookCopy.Status.AVAILABLE,
                'condition': BookCopy.Condition.NEW,
                'price': Decimal('49.99'),
            }
        )

        copy3_1, _ = BookCopy.objects.get_or_create(
            barcode='BC-FRK-001',
            defaults={
                'book': book3,
                'rack_location': 'Rack LIT-04, Shelf 3',
                'status': BookCopy.Status.ISSUED,
                'condition': BookCopy.Condition.GOOD,
                'price': Decimal('12.95'),
            }
        )

        copy4_1, _ = BookCopy.objects.get_or_create(
            barcode='BC-KNT-001',
            defaults={
                'book': book4,
                'rack_location': 'Rack REF-01, Shelf 4',
                'status': BookCopy.Status.AVAILABLE,
                'condition': BookCopy.Condition.EXCELLENT,
                'price': Decimal('75.00'),
            }
        )

        # 7. Transactions (Active, Overdue, and Returned)
        now = timezone.now()

        # Active Loan (Student Alex)
        trans1, _ = Transaction.objects.get_or_create(
            book_copy=copy1_1,
            user=student1,
            status=Transaction.Status.ISSUED,
            defaults={
                'issued_by': librarian,
                'issue_date': now - timezone.timedelta(days=5),
                'due_date': now + timezone.timedelta(days=9),
                'remarks': 'Issued for coursework study',
            }
        )

        # Overdue Loan (Student Emily)
        trans2, _ = Transaction.objects.get_or_create(
            book_copy=copy3_1,
            user=student2,
            defaults={
                'issued_by': librarian,
                'issue_date': now - timezone.timedelta(days=20),
                'due_date': now - timezone.timedelta(days=6),  # 6 days overdue
                'status': Transaction.Status.OVERDUE,
                'remarks': 'Literature thesis preparation',
            }
        )
        if trans2.status == Transaction.Status.OVERDUE:
            Fine.objects.get_or_create(
                transaction=trans2,
                defaults={
                    'amount': Decimal('6.00'),
                    'is_paid': False,
                    'notes': 'Overdue by 6 days',
                }
            )

        # 8. Reservations
        Reservation.objects.get_or_create(
            book=book2,
            user=student1,
            defaults={
                'queue_position': 1,
                'status': Reservation.Status.PENDING,
                'notes': 'Priority study booking',
            }
        )

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with sample books, users, circulation and fines!"))
