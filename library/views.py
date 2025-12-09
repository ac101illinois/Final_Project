from django.shortcuts import render, redirect, get_object_or_404
from .models import Book, BookList, BookListItem, ReadingProgress, Reward
from datetime import datetime
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.utils.text import slugify
import requests
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

#Home/Dashboard
@login_required(login_url='library:login')
def home_view(request):
    #current read:
    current_progress = ReadingProgress.objects.filter(status='reading').first()
    current_book = current_progress.book if current_progress else None

    #points on dashboard
    total_pages = ReadingProgress.objects.aggregate(total=Sum('pages_read'))['total'] or 0
    points = int(total_pages / 10)

    #showing next reward
    next_reward = None
    points_needed = 0
    for reward in Reward.objects.order_by('required_points'):
        if reward.required_points > points:
            next_reward = reward
            points_needed = reward.required_points - points
            break

    #update progress:
    if request.method == 'POST' and 'update_progress' in request.POST and current_book:
        pages = request.POST.get('pages_read')
        status = request.POST.get('status')

        progress_result = ReadingProgress.objects.get_or_create(book=current_book)
        progress = progress_result[0]
        created = progress_result[1]

        if pages:
            progress.pages_read = int(pages)
        if status in ['not_started', 'reading', 'finished']:
            progress.status = status
            if status == 'reading' and not progress.date_started:
                progress.date_started = datetime.now().date()
            if status == 'finished':
                progress.date_finished = datetime.now().date()
        progress.save()
        return redirect('home')

    if request.method == 'POST' and 'add_book' in request.POST:
        # Use a single default list (create if it doesn't exist)
        library_list, _ = BookList.objects.get_or_create(
            user=request.user,
            list_name="My Books"
        )

        title = request.POST.get('title')
        author = request.POST.get('author')
        total_pages = request.POST.get('total_pages')
        cover = request.POST.get('cover')
        description = request.POST.get('description', "")

        book, _ = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={
                "total_pages": total_pages,
                "cover": cover,
                "description": description
            }
        )

        BookListItem.objects.get_or_create(book=book, book_list=library_list)
        return redirect('home')

    #search open library:
    query = request.GET.get('q', '')
    search_results = []
    if query:
        url = 'https://openlibrary.org/search.json'
        params = {'q': query, 'limit': 10}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for doc in data.get('docs', []):
                edition_key = doc.get('edition_key', [''])[0]
                search_results.append({
                    'title': doc.get('title'),
                    'author': ', '.join(doc.get('author_name', [])),
                    'total_pages': doc.get('number_of_pages_median'),
                    'cover_url': f"https://covers.openlibrary.org/b/olid/{edition_key}-L.jpg" if edition_key else '',
                    'edition_key': edition_key,
                })

    return render(request, 'home.html', {
        'current_book': current_book,
        'points': points,
        'next_reward': next_reward,
        'points_needed': points_needed,
        'search_results': search_results,
        'query': query,
    })

@login_required(login_url='library:login')
def mybooks_view(request):
    query = request.GET.get('q', '')

    if query:
        books = Book.objects.filter(title__icontains=query)
    else:
        books = Book.objects.all()

    lists = BookList.objects.all()

    context = {
        'books': books,
        'lists': lists,
        'query': query
    }

    return render(request, 'mybooks.html', context)

@login_required(login_url='library:login')
def list_view(request, slug):

    book_list = get_object_or_404(BookList, slug=slug)
    books = book_list.books.all()

    context = {
        'books': books,
        'book_list': book_list
    }

    return render(request, 'booklist.html', context)

@login_required(login_url='library:login')
def addlist_view(request, slug):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            slug = slugify(name)
            BookList.objects.create(name=name, slug=slug)
            return redirect('mybooks')

    return render(request, 'addlist.html')

@login_required(login_url='library:login')
def editlist_view(request, slug):
    book_list = get_object_or_404(BookList, slug=slug)

    if request.method == 'POST':
        new_name = request.POST.get('name')
        if new_name:
            book_list.name = new_name
            book_list.slug = slugify(new_name)
            book_list.save()
            return redirect('mybooks')

    return render(request, 'editlist.html')

@login_required(login_url='library:login')
def deletelist_view(request, slug):
    book_list = get_object_or_404(BookList, slug=slug)

    if request.method == 'POST':
        book_list.delete()
        return redirect('mybooks')

    return render(request, 'deletelist.html')

@login_required(login_url='library:login')
def addbook_view(request, slug):
    if request.method == 'POST':
        book_list = get_object_or_404(BookList, slug=slug)

        title = request.POST.get('title')
        author = request.POST.get('author')
        pages = request.POST.get('pages')
        edition_key = request.POST.get('edition_key')
        cover_url = request.POST.get('cover_url')

        book, create = Book.objects.get_or_create(
            title=title,
            author=author,
            pages=pages,
            edition_key=edition_key,
            cover_url=cover_url,

        )


