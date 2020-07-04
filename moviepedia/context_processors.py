from django.conf import settings


def base(request):
    return {"tracking_id": settings.GOOGLE_ANALYTICS}
