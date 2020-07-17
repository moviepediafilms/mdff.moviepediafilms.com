from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "dff2020"

urlpatterns = [
    path("", TemplateView.as_view(template_name="dff2020/home.html"), name="home"),
    path("signup", views.SignUpView.as_view(), name="signup"),
    path("login", views.Login.as_view(), name="login"),
    path("api/login", views.LoginApiView.as_view(), name="api-login"),
    path("api/signup/quick", views.SignupApiView.as_view(), name="api-signup-login"),
    path("api/rate/<int:shortlist_id>", views.RateApiView.as_view(), name="api-rate"),
    path(
        "api/quiz/start/<int:shortlist_id>",
        views.StartQuizView.as_view(),
        name="api-quiz-start",
    ),
    path(
        "api/quiz/<int:shortlist_id>/<int:question_id>/<int:answer>",
        views.SaveQuizResponseView.as_view(),
        name="api-quiz-question",
    ),
    path("forgot-password", views.ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset/<uid>/<token>", views.PasswordReset.as_view(), name="password-reset",),
    path(
        "order/delete/<order_id>", views.OrderDeleteView.as_view(), name="delete-order"
    ),
    path("logout", views.Logout.as_view(), name="logout"),
    path("registration", views.RegistrationOver.as_view(), name="registration",),
    path("verify_payment", views.VerifyPayment.as_view(), name="verify_payment"),
    path("submissions", views.SubmissionView.as_view(), name="submissions"),
    path("rules", views.RulesView.as_view(), name="rules"),
    path("faq", views.FAQView.as_view(), name="faq"),
    path(
        "payment/<str:status>",
        views.PaymentResultView.as_view(),
        name="verify_payment",
    ),
    path(
        "refund-policy/",
        TemplateView.as_view(template_name="dff2020/refund_policy.html"),
        name="refund-policy",
    ),
    path(
        "privacy-policy/",
        TemplateView.as_view(template_name="dff2020/privacy_policy.html"),
        name="privacy-policy",
    ),
    path("tos/", TemplateView.as_view(template_name="dff2020/tos.html"), name="tos"),
    path("judges/", views.JudgesView.as_view(), name="judges"),
    path(
        "shortlist/<int:shortlist_id>",
        views.DetailShortlistView.as_view(),
        name="shortlist-detail",
    ),
    path("shortlist/all", views.ShortlistView.as_view(), name="shortlists"),
]
