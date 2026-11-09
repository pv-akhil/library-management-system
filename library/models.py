import random
import string
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=200, unique=True)
    biography = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    isbn = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Standard 10 or 13-digit ISBN number"
    )
    title = models.CharField(max_length=255, db_index=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books'
    )
    authors = models.ManyToManyField(Author, related_name='books', blank=True)
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books'
    )
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    edition = models.CharField(max_length=50, blank=True, default='')
    pages = models.PositiveIntegerField(null=True, blank=True)
    language = models.CharField(max_length=50, default='English')
    summary = models.TextField(blank=True, default='')
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'title']

    def __str__(self):
        return f"{self.title} (ISBN: {self.isbn})"

    @property
    def author_names(self) -> str:
        authors = list(self.authors.values_list('name', flat=True))
        return ", ".join(authors) if authors else "Unknown Author"

    @property
    def total_copies_count(self) -> int:
        return self.copies.count()

    @property
    def available_copies_count(self) -> int:
        return self.copies.filter(status=BookCopy.Status.AVAILABLE).count()

    @property
    def is_available(self) -> bool:
        return self.available_copies_count > 0


class BookCopy(models.Model):
    """
    Physical individual copy of a book in inventory with barcode and rack shelf tracking.
    """
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        ISSUED = 'ISSUED', 'Issued / On Loan'
        RESERVED = 'RESERVED', 'Reserved'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance / Repair'
        LOST = 'LOST', 'Lost / Written Off'

    class Condition(models.TextChoices):
        NEW = 'NEW', 'Brand New'
        EXCELLENT = 'EXCELLENT', 'Excellent'
        GOOD = 'GOOD', 'Good'
        FAIR = 'FAIR', 'Fair'
        DAMAGED = 'DAMAGED', 'Damaged'

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    barcode = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique accession barcode tag (e.g., BC-987452)."
    )
    rack_location = models.CharField(
        max_length=100,
        blank=True,
        default='Main Stacks',
        help_text="Physical location in library (e.g., Section A, Shelf 3, Bay 2)"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        db_index=True
    )
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.EXCELLENT
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    acquired_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['barcode']
        verbose_name_plural = 'Book Copies'

    def __str__(self):
        return f"{self.book.title} [Barcode: {self.barcode}] - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.barcode:
            # Auto generate barcode accession number
            chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.barcode = f"BC-{chars}"
        super().save(*args, **kwargs)
