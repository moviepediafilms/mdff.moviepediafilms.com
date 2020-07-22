import re
import json
import logging
import hashlib
from collections import defaultdict
import requests
import razorpay
import random
from datetime import datetime, timedelta, timezone

from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.conf import settings
from django.http import JsonResponse
from django.middleware import csrf
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.templatetags.static import static

from .constants import LATE_REGISTRATION_START_DATE, QUESTION_TO_ASK, QUIZ_TIME_LIMIT
from .models import (
    Profile,
    Order,
    Entry,
    Faq,
    Rule,
    Shortlist,
    UserRating,
    UserQuizAttempt,
    QuizResponse,
    Question,
    Option,
)
from .email import (
    send_password_reset_email,
    send_welcome_email,
    send_film_registration_email,
)
from dff2020.templatetags.dff2020_extras import get_gravatar

logger = logging.getLogger("app.dff2020")


rzp_client = razorpay.Client(
    auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET)
)

random.seed(0)


def get_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def verify_recapcha(request, recapcha_response):
    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            params={
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": recapcha_response,
                "remoteip": get_ip(request),
            },
        ).json()
        logger.debug(response)
        if response.get("success"):
            return True
        else:
            logger.error(response)
            return False
    except Exception as ex:
        logger.exception(ex)
        return False


def _is_shortlist_published(shortlist):
    ist_today = (datetime.now() + timedelta(hours=5, minutes=30)).date()
    logger.debug(f"{shortlist.publish_on} <= {ist_today}")
    return shortlist.publish_on <= ist_today


def _is_shortlist_active(shortlist):
    ist_today = (datetime.now() + timedelta(hours=5, minutes=30)).date()
    logger.debug(f"{shortlist.publish_on} <= {ist_today}")
    return shortlist.publish_on == ist_today


class Logout(View):
    def get(self, request):
        if not request.user.is_anonymous:
            logout(request)
        return redirect("dff2020:login")


class LoginMixin:
    def post(self, request):
        username = request.POST.get("email")
        password = request.POST.get("password")
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                logger.debug("user authenticated")
                login(request, user)
                return True, "User authenticated"
            else:
                error = "Invalid email and password combination"
        else:
            error = "username or password cannot be empty"
        return False, error


class Login(LoginMixin, View):
    def post(self, request):
        success, message = super().post(request)
        if success:
            user_has_orders = Order.objects.filter(owner=self.request.user).exists()
            name = "submissions" if user_has_orders else "registration"
            url = reverse(f"dff2020:{name}")
        else:
            url = reverse("dff2020:login") + f"?error={message}"
        return redirect(url)

    def get(self, request):
        if not request.user.is_anonymous:
            # if Order.objects.filter(owner=request.user).exists():
            #     return redirect("dff2020:submissions")
            return redirect("dff2020:submissions")
        error = request.GET.get("error") or ""
        message = request.GET.get("message") or ""
        return render(request, "dff2020/login.html", dict(error=error, message=message))


class SignUpMixin:
    recapcha_enabled = True

    def _get_avatar(self, gender):
        possibilities = {
            "M": [f"male{i}.png" for i in range(1, 5)],
            "F": [f"female{i}.png" for i in range(1, 5)],
            "O": ["neutral.png"],
        }.get(gender)
        return random.choice(possibilities)

    def post(self, request):
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        agree = request.POST.get("agree", "").strip()
        gender = request.POST.get("gender")
        location = request.POST.get("location")

        recapcha = request.POST.get("g-recaptcha-response", "")

        logger.debug(f"{email} {password} {agree} {recapcha}")
        if gender and gender not in "MFO":
            error = "Invalid gender value"
        elif not all([agree, name, email, password]):
            error = "Blank values are not allowed!"
        elif self.recapcha_enabled and not verify_recapcha(request, recapcha):
            error = "Invalid captcha!"
        elif User.objects.filter(email=email).exists():
            error = "This email is already registered!"
        else:
            name = re.split(r"\s+", name, 1)
            user = User.objects.create_user(email, email, password)
            user.first_name = name[0]
            if len(name) > 1:
                user.last_name = name[1]
            user.save()
            if gender:
                gender = gender.strip()
                location = location and location.strip()
                avatar = self._get_avatar(gender)
                profile = Profile.objects.create(
                    user=user, gender=gender, avatar=avatar, location=location
                )
                profile.save()
            message = "Congratulations!! Your account is created please login!"
            send_welcome_email(user)
            return True, message, user
        return False, error, None


