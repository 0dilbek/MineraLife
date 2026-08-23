from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Product


class ProductModernUiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="product-admin",
            email="product@example.com",
            password="password",
        )
        self.product = Product.objects.create(
            name="Mineral suv",
            description="Sinov mahsuloti",
            price=Decimal("19000.00"),
        )
        self.client.force_login(self.admin)
        self.client.post(reverse("set_admin_ui"), {"mode": "modern"})

    def test_product_list_uses_modern_catalog_components(self):
        response = self.client.get(reverse("products:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base_modern.html")
        self.assertContains(response, "Katalog")
        self.assertContains(response, "1 ta mahsulot")

    def test_product_detail_has_working_order_action(self):
        response = self.client.get(reverse("products:detail", args=[self.product.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("orders:create"))
