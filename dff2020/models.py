from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


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

    def __str__(self):
        return f"{self.name} ({self.director})"

    class Meta:
        verbose_name_plural = "Entries"


class Faq(models.Model):
    question = models.CharField(max_length=200)
    answer = models.CharField(max_length=700)

    def __str__(self):
        return f"{self.question}"

    class Meta:
        verbose_name_plural = "FAQs"


class Rule(models.Model):
    text = models.CharField(max_length=800)
    type = models.CharField(max_length=40)

    def __str__(self):
        return f"{self.text}"


class Shortlist(models.Model):
    entry = models.OneToOneField(Entry, on_delete=models.CASCADE)
    review = models.CharField(max_length=2000)
    jury_rating = models.FloatField(
        validators=[MaxValueValidator(10), MinValueValidator(0)]
    )
    publish_on = models.DateField()
    is_jury_rating_locked = models.BooleanField(default=False)

    def __str__(self):
        return f"{str(self.entry)}: {self.jury_rating}"


class UserRating(models.Model):
    shortlist = models.ForeignKey(Shortlist, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.FloatField(validators=[MaxValueValidator(10), MinValueValidator(0)])
    review = models.CharField(max_length=2000)
    added_on = models.DateTimeField(auto_now=True)
    lat = models.CharField(max_length=100, null=True, blank=True)
    long = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.shortlist.entry}: {self.rating} ({self.user.username})"

    class Meta:
        unique_together = [["shortlist", "user"]]


class Question(models.Model):
    shortlist = models.ForeignKey(Shortlist, on_delete=models.CASCADE)
    text = models.CharField(max_length=500)

    def __str__(self):
        return f"{str(self.shortlist.entry)}: {self.text}"


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.question.text}: {self.text}"


class UserQuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now=True)
    shortlist = models.ForeignKey(Shortlist, on_delete=models.CASCADE)

    class Meta:
        unique_together = [["shortlist", "user"]]

    def __str__(self):
        return f"{self.user.username}: {self.shortlist.id}"


class QuizResponse(models.Model):
    quiz_attempt = models.ForeignKey(UserQuizAttempt, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submit_at = models.DateTimeField(auto_now=True)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return (
            f"{self.quiz_attempt.id}: {self.question.id} => {self.selected_option.id}"
        )

    class Meta:
        verbose_name_plural = "Quiz Response"
        unique_together = [["quiz_attempt", "question"]]