class SignUpView(SignUpMixin, View):
    def post(self, request):
        success, message, user = super().post(request)
        param = "message" if success else "error"
        name = "login" if success else "signup"
        return redirect(reverse(f"dff2020:{name}") + f"?{param}={message}")

    def get(self, request):
        if not request.user.is_anonymous:
            if Order.objects.filter(owner=request.user).exists():
                return redirect("dff2020:submissions")
            return redirect("dff2020:registration")
        error = request.GET.get("error") or ""
        return render(request, "dff2020/signup.html", dict(error=error))


class PasswordReset(View):
    template_name = "dff2020/password_reset.html"
    token_generator = default_token_generator

    def get_user(self, uid):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
            ValidationError,
        ):
            user = None
        return user

    def get(self, request, uid, token):
        user = self.get_user(uid)
        if user is not None:
            if token == "set-password":
                session_token = self.request.session.get("_password_reset_token")
                if self.token_generator.check_token(user, session_token):
                    # If the token is valid, display the password reset form.
                    return render(request, "dff2020/password_reset.html", {})
            else:
                if self.token_generator.check_token(user, token):
                    # Store the token in the session and redirect to the
                    # password reset form at a URL without the token. That
                    # avoids the possibility of leaking the token in the
                    # HTTP Referer header.
                    self.request.session["_password_reset_token"] = token
                    redirect_url = self.request.path.replace(token, "set-password")
                    return redirect(redirect_url)

        # Display the "Password reset unsuccessful" page.
        return render(
            request, "dff2020/error.html", {"error": "Password reset unsuccessful"}
        )

    def post(self, request, uid, token):
        user = self.get_user(uid)
        token = self.request.session["_password_reset_token"]
        if self.token_generator.check_token(user, token):
            password = request.POST["password"]
            cnf_password = request.POST["confirm_password"]
            if password == cnf_password:
                user.set_password(password)
                user.save()
                del self.request.session["_password_reset_token"]
                return render(request, "dff2020/password_reset_success.html")


class ForgotPasswordView(TemplateView):
    template_name = "dff2020/forgot_password.html"
    token_generator = default_token_generator

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["msg"] = self.request.GET.get("msg", "")
        return context

    def post(self, request):
        recapcha = request.POST.get("g-recaptcha-response", "")
        if verify_recapcha(request, recapcha):
            user = User.objects.filter(email=request.POST.get("email")).first()
            if user is not None:
                token = self.token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                link = f"https://{request.get_host()}" + reverse(
                    "dff2020:password-reset", args=[uid, token]
                )
                logger.debug(link)
                send_password_reset_email(user, link)
            message = "If this email is registered! you should receive an email with link to reset your password."
        else:
            message = "Invalid captcha"
        return redirect(reverse("dff2020:forgot_password") + f"?msg={message}")


class RegistrationOver(View):
    def get(self, request):
        return redirect(reverse("dff2020:home"))


