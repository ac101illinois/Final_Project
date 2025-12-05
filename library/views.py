from django.shortcuts import render, redirect, get_object_or_404
from .models import Book, BookList, BookListItem, ReadingProgress, Reward
from datetime import datetime
from django.db.models import Sum, Count
from django.utils.timezone import now
import requests
from django.db.models import Sum

#Home/Dashboard
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


