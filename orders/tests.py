import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from clients.models import Client
from orders.models import Order


class BulkAssignCourierToOrdersTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.courier_group = Group.objects.create(name="couriers")
        self.courier = User.objects.create_user(username="courier", password="password")
        self.courier.groups.add(self.courier_group)
        self.other_user = User.objects.create_user(username="operator", password="password")
        self.client_obj = Client.objects.create(name="Mijoz", latitude=41.31, longitude=69.24)
        self.orders = [
            Order.objects.create(client=self.client_obj, outquantity=1),
            Order.objects.create(client=self.client_obj, outquantity=2),
        ]
        self.url = reverse("orders:bulk_assign_courier")

    def post_json(self, payload):
        self.client.force_login(self.admin)
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_bulk_assigns_selected_orders_to_courier(self):
        response = self.post_json({
            "order_ids": [order.id for order in self.orders],
            "courier_id": self.courier.id,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated_count"], 2)
        self.assertEqual(
            set(Order.objects.filter(courier=self.courier).values_list("id", flat=True)),
            {order.id for order in self.orders},
        )

    def test_bulk_assign_rejects_empty_selection(self):
        response = self.post_json({"order_ids": [], "courier_id": self.courier.id})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_bulk_assign_rejects_non_courier_user_when_group_exists(self):
        response = self.post_json({
            "order_ids": [self.orders[0].id],
            "courier_id": self.other_user.id,
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
