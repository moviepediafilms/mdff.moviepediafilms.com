import re
import os
import logging

import requests
import razorpay

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.views import View
from django.conf import settings


logger = logging.getLogger("app.dff2020")

client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))


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
    @method_decorator(login_required)
    def get(self, request):
        return render(request, "dff2020/registration.html")

    @method_decorator(login_required)
    def post(self, request):
        return render(
            request, "dff2020/registration.html", dict(error="cannot login now!")
        )
