from django.test import TestCase
from django.shortcuts import reverse
from django.contrib import auth


app_name = "dff2020"


class LogoutTest(TestCase):
    def setUp(self):
        self.client.login(username="fred", password="secret")

    def test_logout(self):
        res = self.client.get(reverse(f"{app_name}:logout"))
        self.assertRedirects(res, reverse("dff2020:login"))
        user = auth.get_user(self.client)
        self.assertFalse(user.is_authenticated)


class LoginTest(TestCase):
    def test_get(self):
        res = self.client.get(reverse(f"{app_name}:login"))
        self.assertTemplateUsed(res, template_name="dff2020/login.html")
        print(dir(res.content))

    def test_post(self):
        self.client.post(reverse(f"{app_name}:login"))
