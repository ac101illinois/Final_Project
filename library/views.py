from django.shortcuts import render, redirect, get_object_or_404
from .models import Book, BookList, ReadingStats, Reward

# Create your views here.
#Views: home, stats, search for book, add, delete, update progress,

#Pages: Home, My Books, Stats, reading timer, session?, rewards page?

#Home/Dashboard
def home_view(request):
    books = Book.objects.filter(owner=request.user)

    current_read = books.filter(is_currently_reading=True).first()

    total_points = sum(b.pages_read for b in books)
    goal = 1000
    points_remaining = goal - total_points
    progress_percentage = ((total_points / goal) * 100)

    context = {
        'current_read': current_read,
        'total_points': total_points,
        'goal': goal,
        'progress_percentage': progress_percentage,
        'points_remaining': points_remaining,
        'books': books
    }

    return render(request, 'home.html', context)

#My Books
def mybooks_view(request):

    query = request.GET.get("q", "")

    books = Book.objects.filter(owner=request.user)
    if query:
        books = books.filter(title__icontains=query)

    book_lists = BookList.objects.filter(owner=request.user)

    context = {
        'book_lists': book_lists,
        'books': books,
        'query': query,
    }

    return render(request, 'mybooks.html', context)

def booklist_view(request):
    book_list = get_object_or_404(BookList, owner=request.user)

    books = book_list.books.all()

    context = {
        'book_lists': book_list,
        'books': books,
    }

    return render(request, 'booklist.html', context)

def addlist_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        new_list = BookList(title=name, owner=request.user)
        return redirect('mybooks')

    return render(request, 'addlist.html')

def editlist_view(request):
    book_list = get_object_or_404(BookList, owner=request.user)

    if request.method == "POST":
        book_list.name == request.POST.get("name")
        book_list.save()
        return redirect('mybooks')

    context = {
        'book_list': book_list,
    }

    return render(request, 'editlist.html', context)


def deletelist_view(request):
    book_list = get_object_or_404(BookList, owner=request.user)

    if request.method == "POST":
        book_list.delete()
        return redirect('mybooks')

    context = {
        'book_list': book_list,
    }

    return render(request, 'deletelist.html', context)







