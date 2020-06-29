import re
import json
import logging
import hashlib
from collections import defaultdict
from datetime import datetime
import requests
import razorpay

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

from .models import Order, Entry, Faq, Rule
from .email import (
    send_password_reset_email,
    send_welcome_email,
    send_film_registration_email,
)


logger = logging.getLogger("app.dff2020")

LATE_DATE = datetime.strptime("2020-07-01T00:00:00+05:30", "%Y-%m-%dT%H:%M:%S%z")

rzp_client = razorpay.Client(
    auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET)
)


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


class Logout(View):
    def get(self, request):
        if not request.user.is_anonymous:
            logout(request)
        return redirect("dff2020:login")


class Login(View):
    def post(self, request):
        username = request.POST.get("email")
        password = request.POST.get("password")
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                logger.debug("user authenticated")
                login(request, user)
                if Order.objects.filter(owner=user).exists():
                    return redirect("dff2020:submissions")
                return redirect("dff2020:registration")
            else:
                error = "Invalid email and password combination"
        else:
            error = "username or password cannot be empty"
        return redirect(reverse("dff2020:login") + f"?error={error}")

    def get(self, request):
        if not request.user.is_anonymous:
            if Order.objects.filter(owner=request.user).exists():
                return redirect("dff2020:submissions")
            return redirect("dff2020:registration")
        error = request.GET.get("error") or ""
        message = request.GET.get("message") or ""
        return render(request, "dff2020/login.html", dict(error=error, message=message))


class SignUp(View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        agree = request.POST.get("agree", "").strip()

        recapcha = request.POST.get("g-recaptcha-response", "")

        logger.debug(f"{email} {password} {agree} {recapcha}")
        if not all([agree, name, email, password]):
            error = "Blank values are not allowed!"
        elif not verify_recapcha(request, recapcha):
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
            message = "Congratulations!! Your account is created please login!"
            send_welcome_email(user)
            return redirect(reverse("dff2020:login") + f"?message={message}")
        return redirect(reverse("dff2020:signup") + f"?error={error}")

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
        if request.user.date_joined > LATE_DATE:
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
        late_user = request.user.date_joined > LATE_DATE
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
                    rp_order_res = {"status": "created", "id": "xyz", "receipt": "123"}
                    # rp_order_res = rzp_client.order.create(
                    #     {
                    #         "amount": amount,
                    #         "currency": "INR",
                    #         "receipt": receipt_number,
                    #         "payment_capture": 1,
                    #         "notes": {"email": request.user.email},
                    #     }
                    # )
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
                            response[
                                "message"
                            ] = "your order is created! waiting for youto complete payment!"
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
        if order:
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
