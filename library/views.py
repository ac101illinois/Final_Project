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
from django.http import HttpResponse

@login_required(login_url='library:login')
def home_view(request):

    user = request.user

    # ---------------------------------------------------------
    # 1. ADD BOOK TO USER'S LIST
    # ---------------------------------------------------------
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

        # Create book
        book, _ = Book.objects.get_or_create(
            title=title,
            author=author,
            defaults={
                "total_pages": pages,
                "cover": cover,
                "edition_key": edition_key,
            }
        )

        # Add to list
        BookListItem.objects.get_or_create(book=book, book_list=library_list)

        # Create reading progress default ("to_read")
        ReadingProgress.objects.get_or_create(
            user=user,
            book=book,
            defaults={"status": "to_read"}
        )

        return redirect("library:home-view")

    # ---------------------------------------------------------
    # 2. SEARCH FUNCTION — retrieves editions
    # ---------------------------------------------------------
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

                # Fetch editions
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

    # ---------------------------------------------------------
    # 3. LOAD USER DASHBOARD (TBR + Current Reads)
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # RENDER PAGE
    # ---------------------------------------------------------
    return render(request, "home.html", {
        "query": query,
        "search_results": search_results,
        "to_read_books": to_read_books,
        "current_reads": current_reads,
        "username": user.username,
    })

@login_required(login_url='library:login')
def mybooks_view(request):

    # -------------------------
    # REMOVE BOOK FROM LIST
    # -------------------------
    if request.method == "POST" and "remove_book" in request.POST:
        book_id = request.POST.get("book_id")
        if book_id:
            book_list = BookList.objects.get(user=request.user, list_name="My Books")
            BookListItem.objects.filter(book_list=book_list, book_id=book_id).delete()

            # Remove progress (optional)
            ReadingProgress.objects.filter(user=request.user, book_id=book_id).delete()

        return redirect("library:mybooks-view")


    # -------------------------
    # UPDATE STATUS
    # -------------------------
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


    # -------------------------
    # UPDATE READING PROGRESS
    # -------------------------
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

            # Auto-start date
            if progress.status == "reading" and not progress.date_started:
                progress.date_started = datetime.now().date()

            # Auto-complete
            book = Book.objects.get(id=book_id)
            if book.total_pages and progress.pages_read >= book.total_pages:
                progress.status = "finished"
                progress.date_finished = datetime.now().date()

        progress.save()
        return redirect("library:mybooks-view")


    # -------------------------
    # DISPLAY USER BOOKS
    # -------------------------
    search_query = request.GET.get("q", "").strip()
    filter_status = request.GET.get("status", "")

    # Get list
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

    # Search filter
    if search_query:
        books = [b for b in books if search_query.lower() in b["object"].title.lower()]

    # Status filter
    if filter_status:
        books = [b for b in books if b["status"] == filter_status]

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

    # --------------------------------------------
    # Get all progress objects for this user
    # --------------------------------------------
    progress = ReadingProgress.objects.filter(user=user).select_related("book")

    # --------------------------------------------
    # BASIC COUNTS
    # --------------------------------------------
    total_books = progress.count()
    currently_reading = progress.filter(status="reading").count()
    finished_books = progress.filter(status="finished").count()
    to_read_count = progress.filter(status="to_read").count()

    # This year filter
    year = datetime.now().year
    books_read_this_year = progress.filter(
        status="finished",
        date_finished__year=year
    ).count()

    # Pages read this year
    pages_read_this_year = progress.filter(
        status="finished",
        date_finished__year=year
    ).aggregate(total=Sum("pages_read"))["total"] or 0

    # --------------------------------------------
    # GRAPH DATA: Books Finished Per Month
    # --------------------------------------------
    monthly_finished = (
        progress.filter(status="finished", date_finished__year=year)
        .values("date_finished__month")
        .annotate(count=Count("id"))
        .order_by("date_finished__month")
    )

    # Convert to 12-month array for chart.js
    books_per_month = [0] * 12
    for entry in monthly_finished:
        month_index = entry["date_finished__month"] - 1
        books_per_month[month_index] = entry["count"]

    # --------------------------------------------
    # GRAPH DATA: Pages Per Month
    # --------------------------------------------
    monthly_pages = (
        progress.filter(status="finished", date_finished__year=year)
        .values("date_finished__month")
        .annotate(total_pages=Sum("pages_read"))
        .order_by("date_finished__month")
    )

    pages_per_month = [0] * 12
    for entry in monthly_pages:
        month_index = entry["date_finished__month"] - 1
        pages_per_month[month_index] = entry["total_pages"]

    # --------------------------------------------
    return render(request, "stats.html", {
        "year": year,
        "total_books": total_books,
        "currently_reading": currently_reading,
        "finished_books": finished_books,
        "to_read_count": to_read_count,
        "books_read_this_year": books_read_this_year,
        "pages_read_this_year": pages_read_this_year,
        "books_per_month": books_per_month,
        "pages_per_month": pages_per_month,
    })

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
