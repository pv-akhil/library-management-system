from rest_framework import serializers
from .models import Author, Book, BookCopy, Category, Publisher


class CategorySerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(source='books.count', read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'description', 'books_count')


class AuthorSerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(source='books.count', read_only=True)

    class Meta:
        model = Author
        fields = ('id', 'name', 'biography', 'books_count')


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ('id', 'name', 'address', 'website')


class BookCopySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = BookCopy
        fields = (
            'id', 'book', 'book_title', 'barcode', 'rack_location',
            'status', 'status_display', 'condition', 'condition_display',
            'price', 'acquired_date', 'notes'
        )
        read_only_fields = ('id',)


class BookListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    publisher_name = serializers.CharField(source='publisher.name', read_only=True)
    author_names = serializers.ReadOnlyField()
    total_copies = serializers.ReadOnlyField(source='total_copies_count')
    available_copies = serializers.ReadOnlyField(source='available_copies_count')

    class Meta:
        model = Book
        fields = (
            'id', 'isbn', 'title', 'category', 'category_name',
            'publisher', 'publisher_name', 'author_names',
            'publication_year', 'edition', 'pages', 'language',
            'cover_image', 'total_copies', 'available_copies'
        )


class BookDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)
    authors = AuthorSerializer(many=True, read_only=True)
    author_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Author.objects.all(), write_only=True, source='authors'
    )
    copies = BookCopySerializer(many=True, read_only=True)
    total_copies = serializers.ReadOnlyField(source='total_copies_count')
    available_copies = serializers.ReadOnlyField(source='available_copies_count')

    class Meta:
        model = Book
        fields = (
            'id', 'isbn', 'title', 'category', 'authors', 'author_ids',
            'publisher', 'publication_year', 'edition', 'pages', 'language',
            'summary', 'cover_image', 'total_copies', 'available_copies',
            'copies', 'created_at', 'updated_at'
        )
