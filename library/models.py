from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
        title = models.CharField(max_length=100)
        author = models.CharField(max_length=100)
        total_pages = models.PositiveIntegerField(null=True, blank=True)
        description = models.TextField(blank=True)
        cover = models.URLField(blank=True)
        edition_key = models.CharField(max_length=50, blank=True, null=True)

        def __str__(self):
            return self.title

class BookList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    list_name = models.CharField(max_length=255)
    books = models.ManyToManyField(Book, through='BookListItem')
    slug = models.SlugField(default="", null=False)
    def __str__(self):
        return self.list_name

class BookListItem(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    book_list = models.ForeignKey(BookList, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.book.title} in {self.book_list.list_name}"

class ReadingProgress(models.Model):

    STATUS_CHOICES = [
        ('to_read', 'To Read'),
        ('reading', 'Currently Reading'),
        ('finished', 'Finished'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reading_progress')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='progress_records')

    pages_read = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='to_read')

    date_started = models.DateField(blank=True, null=True)
    date_finished = models.DateField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                name='unique_user_book_progress'
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"
