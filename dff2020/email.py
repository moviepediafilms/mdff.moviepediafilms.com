from django.conf import settings
import sendgrid
import logging

logger = logging.getLogger("app.dff2020.email")

sg = sendgrid.SendGridAPIClient(settings.SENDGRID_API_KEY)


def send_welcome_email(user):
    data = _get_base_data(user)
    data["from"]["template_id"] = settings.SENDGRID_TEMPLATE_WELCOME
    _send(data)


def send_password_reset_email(user):
    data = _get_base_data(user)
    data["from"]["template_id"] = settings.SENDGRID_TEMPLATE_PASSWORD_RESET
    _send(data)


def send_film_registration_email(user):
    data = _get_base_data(user)
    data["from"]["template_id"] = settings.SENDGRID_TEMPLATE_FILM_REG
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
    else:
        logger.debug(f"sendgrid: {response}")