class Registration(LoginRequiredMixin, View):
    def get(self, request):
        if self.has_unpaid_first_order(request):
            return redirect(
                reverse("dff2020:submissions")
                + "?error=Please complete existing order before submitting another movie!"
            )
        return render(request, "dff2020/registration.html")

    def _validate_entries(self, entries, request, existing_orders):
        error = None
        try:
            entries = list(entries)
        except Exception:
            error = "movies should be a list"
        if not entries:
            error = "No Movies were received"
        else:
            for entry in entries:
                if not all(
                    [
                        entry.get("name"),
                        entry.get("director"),
                        entry.get("runtime"),
                        entry.get("link"),
                    ]
                ):
                    error = "All movies must have name, director, runtime and link"
                    break
                if entry.get("synopsis") is not None:
                    entry["synopsis"] = entry.get("synopsis")[:500]
                entry["name"] = entry.get("name")[:50]
                entry["director"] = entry.get("director")[:50]
                entry["link"] = entry.get("link")[:500]

            if not error:
                existing_entries = []
                existing_entry_names = []
                if existing_orders:
                    existing_entries = Entry.objects.filter(
                        order__in=[order.id for order in existing_orders]
                    ).all()
                    existing_entry_names = [entry.name for entry in existing_entries]
                entry_names_set = set(entry.get("name") for entry in entries)
                if len(entry_names_set) != len(entries) or entry_names_set.intersection(
                    existing_entry_names
                ):
                    error = "All movie names should be unique, including any previously submitted movie"
                try:
                    runtime = float(entry.get("runtime"))
                except Exception as ex:
                    logger.error(ex)
                    error = "runtime should be a number"
                else:
                    if 0 > runtime or runtime > 30:
                        error = "runtime should be between 0.1 to 30"
        return (False, error) if error else (True, None)

    def has_unpaid_first_order(self, request):
        if request.user.date_joined > LATE_REGISTRATION_START_DATE:
            orders = Order.objects.filter(owner=request.user.id).all()
            return (
                len(orders) > 0
                and len([odr for odr in orders if odr.rzp_payment_id is not None]) < 1
            )
        return False

    def post(self, request):
        if self.has_unpaid_first_order(request):
            return redirect(
                reverse("dff2020:submissions")
                + "?error=Please complete existing order before submitting another movie!"
            )
        late_user = request.user.date_joined > LATE_REGISTRATION_START_DATE
        has_paid_orders = (
            Order.objects.filter(
                owner=request.user.id, rzp_payment_id__isnull=False
            ).count()
            > 0
        )

        body = request.body
        logger.debug(body)
        response = {}
        error = None
        try:
            body = json.loads(body)
        except Exception as ex:
            logger.exception(ex)
            error = "Invalid data format"
        else:
            entries = body.get("entries")
            existing_orders = Order.objects.filter(owner=request.user.id).all()
            valid, error = self._validate_entries(entries, request, existing_orders)
            if valid:
                receipt_number = hashlib.md5(
                    f"{request.user.email}:{len(existing_orders)}".encode()
                ).hexdigest()
                amount = len(entries) * 29900  # in paise
                if late_user and not has_paid_orders:
                    amount += 9900
                try:
                    rp_order_res = rzp_client.order.create(
                        {
                            "amount": amount,
                            "currency": "INR",
                            "receipt": receipt_number,
                            "payment_capture": 1,
                            "notes": {"email": request.user.email},
                        }
                    )
                except Exception as ex:
                    logger.exception(ex)
                    error = "Error creating order!"
                else:
                    if rp_order_res.get("status") != "created":
                        error = "Error creating order!"
                        logger.error(f"Error creating order at razorpay {rp_order_res}")
                    else:
                        order = Order.objects.create(
                            owner=request.user,
                            amount=amount,
                            rzp_order_id=rp_order_res.get("id"),
                            receipt_number=rp_order_res.get("receipt"),
                        )
                        try:
                            for entry in entries:
                                Entry.objects.create(
                                    name=entry.get("name"),
                                    director=entry.get("director"),
                                    runtime=int(float(entry.get("runtime"))),
                                    link=entry.get("link"),
                                    synopsis=entry.get("synopsis"),
                                    order=order,
                                )
                        except Exception as ex:
                            order.delete()
                            logger.exception(ex)
                            error = f"Error creating your entry '{entry.get('name')}', Only english alphabets and symbols (UTF-8 charset) are allowed"
                        else:
                            response["success"] = True
                            response["message"] = "Your order is created !"
        return JsonResponse(
            response if not error else {"success": False, "error": error}
        )


class VerifyPayment(LoginRequiredMixin, View):
    def post(self, request):
        error = None
        response = {}
        try:
            data = json.loads(request.body)
        except Exception as ex:
            logger.exception(ex)
            error = "Invalid input"
        else:
            order_id = data.get("razorpay_order_id")
            order = Order.objects.filter(rzp_order_id=order_id).first()
            if not order:
                # yeah little misleading to avoid narrowing down the bruteforce attacks!
                error = "could not verify signature!"
            else:
                try:
                    rzp_client.utility.verify_payment_signature(data)
                except Exception:
                    error = "could not verify signature!"
                else:
                    rzp_payment_id = data["razorpay_payment_id"]
                    order.rzp_payment_id = rzp_payment_id
                    order.save()
                    send_film_registration_email(request.user, order)
                    try:
                        rzp_client.payment.capture(
                            rzp_payment_id, order.amount, {"currency": "INR"}
                        )
                    except Exception as ex:
                        logger.exception(ex)
                        logger.error("failed to capure the payment")
                        response["message"] = "Payment is pending!"
                    else:
                        response["message"] = "Payment Complete"
                    response["success"] = True
        return JsonResponse({"success": False, "error": error} if error else response)


