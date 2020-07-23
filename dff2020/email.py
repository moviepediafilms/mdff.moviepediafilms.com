import logging
import json

import sendgrid

from django.conf import settings

from .models import Entry


logger = logging.getLogger("app.dff2020.email")
sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)


def send_welcome_email(user):
    data = _get_base_data(user)
    data["template_id"] = settings.SENDGRID_TEMPLATE_WELCOME
    _send(data)


def send_password_reset_email(user, link):
    data = _get_base_data(user)
    data["template_id"] = settings.SENDGRID_TEMPLATE_PASSWORD_RESET
    dynamic_template_data = data["personalizations"][0]["dynamic_template_data"]
    dynamic_template_data["link"] = link
    _send(data)


def send_film_registration_email(user, order):
    data = _get_base_data(user)
    data["template_id"] = settings.SENDGRID_TEMPLATE_FILM_REG
    dynamic_template_data = data["personalizations"][0]["dynamic_template_data"]
    dynamic_template_data["movies"] = ", ".join(
        [e.name for e in Entry.objects.filter(order=order).all() if e.name]
    )
    _send(data)


def _get_base_data(user):
    return {
        "from": {"email": settings.SENDGRID_EMAIL, "name": settings.SENDGRID_NAME},
        "reply_to": {
            "email": settings.SENDGRID_REPLY_TO,
            "name": settings.SENDGRID_NAME,
        },
        "personalizations": [
            {
                "to": [{"email": user.email, "name": user.get_full_name()}],
                "dynamic_template_data": {"name": user.get_full_name()},
            }
        ],
    }


def _send(data):
    try:
        response = sg.client.mail.send.post(request_body=data)
    except Exception as ex:
        logger.exception(ex)
        logger.warning("sending email failed!")
        logger.debug(data)
        logger.debug(ex.body)
    else:
        logger.debug(f"sendgrid: {response.status_code}")
