from django.db import models

# Create your models here.

class BookList(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    total_pages = models.IntegerField()
    pages_read = models.IntegerField(default=0)
    list_name = models.ForeignKey(BookList, on_delete=models.SET_NULL, null=True)
    is_currently_reading = models.BooleanField(default=False)
    def __str__(self):
        return self.title

class ReadingStats(models.Model):
    pages_read = models.IntegerField(default=0)
    books_read = models.IntegerField(default=0)
    points = models.IntegerField(default=0)

class Reward(models.Model):
    reward = models.CharField(max_length=100)
    required_points = models.IntegerField()

    def __str__(self):
        return self.reward



