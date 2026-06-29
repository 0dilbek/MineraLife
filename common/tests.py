from django.test import TestCase

from clients.models import Client
from common.text_utils import normalize_multiline_text


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