from django.contrib import admin
from .models import Author, Book, BookCopy, Category, Publisher


class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 1
    fields = ('barcode', 'rack_location', 'status', 'condition', 'price')


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'isbn', 'category', 'author_names', 'publication_year', 'total_copies_count', 'available_copies_count')
    list_filter = ('category', 'publisher', 'language')
    search_fields = ('title', 'isbn', 'authors__name')
    inlines = [BookCopyInline]


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'book', 'rack_location', 'status', 'condition', 'price')
    list_filter = ('status', 'condition')
    search_fields = ('barcode', 'book__title', 'rack_location')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)
