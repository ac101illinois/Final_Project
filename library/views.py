from django.shortcuts import render, redirect, get_object_or_404
from .models import Book, BookList, BookListItem, ReadingProgress
from datetime import datetime
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.utils.text import slugify
import requests
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from .forms_auth import SignUpForm
from django.contrib.auth import login

@login_required(login_url='library:login')
def home_view(request):
    import requests

    # -----------------------------------
    # 1. ADD BOOK TO USER'S BOOK LIST
    # -----------------------------------
    if request.method == 'POST' and 'add_book' in request.POST:
        library_list, _ = BookList.objects.get_or_create(
            user=request.user,
            list_name="My Books"
        )

        title = request.POST.get('title')
        author = request.POST.get('author')
        pages = request.POST.get('pages')
        cover = request.POST.get('cover')
        edition_key = request.POST.get('edition_key')
        description = request.POST.get('description', '')

        # Create or get the book
        book, _ = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={
                "total_pages": pages,
                "cover": cover,
                "description": description,
                "edition_key": edition_key,
            }
        )

        # Add to user's book list
        BookListItem.objects.get_or_create(book=book, book_list=library_list)

        return redirect('library:home-view')

    # -----------------------------------
    # 2. SEARCH: RETURN EDITIONS ONLY
    # -----------------------------------
    query = request.GET.get('q') or ""
    edition_results = []

    if query.strip() != "":
        search_url = "https://openlibrary.org/search.json"
        resp = requests.get(search_url, params={"q": query, "limit": 10})

        if resp.status_code == 200:
            data = resp.json()

            for doc in data.get("docs", []):
                work_id = doc.get("key")  # "/works/OLxxxxxxW"
                work_olid = work_id.replace("/works/", "")

                # Fetch editions
                editions_url = f"https://openlibrary.org/works/{work_olid}/editions.json?limit=50"
                ed_resp = requests.get(editions_url)
                if ed_resp.status_code != 200:
                    continue

                ed_data = ed_resp.json()

                # Build edition cards
                for ed in ed_data.get("entries", []):
                    cover_id = ed.get("covers", [None])[0]

                    edition_results.append({
                        "title": ed.get("title") or doc.get("title") or "Unknown Title",
                        "author": ", ".join(doc.get("author_name", [])),
                        "format": ed.get("physical_format") or "Edition",
                        "country": ed.get("publish_country", "") or "Unknown",
                        "publish_date": ed.get("publish_date", ""),
                        "pages": ed.get("number_of_pages"),
                        "cover": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else "",
                        "edition_key": ed.get("key").replace("/books/", "")
                    })

    return render(request, "home.html", {
        "query": query,
        "editions": edition_results,
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
def mybooks_view(request):
    # Get the user's default "My Books" list
    library_list, _ = BookList.objects.get_or_create(
        user=request.user,
        list_name="My Books"
    )

    if request.method == "POST" and "remove_book" in request.POST:
        book_id = request.POST.get("book_id")
        if book_id:
            BookListItem.objects.filter(
                book_list=library_list,
                book_id=book_id
            ).delete()
        return redirect("library:mybooks-view")

    # Base queryset: all books user owns
    books = library_list.books.all()

    # Apply search filter
    query = request.GET.get('q', "")
    if query:
        books = books.filter(title__icontains=query)

    return render(request, "mybooks.html", {
        "books": books,
        "query": query,
    })

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


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            login(request, new_user)
            return redirect("library:home-view")
    else:
        form = SignUpForm()

    return render(request, "signup.html", {"form": form})


