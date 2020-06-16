from django.db import models
from django.contrib.auth.models import User


class Order(models.Model):
    rzp_order_id = models.CharField(max_length=100, unique=True, blank=False)
    rzp_payment_id = models.CharField(max_length=100, null=True)
    receipt_number = models.CharField(max_length=32, blank=False)
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.rzp_order_id


class Entry(models.Model):
    name = models.CharField(max_length=50)
    director = models.CharField(max_length=50)
    link = models.CharField(max_length=500)
    synopsis = models.CharField(max_length=500, blank=True, null=True,)
    runtime = models.IntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Entries"


class Faq(models.Model):
    question = models.CharField(max_length=200)
    answer = models.CharField(max_length=700)

    class Meta:
        verbose_name_plural = "FAQs"


class Rule(models.Model):
    text = models.CharField(max_length=800)
    type = models.CharField(max_length=40)