class PaymentResultView(LoginRequiredMixin, TemplateView):
    template_name = "dff2020/payment_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["order_id"] = self.request.GET.get("order_id")
        context["payment_id"] = self.request.GET.get("payment_id")
        context["description"] = self.request.GET.get("description")
        context["status"] = kwargs.get("status")
        return context


class SubmissionView(LoginRequiredMixin, TemplateView):
    template_name = "dff2020/submissions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entries = Entry.objects.filter(order__owner=self.request.user).all()
        context["entries"] = [
            {
                "name": entry.name,
                "link": entry.link,
                "director": entry.director,
                "runtime": entry.runtime,
                "synopsis": entry.synopsis,
                "payment": "Complete",
            }
            for entry in entries
            if entry.order.rzp_payment_id
        ]

        context["orders"] = []
        context["pending_orders"] = []

        for order in Order.objects.filter(owner=self.request.user).all():
            order_details = dict(
                pk=order.id,
                id=order.rzp_order_id,
                amount=order.amount,
                amount_txt=order.amount / 100.0,
                status=bool(order.rzp_payment_id),
                movies=[
                    entry.name for entry in Entry.objects.filter(order=order).all()
                ],
            )
            if order.rzp_payment_id:
                context["orders"].append(order_details)
            else:
                context["pending_orders"].append(order_details)
        context["all_orders"] = context["pending_orders"] + context["orders"]
        context["name"] = self.request.user.get_full_name()
        context["email"] = self.request.user.email
        context["csrf"] = csrf.get_token(self.request)
        context["error"] = self.request.GET.get("error", "")
        return context


class OrderDeleteView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        order = get_object_or_404(
            Order, pk=kwargs.get("order_id"), owner=self.request.user
        )
        if order and order.rzp_payment_id is None:
            order.delete()
        return redirect(reverse("dff2020:submissions"))


class FAQView(ListView):
    model = Faq
    template_name = "dff2020/faq.html"


class RulesView(TemplateView):
    template_name = "dff2020/rules.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rules_by_type = defaultdict(list)
        for rule in Rule.objects.all():
            rules_by_type[rule.type].append(rule)
        context["rules_by_type"] = dict(rules_by_type)
        return context


class JudgesView(TemplateView):
    template_name = "dff2020/judges.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["judges"] = [
            dict(
                name="Suganndha Mehrotra",
                image=static("dff2020/img/smehrotra.png"),
                about="Suganndha has worked as an Assistant Director for R. Balki in Paa and Second Assistant Director for Neeraj Pandey in films like Special 26, Baby. She has also worked as an Executive Producer in Homeshop18",
            ),
            dict(
                name="Pawan Sony",
                image=static("dff2020/img/psoni.png"),
                about="Pawan Sony has written for films like Stree (dir. Amar Kaushik) Dil Dosti Etc. (dir. Manish Tiwary), Sixteen (dir. Raj Purohit) and many more. He has published a graphic novel called Bhishma published by Holy Cow.",
            ),
            dict(
                name="Nagesh Naradasi",
                image=static("dff2020/img/nnaradasi.png"),
                about="Nagesh Naradasi is an Indian film Director, who has worked predominantly in Telugu movie industry . Nagesh Naradasi has worked in popular movies like Viraaj , Desa Dimmari .",
            ),
            dict(
                name="Shubham Gaur",
                image=static("dff2020/img/sgaur.png"),
                about="Shubham has worked as a non-fiction writer in UTV And NDTV imagine for 2 yrs. It has been 10 years since he's been working as casting director in Mumbai. Some of his work includes The Lunchbox, Sense8, The Jungle Book, etc.",
            ),
            dict(
                name="Harshit Bansal",
                image=static("dff2020/img/hbansal.png"),
                about="Harshit is the founder and curator of 'Humans of Cinema', a digital film appreciation platform where cinephiles have conversations around their favorite films and the impact of cinema. He also hosts a film podcast where he chats with film artists about their craft and their love for cinema.",
            ),
            dict(
                name="Puneet Prakash",
                image=static("dff2020/img/pprakash.png"),
                about="Puneet Prakash is an award winning ad film maker who is in short time has acquired the reputation of an emotional storyteller with his ad films. His Gillette film on gender equality won the Cannes Silver Lion for India. Recently, it also won 3 Spikes Asia Awards for Film, music & entertainment & 2 Effie awards.",
            ),
        ]
        return context


