from django.test import TestCase
from django.shortcuts import reverse
from django.contrib.auth.models import User
from datetime import datetime
from dff2020.models import Order
from unittest import mock


class LoggedInTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="password")
        assert self.client.login(username="test", password="password")

    def tearDown(self):
        self.user.delete()
        return super().tearDown()


# feature disabled/inactive
class RegistrationTestCase:
    def set_late_user(self, is_late):
        after_late_regitation_date = datetime.strptime(
            "2020-07-01T00:00:01+05:30", "%Y-%m-%dT%H:%M:%S%z"
        )
        before_late_regitation_date = datetime.strptime(
            "2020-06-30T00:00:01+05:30", "%Y-%m-%dT%H:%M:%S%z"
        )
        self.user.date_joined = (
            after_late_regitation_date if is_late else before_late_regitation_date
        )
        self.user.save()

    @mock.patch("dff2020.views.rzp_client")
    def create_order(self, rzp_client):
        rzp_client.order.create.return_value = {
            "status": "created",
            "id": "order_123",
            "receipt": "receipt_123",
        }
        data = {
            "entries": [
                {
                    "name": "Dummy Movie",
                    "runtime": 20,
                    "synopsis": "This is a dummy synopsis",
                    "director": "Test",
                    "link": "google.com",
                }
            ]
        }
        return self.client.post(
            reverse("dff2020:registration"), data=data, content_type="application/json"
        )

    def test_late_user_first_order(self):
        """Late users should be able to create only one order with 99INR extra"""
        self.set_late_user(True)
        res = self.create_order()
        self.assertEquals(res.status_code, 200)
        orders = Order.objects.filter(owner=self.user).all()
        self.assertEquals(len(orders), 1)
        self.assertEquals(orders[0].amount, 29900 + 9900)

    def test_late_user_order_after_paid_first(self):
        """Late users should be able to create order at 299INR after paying the first one"""
        Order.objects.create(
            rzp_order_id="order_XXX",
            rzp_payment_id="pay_XXX",
            receipt_number="receipt_XXX",
            amount=29900,
            owner=self.user,
        )
        self.set_late_user(True)
        res = self.create_order()
        self.assertEquals(res.status_code, 200)
        orders = Order.objects.filter(owner=self.user).all()
        self.assertEquals(len(orders), 2)
        self.assertEquals(orders[0].amount, 29900)
        self.assertEquals(orders[1].amount, 29900)

    def test_late_user_order_after_unpaid_first(self):
        """Late users should not be able to create order if the first is unpaid"""
        Order.objects.create(
            rzp_order_id="order_XXX",
            receipt_number="receipt_XXX",
            amount=29900,
            owner=self.user,
        )
        self.set_late_user(True)
        res = self.create_order()
        self.assertRedirects(
            res,
            reverse("dff2020:submissions")
            + "?error=Please complete existing order before submitting another movie!",
        )

    def test_old_user_order(self):
        """Old users should be able to create order with no extra fee"""
        self.set_late_user(False)
        res = self.create_order()
        self.assertEquals(res.status_code, 200)
        orders = Order.objects.filter(owner=self.user).all()
        self.assertEquals(len(orders), 1)
        self.assertEquals(orders[0].amount, 29900)

    def test_old_user_order_after_unpaid_first(self):
        """Late users should not be able to create order if the first is unpaid"""
        Order.objects.create(
            rzp_order_id="order_XXX",
            receipt_number="receipt_XXX",
            amount=29900,
            owner=self.user,
        )
        self.set_late_user(False)
        res = self.create_order()
        self.assertEquals(res.status_code, 200)
        orders = Order.objects.filter(owner=self.user).all()
        self.assertEquals(len(orders), 2)
        self.assertEquals(orders[0].amount, 29900)
        self.assertEquals(orders[1].amount, 29900)


class SubmissionTestCase(LoggedInTestCase):
    def setUp(self):
        super().setUp()
        self.order = Order.objects.create(
            rzp_order_id="order_XXX",
            receipt_number="receipt_XXX",
            amount=29900,
            owner=self.user,
        )

    def tearDown(self):
        self.order.delete()
        return super().tearDown()

    def test_error_is_visible(self):
        res = self.client.get(
            reverse("dff2020:submissions") + "?error=this_is_an_error"
        )
        self.assertInHTML("this_is_an_error", res.content.decode())

    def test_delete_button_hidden_on_unpaid(self):
        res = self.client.get(reverse("dff2020:submissions"))
        self.assertNotContains(
            res, reverse("dff2020:delete-order", args=(self.order.id,))
        )

    def test_delete_button_hidden_on_paid(self):
        self.order.rzp_payment_id = "pay_XXX"
        self.order.save()
        res = self.client.get(reverse("dff2020:submissions"))
        self.assertNotContains(
            res, reverse("dff2020:delete-order", args=(self.order.id,))
        )

    def test_should_not_delete_paid_order(self):
        self.order.rzp_payment_id = "pay_XXX"
        self.order.save()
        self.client.get(reverse("dff2020:delete-order", args=(self.order.id,)))
        self.assertEqual(Order.objects.filter(owner=self.user).count(), 1)


class SignupTestCase(TestCase):
    def setUp(self):
        self.send_welcome_email_patcher = mock.patch("dff2020.views.send_welcome_email")
        self.verify_recapcha_patcher = mock.patch("dff2020.views.verify_recapcha")
        self.send_welcome_email = self.send_welcome_email_patcher.start()
        self.verify_recapcha = self.verify_recapcha_patcher.start()

    def tearDown(self):
        self.send_welcome_email_patcher.stop()
        self.verify_recapcha_patcher.stop()

    def test_new_account_create(self):
        "Allow new users to create account"
        self.verify_recapcha.return_value = True
        res = self.client.post(
            reverse("dff2020:signup"),
            data={
                "name": "A",
                "email": "abcd@gmail.com",
                "password": "B",
                "agree": True,
                "g-recaptcha-response": "sdfhgjjsdf",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(User.objects.filter(username="abcd@gmail.com").count(), 1)

    def test_new_account_create(self):
        "New account creation not allowed after END_USER_CREATION_DATE"
        self.verify_recapcha.return_value = True
        res = self.client.post(
            reverse("dff2020:signup"),
            data={
                "name": "A",
                "email": "abcd@gmail.com",
                "password": "B",
                "agree": True,
                "g-recaptcha-response": "sdfhgjjsdf",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(User.objects.filter(username="abcd@gmail.com").count(), 1)
