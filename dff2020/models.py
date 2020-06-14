from django.db import models
from django.contrib.auth.models import User


class Order(models.Model):
    rzp_order_id = models.CharField(max_length=100, unique=True, blank=False)
    rzp_payment_id = models.CharField(max_length=100, null=True)
    receipt_number = models.CharField(max_length=32, blank=False)
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)


class Entry(models.Model):
    name = models.CharField(max_length=50)
    director = models.CharField(max_length=50)
    link = models.CharField(max_length=500)
    synopsis = models.CharField(max_length=500, blank=True, null=True,)
    runtime = models.IntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
