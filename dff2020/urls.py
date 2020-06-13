from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.SignUp.as_view(), name="signup"),
    path("login", views.Login.as_view(), name="login"),
    path("registration", views.Registration.as_view(), name="registration"),
]
