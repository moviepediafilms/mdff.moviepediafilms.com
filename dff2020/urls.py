from django.urls import path
from . import views

urlpatterns = [
    path("", views.SignUp.as_view(), name="signup"),
    path("login", views.Login.as_view(), name="login"),
    path("registration", views.Registration.as_view(), name="registration"),
    path("verify_payment", views.VerifyPayment.as_view(), name="verify_payment"),
]
