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
import csv
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
import matplotlib.pyplot as plt
from io import BytesIO

@login_required(login_url='library:login')
def home_view(request):

    user = request.user

# Add a book to the user's "mybooks" list
    if request.method == "POST" and "add_book" in request.POST:
        library_list, _ = BookList.objects.get_or_create(
            user=user,
            list_name="My Books"
        )

        title = request.POST.get("title")
        author = request.POST.get("author")
        pages = request.POST.get("pages")
        cover = request.POST.get("cover")
        edition_key = request.POST.get("edition_key")

        # Create or get the book they searched
        book, _ = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={
                "total_pages": pages,
                "cover": cover,
                "edition_key": edition_key,
            }
        )

        # Add the book to their list
        BookListItem.objects.get_or_create(book=book, book_list=library_list)

        # When the book is added, its status is automatically set to "to_read"
        ReadingProgress.objects.get_or_create(
            user=user,
            book=book,
            defaults={"status": "to_read"}
        )

        return redirect("library:home-view")

# Searching the Open library api for books
    query = request.GET.get("q", "").strip()
    search_results = []

    if query:
        url = "https://openlibrary.org/search.json"
        resp = requests.get(url, params={"q": query, "limit": 10})

        if resp.status_code == 200:
            data = resp.json()
            docs = data.get("docs", [])

            for doc in docs:
                work_key = doc.get("key")
                if not work_key:
                    continue

                work_id = work_key.replace("/works/", "")

                # get each edition of the book they are searching
                editions_url = f"https://openlibrary.org/works/{work_id}/editions.json?limit=50"
                ed_resp = requests.get(editions_url)
                if ed_resp.status_code != 200:
                    continue

                ed_data = ed_resp.json()
                edition_entries = ed_data.get("entries", [])

                editions_list = []
                for e in edition_entries:
                    cover_id = e.get("covers", [None])[0]

                    editions_list.append({
                        "cover": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
                        "format": e.get("physical_format"),
                        "pages": e.get("number_of_pages"),
                        "publish_date": e.get("publish_date"),
                        "edition_key": e.get("key").replace("/books/", "")
                    })

                search_results.append({
                    "title": doc.get("title"),
                    "author": ", ".join(doc.get("author_name", [])),
                    "editions": editions_list[:6]
                })

# Dashboard displaying the books in the user's "my books" page
    book_list, _ = BookList.objects.get_or_create(
        user=user,
        list_name="My Books"
    )

    items = BookListItem.objects.filter(book_list=book_list).select_related("book")

    to_read_books = []
    current_reads = []

    for item in items:
        book = item.book
        progress = ReadingProgress.objects.filter(user=user, book=book).first()

        # Ensure reading status always exists
        if not progress:
            progress = ReadingProgress.objects.create(
                user=user,
                book=book,
                status="to_read",
                pages_read=0
            )

        data = {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover": book.cover,
            "status": progress.status,
            "pages_read": progress.pages_read,
            "total_pages": book.total_pages,
        }

        if progress.status == "reading":
            current_reads.append(data)
        elif progress.status == "to_read":
            to_read_books.append(data)


    return render(request, "home.html", {
        "query": query,
        "search_results": search_results,
        "to_read_books": to_read_books,
        "current_reads": current_reads,
        "username": user.username,
    })

@login_required(login_url='library:login')
def mybooks_view(request):

# remove book from "mybooks"
    if request.method == "POST" and "remove_book" in request.POST:
        book_id = request.POST.get("book_id")
        if book_id:
            book_list = BookList.objects.get(user=request.user, list_name="My Books")
            BookListItem.objects.filter(book_list=book_list, book_id=book_id).delete()

            # Remove progress (optional)
            ReadingProgress.objects.filter(user=request.user, book_id=book_id).delete()

        return redirect("library:mybooks-view")

#user can update the status of their books (to_read, finished, currently reading)
    if request.method == "POST" and "update_status" in request.POST:
        book_id = request.POST.get("book_id")
        new_status = request.POST.get("new_status")

        if book_id and new_status:
            book = Book.objects.get(id=book_id)
            progress, _ = ReadingProgress.objects.get_or_create(
                user=request.user,
                book=book
            )

            progress.status = new_status

            # Dates
            if new_status == "reading" and not progress.date_started:
                progress.date_started = now().date()
            if new_status == "finished":
                progress.date_finished = now().date()

            progress.save()

        return redirect("library:mybooks-view")

# user can update their reading progress if a book's status is "currently reading"
    if request.method == "POST" and "update_progress" in request.POST:
        book_id = request.POST.get("book_id")
        pages_read = request.POST.get("pages_read")

        progress, created = ReadingProgress.objects.get_or_create(
            user=request.user,
            book_id=book_id,
            defaults={"status": "reading"}
        )

        if pages_read:
            progress.pages_read = int(pages_read)

            # if a start date is not already specified, the day they add progress is the start date
            if progress.status == "reading" and not progress.date_started:
                progress.date_started = datetime.now().date()

            # if the user adds progress and the page count is equal or more than the pages of the book,
            #it is automatically set as "finished"
            book = Book.objects.get(id=book_id)
            if book.total_pages and progress.pages_read >= book.total_pages:
                progress.status = "finished"
                progress.date_finished = datetime.now().date()

        progress.save()
        return redirect("library:mybooks-view")

