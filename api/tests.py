from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from clients.models import Client, ClientPhoneNumber
from couriers.models import CourierLocation
from orders.models import Order


class MobileCourierApiTests(APITestCase):
    def setUp(self):
        courier_group = Group.objects.create(name='couriers')
        self.courier = User.objects.create_user(
            username='courier-mobile', password='strong-password'
        )
        self.courier.groups.add(courier_group)
        self.other_courier = User.objects.create_user(
            username='other-courier', password='strong-password'
        )
        self.other_courier.groups.add(courier_group)
        self.non_courier = User.objects.create_user(
            username='office-user', password='strong-password'
        )
        self.client_obj = Client.objects.create(
            name='Mobil mijoz', latitude=41.311, longitude=69.279
        )
        ClientPhoneNumber.objects.create(
            client=self.client_obj,
            phone_number='+998901234567',
            is_primary=True,
        )
        self.today_order = Order.objects.create(
            client=self.client_obj,
            courier=self.courier,
            effective_date=timezone.localdate(),
            outquantity=10,
            price=19000,
        )
        self.other_order = Order.objects.create(
            client=self.client_obj,
            courier=self.other_courier,
            effective_date=timezone.localdate(),
            outquantity=5,
        )

    def authenticate(self, user=None):
        token = Token.objects.create(user=user or self.courier)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        return token

    def test_login_returns_token_only_for_courier_group(self):
        response = self.client.post(reverse('api:mobile_login'), {
            'username': self.courier.username,
            'password': 'strong-password',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['token'])
        self.assertEqual(response.data['user']['username'], self.courier.username)

        denied = self.client.post(reverse('api:mobile_login'), {
            'username': self.non_courier.username,
            'password': 'strong-password',
        })
        self.assertEqual(denied.status_code, 400)

    def test_dashboard_contains_only_authenticated_courier_orders(self):
        self.authenticate()
        response = self.client.get(reverse('api:mobile_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['summary']['pending_count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertEqual(response.data['orders'][0]['id'], self.today_order.id)
        self.assertEqual(
            response.data['orders'][0]['client']['primary_phone'],
            '+998901234567',
        )

    def test_dashboard_and_debtors_endpoint_include_active_debt_reminder(self):
        admin = User.objects.create_superuser("admin-debt", "admin@example.com", "password")
        self.today_order.mark_as_debt(admin)
        self.authenticate()

        dashboard = self.client.get(reverse('api:mobile_dashboard'))
        debtors = self.client.get(reverse('api:mobile_debtors'))

        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['debtors_count'], 1)
        self.assertTrue(dashboard.data['orders'][0]['is_debt'])
        self.assertFalse(dashboard.data['orders'][0]['can_edit'])
        self.assertEqual(debtors.data['count'], 1)
        self.assertEqual(debtors.data['results'][0]['client']['id'], self.client_obj.id)

    def test_courier_cannot_read_another_couriers_order(self):
        self.authenticate()
        response = self.client.get(reverse(
            'api:mobile_order_detail', kwargs={'order_id': self.other_order.id}
        ))
        self.assertEqual(response.status_code, 404)

    def test_order_can_be_completed_with_payments(self):
        self.authenticate()
        response = self.client.patch(
            reverse('api:mobile_order_detail', kwargs={'order_id': self.today_order.id}),
            {
                'status': 'completed',
                'inquantity': 2,
                'outquantity': 10,
                'cash_amount': '190000',
                'card_amount': '0',
                'perechesleniya_amount': '0',
                'debt_amount': '0',
                'notes': 'Yetkazildi',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.today_order.refresh_from_db()
        self.assertEqual(self.today_order.status, 'completed')
        self.assertEqual(self.today_order.cash_amount, 190000)

    def test_past_order_is_read_only(self):
        self.authenticate()
        order = Order.objects.create(
            client=self.client_obj,
            courier=self.courier,
            effective_date=timezone.localdate() - timedelta(days=1),
            outquantity=3,
        )
        response = self.client.patch(
            reverse('api:mobile_order_detail', kwargs={'order_id': order.id}),
            {'status': 'completed', 'outquantity': 3},
            format='json',
        )
        self.assertEqual(response.status_code, 409)

    def test_cancelling_order_schedules_tomorrow_copy(self):
        self.authenticate()
        response = self.client.patch(
            reverse('api:mobile_order_detail', kwargs={'order_id': self.today_order.id}),
            {'status': 'cancelled'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.filter(
            client=self.client_obj,
            courier=self.courier,
            effective_date=timezone.localdate() + timedelta(days=1),
            status='pending',
        ).exists())

    def test_location_update_rejects_invalid_and_ignores_stale_points(self):
        self.authenticate()
        location_url = reverse('api:mobile_location')
        captured_at = timezone.now()
        response = self.client.post(location_url, {
            'latitude': 41.311,
            'longitude': 69.279,
            'accuracy': 4.5,
            'speed': 3.2,
            'bearing': 180,
            'captured_at': captured_at.isoformat(),
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['accepted'])
        self.assertTrue(CourierLocation.objects.filter(courier=self.courier).exists())

        stale = self.client.post(location_url, {
            'latitude': 40.0,
            'longitude': 60.0,
            'captured_at': (captured_at - timedelta(minutes=1)).isoformat(),
        }, format='json')
        self.assertEqual(stale.status_code, 200)
        self.assertFalse(stale.data['accepted'])
        self.assertEqual(
            CourierLocation.objects.get(courier=self.courier).latitude,
            41.311,
        )

        invalid = self.client.post(location_url, {
            'latitude': 120,
            'longitude': 69.279,
        }, format='json')
        self.assertEqual(invalid.status_code, 400)

    def test_logout_revokes_token(self):
        token = self.authenticate()
        response = self.client.post(reverse('api:mobile_logout'))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