class ShortlistView(TemplateView):
    template_name = "dff2020/shortlist.html"

    def _serialize(self, request, shortlist):
        user_ratings = shortlist.userrating_set.all()
        user_has_voted = any(rating.user == request.user for rating in user_ratings)
        audience_rating = 0
        if user_ratings:
            audience_rating = sum(r.rating for r in user_ratings) / len(user_ratings)
        return {
            "id": shortlist.id,
            "publish_on": shortlist.publish_on.isoformat(),
            "thumbnail": shortlist.thumbnail,
            "link": shortlist.entry.link,
            "user_has_voted": user_has_voted,
            "name": shortlist.entry.name,
            "review": shortlist.review,
            "jury_rating": "{:.2f}".format(shortlist.jury_rating),
            "audience_rating": "{:.2f}".format(audience_rating),
            "is_jury_rating_locked": shortlist.is_jury_rating_locked,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ist_today = datetime.now() + timedelta(hours=5, minutes=30)
        context["locked_shortlists"] = [
            self._serialize(self.request, shortlist)
            for shortlist in Shortlist.objects.filter(publish_on=ist_today).all()
        ]
        context["unlocked_shortlists"] = [
            self._serialize(self.request, shortlist)
            for shortlist in Shortlist.objects.filter(publish_on__lt=ist_today).all()
        ]
        return context


class DetailShortlistView(TemplateView):
    template_name = "dff2020/shortlist_details.html"

    def get(self, request, *args, **kwargs):
        shortlist_id = kwargs.get("shortlist_id")
        try:
            movie = Shortlist.objects.get(pk=shortlist_id)
        except Shortlist.DoesNotExist as ex:
            logger.exception(ex)
            return redirect("dff2020:shortlists")
        else:
            if not _is_shortlist_published(movie):
                return redirect("dff2020:shortlists")
        is_active = _is_shortlist_active(movie)
        dummy_rating = 100
        context = self.get_context_data(**kwargs)
        context["csrf"] = csrf.get_token(self.request)
        context["movie"] = movie
        user_ratings = movie.userrating_set.all()
        user_voted = not is_active or any(
            rating.user == self.request.user for rating in user_ratings
        )
        context["user_voted"] = user_voted

        context["jury_rating"] = "{:.2f}".format(movie.jury_rating * 10)
        audience_rating = (
            sum(r.rating for r in user_ratings) / len(user_ratings)
            if len(user_ratings)
            else 0
        )
        context["audience_rating"] = "{:.2f}".format(audience_rating * 10)
        if not user_voted:
            context["jury_rating"] = "{:.2f}".format(dummy_rating)
            context["audience_rating"] = "{:.2f}".format(dummy_rating)

        context["reviews"] = [
            dict(
                profile_pic=get_gravatar(rating.user),
                user_full_name=rating.user.get_full_name(),
                rating="{:.0f}/10".format(rating.rating),
                content=rating.review,
            )
            for rating in user_ratings
            if rating.review
        ]
        if self.request.user.is_authenticated:
            quiz_attempt = UserQuizAttempt.objects.filter(
                shortlist=movie, user=self.request.user
            ).first()
            if quiz_attempt:
                now = datetime.now(timezone.utc)
                quiz_over_at = quiz_attempt.start_time + timedelta(
                    seconds=QUIZ_TIME_LIMIT
                )
                logger.debug(now.isoformat())
                logger.debug(quiz_over_at.isoformat())
                context["quiz_over"] = (
                    not is_active
                    or now >= quiz_over_at
                    or quiz_attempt.quizresponse_set.count() == QUESTION_TO_ASK
                )
        if "quiz_over" not in context:
            context["quiz_over"] = not is_active

        return self.render_to_response(context)


def _serialize_attempt(request, attempt):
    responses = attempt.quizresponse_set.all()
    if len(responses) > 3:
        # we have a problem
        pass
    response_score = sum(res.selected_option.is_correct for res in responses)
    time_start = attempt.start_time
    time_end = attempt.start_time + timedelta(seconds=QUIZ_TIME_LIMIT)
    if len(responses) == QUESTION_TO_ASK:
        time_end = max(res.submit_at for res in responses)
    logger.debug(f"{time_start} {time_end}")
    time_taken = time_end - time_start
    logger.debug(f"time_score {time_taken.seconds} + {time_taken.microseconds}")
    time_taken = float(f"{time_taken.seconds}.{time_taken.microseconds}")
    profile = getattr(attempt.user, "profile", None)
    res = {
        "id": attempt.id,
        "profile_pic": get_gravatar(attempt.user),
        "name": attempt.user.get_full_name().title(),
        "location": profile and profile.location,
        "gender": profile and profile.gender,
        "total_time": time_taken,
        "total_time_left": QUIZ_TIME_LIMIT - time_taken,
        "score": response_score,
        "correct": response_score,
        "asked": [True] * response_score + [False] * (QUESTION_TO_ASK - response_score),
        "is_viewer": attempt.user == request.user,
    }
    return res


def _get_user_attempts_by_rank(request, shortlist):
    return list(
        sorted(
            [
                _serialize_attempt(request, attempt)
                for attempt in UserQuizAttempt.objects.filter(shortlist=shortlist).all()
            ],
            key=lambda item: (item.get("score"), item.get("total_time_left")),
            reverse=True,
        )
    )


class ResultShortlistApiView(View):
    def get(self, request, shortlist_id):
        data = {}
        error = None
        message = None
        try:
            shortlist = Shortlist.objects.get(pk=shortlist_id)
        except Shortlist.DoesNotExist as ex:
            logger.exception(ex)
            error = "No such shortlist"
        else:
            if not _is_shortlist_published(shortlist):
                error = "Shortlist not yet published"

        if not error:
            data["attempts"] = _get_user_attempts_by_rank(request, shortlist)

        data["success"] = not error
        data["error"] = error
        data["message"] = message
        return JsonResponse(data)


class ResultShortlistView(TemplateView):
    template_name = "dff2020/shortlist_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["shortlist_id"] = kwargs.get("shortlist_id")
        return context


class LoginApiView(LoginMixin, View):
    def post(self, request):
        success, message = super().post(request)
        data = {"success": success}
        if success:
            data["csrf"] = csrf.get_token(self.request)
        else:
            data["error"] = message
        return JsonResponse(data)


class SignupApiView(SignUpMixin, View):
    recapcha_enabled = False

    def post(self, request):
        success, message, user = super().post(request)
        data = {"success": success}
        if success:
            login(request, user)
            data["csrf"] = csrf.get_token(self.request)
        else:
            data["error"] = message
        return JsonResponse(data)


class RateApiView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        shortlist_id = kwargs.get("shortlist_id")
        rating = request.POST.get("rating")
        review = request.POST.get("review")
        if review:
            review = review[:2000]
        error = None
        message = None
        reload = False
        try:
            rating = float(rating)
            if rating < 0 or rating > 10:
                raise Exception("Rating can only be between 0, 10")
        except TypeError as ex:
            logger.exception(ex)
            error = "rating is not integer"
        except Exception as ex:
            logger.exception(ex)
            error = str(ex)
        else:
            try:
                shortlist = Shortlist.objects.get(pk=shortlist_id)
            except Shortlist.DoesNotExist as ex:
                logging.exception(ex)
                error = "Invalid shortlist"
            else:
                if not _is_shortlist_active(shortlist):
                    error = "Shortlist not open for rating"
                else:
                    user_rating = UserRating.objects.filter(
                        shortlist=shortlist, user=request.user
                    ).first()
                    if user_rating:
                        reload = True
                        error = "You have already rated this movie"
                    else:
                        UserRating.objects.create(
                            shortlist=shortlist,
                            user=request.user,
                            rating=rating,
                            review=review,
                        )
                    message = "You have successfully submited your rating"

        return JsonResponse(
            {
                "success": not bool(error),
                "error": error,
                "message": message,
                "reload": reload,
            }
        )


def _get_next_question(attempt):
    answered_questions = [
        entry.question
        for entry in QuizResponse.objects.filter(quiz_attempt=attempt).all()
    ]
    if len(answered_questions) < QUESTION_TO_ASK:
        remaining_questions = (
            Question.objects.filter(shortlist=attempt.shortlist,)
            .exclude(id__in=[q.id for q in answered_questions],)
            .all()
        )
        if not remaining_questions:
            return False, "No remainig questions found"
        else:
            question = random.choice(remaining_questions)
            options = Option.objects.filter(question=question).all()
            question_dict = {
                "id": question.id,
                "content": question.text,
                "options": [
                    {"id": option.id, "content": option.text} for option in options
                ],
            }
            return True, question_dict
    return False, "Already answered all questions"


class StartQuizView(LoginRequiredMixin, View):
    def get(self, request, shortlist_id):
        response = {}
        error = None
        try:
            shortlist = Shortlist.objects.get(pk=shortlist_id)
            if not _is_shortlist_active(shortlist):
                raise Exception("Shortlist is not open for quiz")
            if not UserRating.objects.filter(
                shortlist=shortlist, user=request.user
            ).exists():
                raise Exception("You should rate before you start taking quiz")
        except Shortlist.DoesNotExist as ex:
            logger.exception(ex)
            error = "Invalid shortlist"
        except Exception as ex:
            error = str(ex)
        else:
            try:
                response["new"] = False
                attempt = UserQuizAttempt.objects.get(
                    shortlist=shortlist, user=request.user
                )
            except UserQuizAttempt.DoesNotExist as ex:
                logger.warning(str(ex))
                # check min 3 questions should be there
                questions_count = Question.objects.filter(shortlist=shortlist).count()
                logger.info(f"found {questions_count} questions")
                if questions_count < QUESTION_TO_ASK:
                    error = "Sufficient questions are not ready, please try again after some time!"

                if not error:
                    attempt = UserQuizAttempt.objects.create(
                        user=request.user, shortlist=shortlist
                    )
                    response["new"] = True

        if not error:
            response["start_time"] = attempt.start_time
            response["quiz_time_limit"] = QUIZ_TIME_LIMIT
            success, result = _get_next_question(attempt)
            response["question_count"] = attempt.quizresponse_set.count()
            logger.debug(f"{success} {result}")
            if success:
                response["question"] = result
            else:
                error = result
        if error:
            response["success"] = False
            response["error"] = error
        else:
            response["success"] = True

        return JsonResponse(response)


class SaveQuizResponseView(LoginRequiredMixin, View):
    def get(self, request, shortlist_id, question_id, answer):
        res_body = {}
        error = None
        try:
            shortlist = Shortlist.objects.get(pk=int(shortlist_id))
            question = Question.objects.get(pk=int(question_id))
            option = Option.objects.get(question=question, pk=int(answer))
        except Shortlist.DoesNotExists:
            error = "Invalid Shortlist"
        except Question.DoesNotExists:
            error = "Invalid Question"
        except Option.DoesNotExists:
            error = "Invalid Option"
        else:
            try:
                attempt = UserQuizAttempt.objects.get(
                    shortlist=shortlist, user=request.user
                )
            except UserQuizAttempt.DoesNotExists:
                error = "Start the quiz before answering the question!"
            else:
                now = datetime.now(timezone.utc)
                quiz_over_at = attempt.start_time + timedelta(seconds=QUIZ_TIME_LIMIT)
                if now >= quiz_over_at:
                    error = "Quiz time is up!"
                elif attempt.quizresponse_set.count() >= QUESTION_TO_ASK:
                    error = f"You have already answered {QUESTION_TO_ASK} questions!"
                else:
                    try:
                        logging.info(
                            f"Quiz response:{request.user.username}:{attempt.id}:{question.id}:{option.id}"
                        )
                        QuizResponse.objects.create(
                            quiz_attempt=attempt,
                            question=question,
                            selected_option=option,
                        )
                    except IntegrityError as ex:
                        logger.exception(ex)
                        error = "We have already saved your response for this question"
                    except Exception as ex:
                        logger.exception(ex)
                        error = "An error occured while saving your response, refresh the page and try again!"
                    else:
                        res_body["previous_correct_answer"] = option.is_correct
                        question_count = attempt.quizresponse_set.count()
                        res_body["question_count"] = question_count
                        if question_count >= QUESTION_TO_ASK:
                            success, value = True, {}
                        else:
                            success, value = _get_next_question(attempt)
                        if success:
                            res_body["question"] = value
                        else:
                            error = value
        if error:
            res_body["success"] = False
            res_body["error"] = error
        else:
            res_body["success"] = True
        return JsonResponse(res_body)
