from django.db import models

# Create your models here.
class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    total_pages = models.IntegerField()
    pages_read = models.IntegerField(default=0)
    list_name = models.CharField(max_length=100, default="My Books")
    def __str__(self):
        return self.title

class ReadingStats(models.Model):
    pages_read = models.IntegerField(default=0)
    books_read = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
