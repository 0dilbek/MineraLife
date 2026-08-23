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


class AdminInterfaceChoiceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="ui-admin",
            email="ui@example.com",
            password="password",
        )
        self.client.force_login(self.admin)

    def test_new_admin_session_opens_interface_choice(self):
        response = self.client.get(reverse("admin_welcome"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_ui_choice.html")

    def test_classic_choice_keeps_existing_dashboard(self):
        response = self.client.post(reverse("set_admin_ui"), {"mode": "classic"})

        self.assertRedirects(response, reverse("admin_welcome"))
        dashboard = self.client.get(reverse("admin_welcome"))
        self.assertTemplateUsed(dashboard, "admin_welcome.html")
        self.assertEqual(self.client.session["admin_ui_mode"], "classic")

    def test_modern_choice_uses_modern_dashboard_and_base(self):
        self.client.post(reverse("set_admin_ui"), {"mode": "modern"})

        dashboard = self.client.get(reverse("admin_welcome"))
        self.assertTemplateUsed(dashboard, "admin_welcome_modern.html")
        self.assertEqual(dashboard.context["ui_base_template"], "base_modern.html")

    def test_invalid_choice_is_rejected(self):
        response = self.client.post(reverse("set_admin_ui"), {"mode": "unknown"})

        self.assertEqual(response.status_code, 400)

    def test_main_admin_sections_follow_selected_interface(self):
        section_urls = (
            reverse("orders:list"),
            reverse("clients:list"),
            reverse("products:list"),
            reverse("couriers:list"),
            reverse("hisobotlar:reports"),
        )

        for mode, expected_base in (("classic", "base.html"), ("modern", "base_modern.html")):
            self.client.post(reverse("set_admin_ui"), {"mode": mode})
            for url in section_urls:
                with self.subTest(mode=mode, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, expected_base)

    def test_modern_interface_loads_shared_component_layer(self):
        self.client.post(reverse("set_admin_ui"), {"mode": "modern"})

        response = self.client.get(reverse("clients:list"))

        self.assertContains(response, 'id="modern-component-compatibility"')
        self.assertContains(response, "--panel-soft:")


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
