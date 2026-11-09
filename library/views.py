from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import (
    IsLibrarianOrAdminUser,
    librarian_or_admin_required,
)
from .forms import (
    AuthorForm,
    BookCopyForm,
    BookForm,
    CategoryForm,
    PublisherForm,
)
from .models import Author, Book, BookCopy, Category, Publisher
from .serializers import (
    AuthorSerializer,
    BookCopySerializer,
    BookDetailSerializer,
    BookListSerializer,
    CategorySerializer,
    PublisherSerializer,
)


# -------------------------------------------------------------
# Web Views (Catalog, HTMX Search, CRUD)
# -------------------------------------------------------------

def book_catalog_view(request):
    """
    Public & Member Catalog search with title, author, ISBN, category, and availability filters.
    Supports HTMX live searching.
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    available_only = request.GET.get('available') == 'true'

    books = Book.objects.select_related('category', 'publisher').prefetch_related('authors', 'copies').all()

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(isbn__icontains=query) |
            Q(authors__name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(summary__icontains=query)
        ).distinct()

    if category_id:
        books = books.filter(category_id=category_id)

    if available_only:
        books = books.filter(copies__status=BookCopy.Status.AVAILABLE).distinct()

    paginator = Paginator(books, 12)  # 12 per page for responsive grid
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.annotate(books_count=Count('books')).order_by('name')

    context = {
        'page_obj': page_obj,
        'query': query,
        'category_id': category_id,
        'available_only': available_only,
        'categories': categories,
        'total_count': paginator.count,
    }

    # HTMX partial swap for catalog results
    if request.headers.get('HX-Request'):
        return render(request, 'library/partials/catalog_grid.html', context)

    return render(request, 'library/catalog.html', context)


def book_detail_view(request, book_id):
    book = get_object_or_404(
        Book.objects.select_related('category', 'publisher').prefetch_related('authors', 'copies'),
        id=book_id
    )
    user_has_active_reservation = False
    if request.user.is_authenticated:
        user_has_active_reservation = request.user.reservations.filter(
            book=book,
            status__in=['PENDING', 'APPROVED']
        ).exists()

    context = {
        'book': book,
        'copies': book.copies.all(),
        'user_has_active_reservation': user_has_active_reservation,
    }
    return render(request, 'library/book_detail.html', context)


@librarian_or_admin_required
def book_create_view(request):
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            messages.success(request, f"Book '{book.title}' created successfully! You can now add inventory copies.")
            return redirect('library:book_detail', book_id=book.id)
    else:
        form = BookForm()

    return render(request, 'library/book_form.html', {
        'form': form,
        'title': 'Add New Book to Catalog',
        'btn_text': 'Save Book'
    })


@librarian_or_admin_required
def book_edit_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f"Book '{book.title}' updated successfully.")
            return redirect('library:book_detail', book_id=book.id)
    else:
        form = BookForm(instance=book)

    return render(request, 'library/book_form.html', {
        'form': form,
        'book': book,
        'title': f'Edit Book: {book.title}',
        'btn_text': 'Update Book'
    })


@librarian_or_admin_required
def book_delete_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f"Book '{title}' was permanently deleted from the catalog.")
        return redirect('library:catalog')

    return render(request, 'library/book_confirm_delete.html', {'book': book})


# -------------------------------------------------------------
# Book Copy / Inventory Management Views
# -------------------------------------------------------------

@librarian_or_admin_required
def copy_add_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    if request.method == 'POST':
        form = BookCopyForm(request.POST)
        if form.is_valid():
            copy = form.save(commit=False)
            copy.book = book
            copy.save()
            messages.success(request, f"Inventory copy with barcode '{copy.barcode}' added successfully.")
            return redirect('library:book_detail', book_id=book.id)
    else:
        form = BookCopyForm()

    return render(request, 'library/copy_form.html', {
        'form': form,
        'book': book,
        'title': f'Add Inventory Copy: {book.title}'
    })


@librarian_or_admin_required
def copy_edit_view(request, copy_id):
    copy = get_object_or_404(BookCopy.objects.select_related('book'), id=copy_id)
    if request.method == 'POST':
        form = BookCopyForm(request.POST, instance=copy)
        if form.is_valid():
            form.save()
            messages.success(request, f"Inventory copy '{copy.barcode}' updated.")
            return redirect('library:book_detail', book_id=copy.book.id)
    else:
        form = BookCopyForm(instance=copy)

    return render(request, 'library/copy_form.html', {
        'form': form,
        'book': copy.book,
        'copy': copy,
        'title': f'Edit Inventory Copy: {copy.barcode}'
    })


@librarian_or_admin_required
def copy_delete_view(request, copy_id):
    copy = get_object_or_404(BookCopy.objects.select_related('book'), id=copy_id)
    book_id = copy.book.id
    if request.method == 'POST':
        barcode = copy.barcode
        copy.delete()
        messages.success(request, f"Copy '{barcode}' removed from inventory.")
        return redirect('library:book_detail', book_id=book_id)

    return render(request, 'library/copy_confirm_delete.html', {'copy': copy})


# -------------------------------------------------------------
# Categories, Authors & Publishers Management
# -------------------------------------------------------------

@librarian_or_admin_required
def category_list_view(request):
    categories = Category.objects.annotate(books_count=Count('books')).order_by('name')
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New category created.")
            return redirect('library:category_list')
    else:
        form = CategoryForm()

    return render(request, 'library/category_list.html', {
        'categories': categories,
        'form': form
    })


# -------------------------------------------------------------
# REST API ViewSets (DRF)
# -------------------------------------------------------------

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ['name', 'description']


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ['name']


class PublisherViewSet(viewsets.ModelViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ['name']


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('category', 'publisher').prefetch_related('authors', 'copies').all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'publisher', 'language', 'publication_year']
    search_fields = ['title', 'isbn', 'authors__name', 'category__name', 'summary']
    ordering_fields = ['created_at', 'title', 'publication_year']

    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return BookDetailSerializer
        return BookListSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsLibrarianOrAdminUser()]
        return [permissions.AllowAny()]


class BookCopyViewSet(viewsets.ModelViewSet):
    queryset = BookCopy.objects.select_related('book').all()
    serializer_class = BookCopySerializer
    filterset_fields = ['book', 'status', 'condition', 'rack_location']
    search_fields = ['barcode', 'rack_location', 'book__title', 'book__isbn']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsLibrarianOrAdminUser()]
        return [permissions.IsAuthenticated()]
