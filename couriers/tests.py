from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from clients.models import Client
from orders.models import Order


class CourierDateFilterTests(TestCase):
    def setUp(self):
        self.courier = User.objects.create_user(username="courier", password="password")
        self.client_obj = Client.objects.create(name="Mijoz", latitude=41.31, longitude=69.24)
        self.client.force_login(self.courier)

    def test_dashboard_can_show_yesterday_orders(self):
        yesterday = localdate() - timedelta(days=1)
        order = Order.objects.create(
            client=self.client_obj,
            courier=self.courier,
            effective_date=yesterday,
            status="pending",
        )

        response = self.client.get(reverse("couriers:dashboard"), {"preset": "yesterday"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["orders"]), [order])
        self.assertFalse(response.context["can_edit_orders"])

    def test_non_today_order_cannot_be_updated_by_post(self):
        yesterday = localdate() - timedelta(days=1)
        order = Order.objects.create(
            client=self.client_obj,
            courier=self.courier,
            effective_date=yesterday,
            status="pending",
            inquantity=1,
            outquantity=1,
        )

        response = self.client.post(reverse("couriers:order_update", kwargs={"pk": order.pk}), {
            "inquantity": 5,
            "outquantity": 5,
            "status": "completed",
            "cash_amount": 90000,
            "card_amount": 0,
            "perechesleniya_amount": 0,
            "debt_amount": 0,
            "notes": "changed",
        })

        order.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.inquantity, 1)
        self.assertEqual(order.outquantity, 1)
        self.assertEqual(order.cash_amount, 0)
