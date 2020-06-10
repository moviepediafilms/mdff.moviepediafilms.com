from django.shortcuts import render


def home(request):
    return render(request, "dff2020/wip.html", {})
