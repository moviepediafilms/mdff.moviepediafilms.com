from django.core.management.base import BaseCommand
from django.conf import settings
from dff2020.models import User
from dff2020.email import _send
import logging


logger = logging.getLogger("app.dff2020.commands")


class Command(BaseCommand):
    help = "Sends email to all users"

    def handle(self, *args, **kwargs):
        all_users = User.objects.all()
        personalizations = []

        logger.info(f"found {len(all_users)} users")
        for user in all_users:
            personalizations.append(
                {
                    "to": [{"email": user.email, "name": user.get_full_name()}],
                    "dynamic_template_data": {"name": user.first_name},
                }
            )
        body = {
            "template_id": "d-fba944f29af840258c443104560d90b4",
            "from": {"email": settings.SENDGRID_EMAIL, "name": settings.SENDGRID_NAME},
            "reply_to": {
                "email": settings.SENDGRID_REPLY_TO,
                "name": settings.SENDGRID_NAME,
            },
            "personalizations": personalizations,
        }
        logger.debug(str(body))
        _send(body)
