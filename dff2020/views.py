from django.shortcuts import render


def login(request):
    return render(request, "dff2020/login.html", {})


def signup(request):
    return render(request, "dff2020/signup.html", {})


def registration(request):
    return render(request, "dff2020/registration.html", {})
