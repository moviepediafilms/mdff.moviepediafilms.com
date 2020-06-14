import re
import json
import logging

import requests
import razorpay
import hashlib

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views import View
from django.conf import settings
from django.http import JsonResponse
from .models import Order, Entry

logger = logging.getLogger("app.dff2020")

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


class Login(View):
    def post(self, request):
        username = request.POST.get("email")
        password = request.POST.get("password")
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                logger.debug("user authenticated")
                login(request, user)
                return redirect("registration")
            else:
                error = "Invalid email and password combination"
        else:
            error = "username or password cannot be empty"
        return redirect(reverse("login") + f"?error={error}")

    def get(self, request):
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
                    response["order_id"] = order.rzp_order_id
                    response["amount"] = amount
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
            data = json.loads(request.data)
        except Exception:
            error = "Invalid input"
        else:
            order_id = data.get("razorpay_order_id")
            order = Order.objects.filter(rzp_order_id=order_id).first()
            if not order:
                # yeah little misleading to avoid narrowing down the bruteforce
                error = "could not verify signature!"
            else:
                try:
                    rzp_client.utility.verify_payment_signature(data)
                except Exception:
                    error = "could not verify signature!"
                else:
                    order.rzp_payment_id = data["razorpay_payment_id"]
                    order.save()
                    response["success"] = True
                    response["message"] = "Payment Complete"
        return JsonResponse({"success": False, "error": error} if error else response)
