import re
import json
import logging
from collections import defaultdict

import requests
import razorpay
import hashlib

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.conf import settings
from django.http import JsonResponse


from .models import Order, Entry, Faq, Rule


logger = logging.getLogger("app.dff2020")

rzp_client = razorpay.Client(
    auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET)
)

DOOMS_DAY_MAP = {
    "signup": "2020-06-15",  # redirect: signup -> registrations are over page
    "submission": "2020-06-15",  # redirect: submission -> submissions are over page
}


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
        return redirect("login")


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
                    return redirect("submissions")
                return redirect("registration")
            else:
                error = "Invalid email and password combination"
        else:
            error = "username or password cannot be empty"
        return redirect(reverse("login") + f"?error={error}")

    def get(self, request):
        if not request.user.is_anonymous:
            if Order.objects.filter(owner=request.user).exists():
                return redirect("submissions")
            return redirect("registration")
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
            return redirect(reverse("login") + f"?message={message}")
        return redirect(reverse("signup") + f"?error={error}")

    def get(self, request):
        if not request.user.is_anonymous:
            if Order.objects.filter(owner=request.user).exists():
                return redirect("submissions")
            return redirect("registration")
        error = request.GET.get("error") or ""
        return render(request, "dff2020/signup.html", dict(error=error))


class Registration(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "dff2020/registration.html")

    def _validate_entries(self, entries, request, existing_orders):
        error = None
        try:
            entries = list(entries)
        except Exception:
            error = "movies should be a list"
        if not entries:
            error = "No Movies were received present"
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

        return (False, error) if error else (True, None)

    def post(self, request):
        body = request.body
        logger.debug(body)
        response = {}
        error = None
        try:
            body = json.loads(body)
        except Exception as ex:
            logger.exception(ex)
            error = "Invalid data format"
        logger.debug(body)
        entries = body.get("entries")
        existing_orders = Order.objects.filter(owner=request.user.id).all()
        valid, error = self._validate_entries(entries, request, existing_orders)
        if valid:
            receipt_number = hashlib.md5(
                f"{request.user.email}:{len(existing_orders)}".encode()
            ).hexdigest()
            amount = len(entries) * 299 * 100  # in paise
            try:
                rp_order_res = rzp_client.order.create(
                    {
                        "amount": amount,
                        "currency": "INR",
                        "receipt": receipt_number,
                        "payment_capture": 0,
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

                    for entry in entries:
                        Entry.objects.create(
                            name=entry.get("name"),
                            director=entry.get("director"),
                            runtime=entry.get("runtime"),
                            link=entry.get("link"),
                            synopsis=entry.get("synopsis"),
                            order=order,
                        )
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
                "payment": "Complete" if entry.order.rzp_payment_id else "Incomplete",
            }
            for entry in entries
        ]

        context["orders"] = [
            dict(
                id=order.rzp_order_id,
                amount=order.amount,
                amount_txt=order.amount / 100.0,
                status=bool(order.rzp_payment_id),
                movies=[
                    entry.name for entry in Entry.objects.filter(order=order).all()
                ],
            )
            for order in Order.objects.filter(owner=self.request.user).all()
        ]
        context["name"] = self.request.user.get_full_name()
        context["email"] = self.request.user.email
        return context


class FAQView(LoginRequiredMixin, ListView):
    model = Faq
    template_name = "dff2020/faq.html"


class RulesView(LoginRequiredMixin, TemplateView):
    template_name = "dff2020/rules.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rules_by_type = defaultdict(list)
        for rule in Rule.objects.all():
            rules_by_type[rule.type].append(rule)
        context["rules_by_type"] = dict(rules_by_type)
        logger.debug(context)
        return context
