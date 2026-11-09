from django import forms
from .models import Author, Book, BookCopy, Category, Publisher


class BookForm(forms.ModelForm):
    authors = forms.ModelMultipleChoiceField(
        queryset=Author.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'})
    )

    class Meta:
        model = Book
        fields = (
            'title', 'isbn', 'category', 'authors', 'publisher',
            'publication_year', 'edition', 'pages', 'language',
            'summary', 'cover_image'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Clean Architecture'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 978-0134494166'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'publisher': forms.Select(attrs={'class': 'form-select'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2024'}),
            'edition': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1st Edition'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '350'}),
            'language': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'English'}),
            'summary': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Book synopsis...'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class BookCopyForm(forms.ModelForm):
    class Meta:
        model = BookCopy
        fields = ('barcode', 'rack_location', 'status', 'condition', 'price', 'acquired_date', 'notes')
        widgets = {
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to auto-generate'}),
            'rack_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Shelf A-4'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'acquired_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ('name', 'biography')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'biography': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class PublisherForm(forms.ModelForm):
    class Meta:
        model = Publisher
        fields = ('name', 'address', 'website')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
