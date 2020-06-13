from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    name = models.CharField(max_length=50)
    director = models.CharField(max_length=50)
    link = models.CharField(max_length=500)
    runtime = models.IntegerField()
    added_at = models.DateTimeField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class Order(models.Model):
    pass
