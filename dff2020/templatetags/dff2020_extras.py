from django import template
import hashlib
from urllib.parse import urlencode

register = template.Library()


@register.filter
def get_gravatar(user):
    default_avatar = {
        "M": "avatar/male.png",
        "F": "avatar/female.png",
        None: "avatar/neutral.png",
    }.get(getattr(user, "profile", None) and user.profile.gender)
    avatar = user.profile.avatar or default_avatar
    default_link = f"https://moviepediafilms.com/static/dff2020/img/{avatar}"
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
