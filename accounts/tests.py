from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


class UserModelAndAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admintest',
            email='admin@test.com',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.librarian_user = User.objects.create_user(
            username='libtest',
            email='lib@test.com',
            password='Password123!',
            role=User.Role.LIBRARIAN
        )
        self.student_user = User.objects.create_user(
            username='studenttest',
            email='student@test.com',
            password='Password123!',
            role=User.Role.STUDENT
        )

    def test_member_id_auto_generation(self):
        """Verify automatic member_id generation with appropriate prefix."""
        self.assertTrue(self.admin_user.member_id.startswith('ADM-'))
        self.assertTrue(self.librarian_user.member_id.startswith('LIB-'))
        self.assertTrue(self.student_user.member_id.startswith('STU-'))

    def test_role_properties(self):
        """Verify role helper properties."""
        self.assertTrue(self.admin_user.is_admin_role)
        self.assertTrue(self.admin_user.is_staff_member)
        self.assertTrue(self.librarian_user.is_librarian_role)
        self.assertTrue(self.librarian_user.is_staff_member)
        self.assertTrue(self.student_user.is_student_role)
        self.assertFalse(self.student_user.is_staff_member)

    def test_student_registration_view(self):
        """Test student self-registration endpoint."""
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'email': 'newstudent@university.edu',
            'first_name': 'New',
            'last_name': 'Student',
            'password1': 'NewPass1234!',
            'password2': 'NewPass1234!',
        })
        self.assertEqual(response.status_code, 302)  # Redirects to login
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.member_id.startswith('STU-'))

    def test_login_flow(self):
        """Test user login with valid credentials."""
        response = self.client.post(reverse('login'), {
            'username': 'studenttest',
            'password': 'Password123!',
            'remember_me': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:index'))
