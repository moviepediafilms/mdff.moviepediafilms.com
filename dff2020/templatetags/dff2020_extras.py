from django import template
import hashlib
from urllib.parse import urlencode

register = template.Library()


@register.filter
def get_gravatar(user):
    default_link = "https://moviepediafilms.com/static/dff2020/img/avatar.jpg"
    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        + hashlib.md5(user.email.lower().encode()).hexdigest()
        + "?"
    )
    gravatar_url += urlencode({"d": default_link, "s": str(70)})
    return gravatar_url
