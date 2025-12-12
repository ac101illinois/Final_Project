from django.contrib import admin
from datetime import date
# Register your models here.

from .models import Book, BookList, BookListItem, ReadingProgress

admin.site.register(Book)
admin.site.register(BookList)
admin.site.register(BookListItem)
admin.site.register(ReadingProgress)
