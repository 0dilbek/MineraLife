from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from clients.models import Client
from common.text_utils import normalize_multiline_text


class SiteNameConfigurationTests(TestCase):
    @override_settings(SITE_NAME="Configured Brand")
    def test_login_page_uses_configured_site_name(self):
        response = self.client.get(reverse("login"))

        self.assertContains(response, "Configured Brand")
        self.assertNotContains(response, ">Ocean<")


class ClassicAdminInterfaceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="ui-admin",
            email="ui@example.com",
            password="password",
        )
        self.client.force_login(self.admin)

    def test_admin_dashboard_opens_classic_directly(self):
        response = self.client.get(reverse("admin_welcome"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_welcome.html")
        self.assertEqual(response.context["ui_base_template"], "base.html")

    def test_main_admin_sections_follow_selected_interface(self):
        section_urls = (
            reverse("orders:list"),
            reverse("clients:list"),
            reverse("products:list"),
            reverse("couriers:list"),
            reverse("hisobotlar:reports"),
        )

        for url in section_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "base.html")


class NormalizeMultilineTextTests(TestCase):
    def test_converts_literal_escape_sequences(self):
        raw = "Samarqand 74\\r\\nMoykadan\\r\\nподъезд 2"
        self.assertEqual(
            normalize_multiline_text(raw),
            "Samarqand 74\nMoykadan\nподъезд 2",
        )

    def test_converts_real_crlf(self):
        raw = "Birinchi qator\r\nIkkinchi qator"
        self.assertEqual(
            normalize_multiline_text(raw),
            "Birinchi qator\nIkkinchi qator",
        )

    def test_removes_control_characters(self):
        raw = "Matn\x07ichida"
        self.assertEqual(normalize_multiline_text(raw), "Matnichida")


class ClientCaptionDisplayTests(TestCase):
    def test_display_text_normalizes_dirty_db_value(self):
        client = Client.objects.create(name="Z-test", caption="temp")
        Client.objects.filter(pk=client.pk).update(
            caption="Samarqand 74\\r\\nMoykadan\\r\\nподъезд 2"
        )
        client.refresh_from_db()

        self.assertIn("\\r\\n", client.caption)
        self.assertEqual(
            client.get_caption_display_text(),
            "Samarqand 74\nMoykadan\nподъезд 2",
        )
