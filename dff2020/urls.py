from django.urls import path
from . import views

app_name = "dff2020"

urlpatterns = [
    path("", views.SignUp.as_view(), name="signup"),
    path("login", views.Login.as_view(), name="login"),
    path("forgot-password", views.ForgotPasswordView.as_view(), name="forgot_password"),
    path(
        "reset/<str:uid>/<str:token>",
        views.PasswordReset.as_view(),
        name="password-reset",
    ),
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
