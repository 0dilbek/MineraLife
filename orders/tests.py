import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import Client
from orders.forms import OrderForm
from orders.models import Order


class OrderDefaultPriceTests(TestCase):
    def test_new_order_uses_19000_default_price(self):
        client_obj = Client.objects.create(name="Yangi mijoz")

        order = Order.objects.create(client=client_obj)

        self.assertEqual(order.price, Decimal("19000.00"))


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


class OrderWorkingDateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="date-admin",
            email="date-admin@example.com",
            password="password",
        )
        self.client.force_login(self.admin)

    def test_order_list_preset_is_reused_by_create_form(self):
        tomorrow = timezone.localdate() + timedelta(days=1)

        self.client.get(reverse("orders:list"), {"preset": "tomorrow"})
        response = self.client.get(reverse("orders:create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["effective_date"], tomorrow)

    def test_order_list_without_query_uses_session_working_date(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        session = self.client.session
        session["orders_working_date"] = yesterday.isoformat()
        session.save()

        response = self.client.get(reverse("orders:list"))

        self.assertEqual(response.context["start_date"], yesterday)
        self.assertEqual(response.context["end_date"], yesterday)


class CancelledOrderRescheduleTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(name="Mijoz", latitude=41.31, longitude=69.24)

    def test_cancelled_order_carries_quantities_to_next_day_copy(self):
        today = timezone.localdate()
        order = Order.objects.create(
            client=self.client_obj,
            inquantity=8,
            outquantity=15,
            cash_amount=120000,
            effective_date=today,
            status="pending",
            notes="Eski izoh",
        )

        order.status = "cancelled"
        order.save()

        tomorrow = today + timedelta(days=1)
        copies = Order.objects.filter(client=self.client_obj, effective_date=tomorrow, status="pending")
        self.assertEqual(copies.count(), 1)

        copy = copies.get()
        self.assertEqual(copy.inquantity, 8)
        self.assertEqual(copy.outquantity, 15)
        self.assertEqual(copy.cash_amount, 0)
        self.assertEqual(copy.card_amount, 0)
        self.assertEqual(copy.perechesleniya_amount, 0)
        self.assertEqual(copy.debt_amount, 0)
        self.assertEqual(copy.notes, "Eski izoh")

        order.refresh_from_db()
        self.assertEqual(order.inquantity, 8)
        self.assertEqual(order.outquantity, 15)

    def test_cancelled_order_updates_existing_pending_copy_with_quantities(self):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        existing = Order.objects.create(
            client=self.client_obj,
            effective_date=tomorrow,
            status="pending",
            inquantity=4,
            outquantity=9,
            cash_amount=50000,
        )
        order = Order.objects.create(
            client=self.client_obj,
            effective_date=today,
            status="pending",
            inquantity=2,
            outquantity=6,
        )

        order.status = "cancelled"
        order.save()

        existing.refresh_from_db()
        self.assertEqual(Order.objects.filter(client=self.client_obj, effective_date=tomorrow, status="pending").count(), 1)
        self.assertEqual(existing.inquantity, 2)
        self.assertEqual(existing.outquantity, 6)
        self.assertEqual(existing.cash_amount, 0)


class EmptyZeroInputTests(TestCase):
    def test_order_form_renders_zero_values_as_empty_inputs(self):
        client_obj = Client.objects.create(name="Zero Client")
        order = Order.objects.create(client=client_obj, inquantity=0, outquantity=0)

        form = OrderForm(instance=order)

        self.assertIn('name="inquantity" value=""', str(form["inquantity"]))
        self.assertIn('name="outquantity" value=""', str(form["outquantity"]))
        self.assertIn('name="cash_amount" value=""', str(form["cash_amount"]))


class DebtWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("debt-admin", "debt@example.com", "password")
        self.client_obj = Client.objects.create(name="Qarzdor mijoz")
        self.order = Order.objects.create(
            client=self.client_obj,
            status="pending",
            outquantity=10,
            price=Decimal("19000"),
            cash_amount=Decimal("40000"),
        )
        self.client.force_login(self.admin)

    def test_admin_marks_pending_order_as_debt_and_completes_it(self):
        response = self.client.post(reverse("orders:mark_debt", args=[self.order.pk]))

        self.assertRedirects(response, reverse("orders:list"))
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_debt)
        self.assertEqual(self.order.status, "completed")
        self.assertEqual(self.order.debt_amount, Decimal("150000"))
        self.assertEqual(self.order.debt_marked_by, self.admin)

    def test_debt_is_closed_only_from_debtor_order_action(self):
        self.order.mark_as_debt(self.admin)
        response = self.client.post(reverse(
            "clients:close_debt",
            args=[self.client_obj.pk, self.order.pk],
        ))

        self.assertRedirects(response, reverse("clients:debtor_detail", args=[self.client_obj.pk]))
        self.order.refresh_from_db()
        self.assertFalse(self.order.is_debt)
        self.assertIsNotNone(self.order.debt_closed_at)
        self.assertEqual(self.order.debt_amount, Decimal("150000"))

    def test_new_order_form_warns_about_active_debtor(self):
        self.order.mark_as_debt(self.admin)
        response = self.client.get(reverse("orders:create"))

        self.assertContains(response, "Bu mijozning yopilmagan qarzi bor")
        self.assertIn(str(self.client_obj.pk), response.context["client_debt_summary"])
