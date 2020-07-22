from django import template
from django.conf import settings
import hashlib
from urllib.parse import urlencode

register = template.Library()


@register.filter
def get_gravatar(user):
    if not user:
        return
    gender = getattr(user, "profile", None) and user.profile.gender
    avatar = {"M": "male.png", "F": "female.png", "O": "neutral.png"}.get(gender)
    profile = getattr(user, "profile", None)
    if profile:
        avatar = user.profile.avatar
    default_link = f"{settings.GRAVTAR_BASE_URL}/dff2020/img/avatar/{avatar}"
    if settings.SKIP_GRAVATAR:
        return default_link
    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        + hashlib.md5(user.email.lower().encode()).hexdigest()
        + "?"
    )
    gravatar_url += urlencode({"d": default_link})
    return gravatar_url


@register.filter
def complete_link(link):
    if link.startswith("https://") or link.startswith("http://"):
        return link
    else:
        return f"https://{link}"