# displaying the user's books in mybooks page
#the user can search through the books they own
    search_query = request.GET.get("q", "").strip()
    filter_status = request.GET.get("status", "")

# display the entire list of books they own
    book_list, _ = BookList.objects.get_or_create(
        user=request.user,
        list_name="My Books"
    )

    items = BookListItem.objects.filter(book_list=book_list).select_related("book")

    books = []
    for item in items:
        book = item.book
        progress = ReadingProgress.objects.filter(user=request.user, book=book).first()

        books.append({
            "object": book,
            "status": progress.status if progress else "to_read",
            "pages_read": progress.pages_read if progress else 0,
        })

    return render(request, "mybooks.html", {
        "books": books,
        "search_query": search_query,
        "filter_status": filter_status,
    })


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

@login_required(login_url='library:login')
def bookdetail_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # Get reading progress if exists
    progress = ReadingProgress.objects.filter(user=request.user, book=book).first()

    # Create a display-friendly progress percent
    progress_pct = 0
    if progress and progress.status == "reading" and book.total_pages:
        progress_pct = int((progress.pages_read / book.total_pages) * 100)

    return render(request, "bookdetail.html", {
        "book": book,
        "progress": progress,
        "progress_pct": progress_pct,
    })

@login_required(login_url='library:login')
def stats_view(request):
    user = request.user
    progress = ReadingProgress.objects.filter(user=user).select_related("book")

    # --- Top counters ---
    total_books = progress.count()
    currently_reading = progress.filter(status="reading").count()
    finished_books = progress.filter(status="finished").count()
    to_read_count = progress.filter(status="to_read").count()

# count of books read this year
    year = datetime.now().year
    books_read_this_year = progress.filter(
        status="finished",
        date_finished__year=year
    ).count()

    return render(request, "stats.html", {
        "year": year,
        "total_books": total_books,
        "currently_reading": currently_reading,
        "finished_books": finished_books,
        "to_read_count": to_read_count,
        "books_read_this_year": books_read_this_year,
    })

@login_required(login_url='library:login')
def books_read_chart(request):
    user = request.user
    year = datetime.now().year

    # Books finished this year
    finished_books = ReadingProgress.objects.filter(
        user=user,
        status="finished",
        date_finished__year=year
    )

    # Count each finished book by month
    monthly_counts = [0] * 12
    for progress in finished_books:
        if progress.date_finished:
            month_index = progress.date_finished.month - 1
            monthly_counts[month_index] += 1

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    fig, ax = plt.subplots(figsize=(6, 2.5), dpi=150)
    ax.bar(months, monthly_counts, color="#fac0b9")
    ax.set_title(f"Books Read in {year}", fontsize=10)
    ax.set_ylabel("Books", fontsize=9)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required(login_url='library:login')
def books_status_pie_chart(request):

    user = request.user
    progress = ReadingProgress.objects.filter(user=user)

    status_counts = {
        "To Read": progress.filter(status="to_read").count(),
        "Reading": progress.filter(status="reading").count(),
        "Finished": progress.filter(status="finished").count(),
    }

    labels = [
        f"To Read ({status_counts['To Read']})",
        f"Reading ({status_counts['Reading']})",
        f"Finished ({status_counts['Finished']})",
    ]

    sizes = [
        status_counts["To Read"],
        status_counts["Reading"],
        status_counts["Finished"],
    ]

    colors = ["#fac0b9", "#af6a63", "#c84747"]

    fig = plt.figure(figsize=(4, 4), dpi=100)
    plt.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%")

    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type="image/png")

@login_required(login_url='library:login')
def export_mybooks_csv(request):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"mybooks_{timestamp}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)

    # CSV Header
    writer.writerow([
        "Title",
        "Author",
        "Status",
        "Pages Read",
        "Total Pages",
        "Date Started",
        "Date Finished",
    ])

    # Get user's book list
    book_list, _ = BookList.objects.get_or_create(
        user=request.user,
        list_name="My Books"
    )

    items = BookListItem.objects.filter(book_list=book_list).select_related("book")

    for item in items:
        book = item.book

        # progress may or may not exist
        progress = ReadingProgress.objects.filter(
            user=request.user,
            book=book
        ).first()

        writer.writerow([
            book.title,
            book.author,
            progress.status if progress else "to_read",
            progress.pages_read if progress else 0,
            book.total_pages or "",
            progress.date_started or "",
            progress.date_finished or "",
        ])

    return response


@login_required(login_url='library:login')
def export_mybooks_json(request):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"mybooks_{timestamp}.json"

    # Get user's book list
    book_list, _ = BookList.objects.get_or_create(
        user=request.user,
        list_name="My Books"
    )

    items = BookListItem.objects.filter(book_list=book_list).select_related("book")

    books_data = []

    for item in items:
        book = item.book

        progress = ReadingProgress.objects.filter(
            user=request.user,
            book=book
        ).first()

        books_data.append({
            "title": book.title,
            "author": book.author,
            "status": progress.status if progress else "to_read",
            "pages_read": progress.pages_read if progress else 0,
            "total_pages": book.total_pages,
            "date_started": progress.date_started.isoformat() if progress and progress.date_started else None,
            "date_finished": progress.date_finished.isoformat() if progress and progress.date_finished else None,
        })

    data = {
        "downloaded_at": timezone.now().isoformat(),
        "record_count": len(books_data),
        "books": books_data,
    }

    response = JsonResponse(data, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

def default_view(request):
    return render(request, "defaultpage.html")
