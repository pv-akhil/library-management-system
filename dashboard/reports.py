import csv
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from library.models import Book, BookCopy
from transactions.models import Transaction, Fine


def export_books_csv():
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="library_books_catalog_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'ISBN', 'Title', 'Category', 'Authors', 'Publisher', 'Publication Year', 'Total Copies', 'Available Copies'])

    books = Book.objects.select_related('category', 'publisher').prefetch_related('authors', 'copies').all()
    for b in books:
        writer.writerow([
            b.id,
            b.isbn,
            b.title,
            b.category.name if b.category else 'Uncategorized',
            b.author_names,
            b.publisher.name if b.publisher else 'N/A',
            b.publication_year or 'N/A',
            b.total_copies_count,
            b.available_copies_count,
        ])

    return response


def export_transactions_csv():
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="circulation_report_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Member ID', 'Member Name', 'Book Title', 'Barcode', 'Issue Date', 'Due Date', 'Return Date', 'Status', 'Overdue Days'])

    transactions = Transaction.objects.select_related('user', 'book_copy__book').order_by('-issue_date')
    for t in transactions:
        writer.writerow([
            t.id,
            t.user.member_id or t.user.username,
            t.user.get_full_name() or t.user.username,
            t.book_copy.book.title,
            t.book_copy.barcode,
            t.issue_date.strftime('%Y-%m-%d %H:%M'),
            t.due_date.strftime('%Y-%m-%d'),
            t.return_date.strftime('%Y-%m-%d %H:%M') if t.return_date else 'Not Returned',
            t.get_status_display(),
            t.overdue_days,
        ])

    return response


def export_overdue_pdf():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=12
    )
    story.append(Paragraph("<b>Apex Library System - Overdue Loans Report</b>", title_style))
    story.append(Paragraph(f"Generated on: {timezone.now().strftime('%B %d, %Y at %H:%M UTC')}", styles['Normal']))
    story.append(Spacer(1, 16))

    overdue_loans = Transaction.objects.select_related('user', 'book_copy__book').filter(
        status__in=[Transaction.Status.OVERDUE, Transaction.Status.ISSUED],
        due_date__lt=timezone.now()
    ).order_by('due_date')

    data = [['Member ID', 'Member Name', 'Book Title', 'Barcode', 'Due Date', 'Days Overdue', 'Est. Fine']]

    for loan in overdue_loans:
        est_fine = loan.calculate_fine_amount()
        data.append([
            loan.user.member_id or loan.user.username,
            loan.user.get_full_name() or loan.user.username,
            loan.book_copy.book.title[:25] + ('...' if len(loan.book_copy.book.title) > 25 else ''),
            loan.book_copy.barcode,
            loan.due_date.strftime('%Y-%m-%d'),
            str(loan.overdue_days),
            f"${est_fine:.2f}"
        ])

    if len(data) == 1:
        data.append(['None', 'No overdue loans currently recorded.', '', '', '', '', ''])

    table = Table(data, colWidths=[70, 100, 150, 70, 70, 50, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))

    story.append(table)
    doc.build(story)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="overdue_loans_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
    return response
