from django.core.management.base import BaseCommand
from django.conf import settings
from dff2020.models import Order
from dff2020.email import _send
from datetime import datetime, date
import logging


logger = logging.getLogger("app.dff2020.commands")


class Command(BaseCommand):
    help = "Sends email to all pending users, to complete their orders"

    def handle(self, *args, **kwargs):
        july_10 = datetime.strptime(
            "2020-07-10T00:00:00+05:30", "%Y-%m-%dT%H:%M:%S%z"
        ).date()
        today = date.today()
        days = (july_10 - today).days
        pending_orders = Order.objects.filter(rzp_payment_id__isnull=True).all()
        personalizations = []

        logger.info(f"found {len(pending_orders)} pending orders")
        for order in pending_orders:
            # '"Kalyug", "DDLJ" and "Dhundh"'
            entry_names = [f'"{entry.name}"' for entry in order.entry_set.all()]
            if len(entry_names) == 0:
                logger.warning(f"No entries found for order {order.id}, skipped")
                continue
            if len(entry_names) > 1:
                entry_names = ", ".join(entry_names[:-1]) + f" and {entry_names[-1]}"
            else:
                entry_names = entry_names[0]
            user = order.owner
            personalizations.append(
                {
                    "to": [{"email": user.email, "name": user.get_full_name()}],
                    "dynamic_template_data": {
                        "name": user.get_full_name(),
                        "days": days,
                        "movie_names": entry_names,
                        "amount": int(order.amount / 100),
                    },
                }
            )
        body = {
            "template_id": "d-97f8f047e8b7418990e2becd578dadcb",
            "from": {"email": settings.SENDGRID_EMAIL, "name": settings.SENDGRID_NAME},
            "reply_to": {
                "email": settings.SENDGRID_REPLY_TO,
                "name": settings.SENDGRID_NAME,
            },
            "personalizations": personalizations,
        }
        logger.debug(str(body))
        _send(body)
