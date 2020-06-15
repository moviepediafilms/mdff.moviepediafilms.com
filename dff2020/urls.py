from django.urls import path
from . import views

urlpatterns = [
    path("", views.SignUp.as_view(), name="signup"),
    path("login", views.Login.as_view(), name="login"),
    path("logout", views.Logout.as_view(), name="logout"),
    path("registration", views.Registration.as_view(), name="registration"),
    path("verify_payment", views.VerifyPayment.as_view(), name="verify_payment"),
    path("submissions", views.SubmissionView.as_view(), name="submissions"),
    path("rules", views.RulesView.as_view(), name="rules"),
    path("faq", views.FAQView.as_view(), name="faq"),
    path(
        "payment/<str:status>",
        views.PaymentResultView.as_view(),
        name="verify_payment",
    ),
]
