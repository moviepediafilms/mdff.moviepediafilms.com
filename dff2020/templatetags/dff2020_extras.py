from django import template
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
    default_link = f"https://moviepediafilms.com/static/dff2020/img/avatar/{avatar}"
    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        + hashlib.md5(user.email.lower().encode()).hexdigest()
        + "?"
    )
    gravatar_url += urlencode({"d": default_link, "s": str(70)})
    return gravatar_url


@register.filter
def complete_link(link):
    if link.startswith("https://") or link.startswith("http://"):
        return link
    else:
        return f"https://{link}"
