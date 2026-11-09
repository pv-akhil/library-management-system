import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom User model with Role-Based Access Control (Admin, Librarian, Student).
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        LIBRARIAN = 'LIBRARIAN', 'Librarian'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Role determining access privileges."
    )
    member_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text="Institutional Member ID (e.g., STU-2026-1042)."
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        full = self.get_full_name()
        display = full if full else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_librarian_role(self) -> bool:
        return self.role == self.Role.LIBRARIAN

    @property
    def is_student_role(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_staff_member(self) -> bool:
        return self.is_admin_role or self.is_librarian_role

    def save(self, *args, **kwargs):
        # Auto-generate member ID if not set
        if not self.member_id:
            year = timezone.now().year
            prefix = {
                self.Role.ADMIN: 'ADM',
                self.Role.LIBRARIAN: 'LIB',
                self.Role.STUDENT: 'STU',
            }.get(self.role, 'MEM')
            rand_num = random.randint(1000, 9999)
            self.member_id = f"{prefix}-{year}-{rand_num}"

        # Sync superuser status
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        elif self.role == self.Role.LIBRARIAN:
            self.is_staff = True
        super().save(*args, **kwargs)
