#!/usr/bin/env python3
"""Ixtiyoriy: bazadagi caption va notes maydonlaridagi \\r\\n belgilarini tozalash.

Ko'rsatish qatlami (display_text, get_caption_display_text) allaqachon iflos
matnni to'g'ri chiqaradi. Bu skript faqat bazani bir martalik tozalash uchun.
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_panel.settings")
django.setup()

from clients.models import Client
from common.text_utils import normalize_multiline_text
from orders.models import Order


def main():
    client_updated = 0
    for client in Client.objects.exclude(caption__isnull=True).exclude(caption=""):
        cleaned = normalize_multiline_text(client.caption)
        if cleaned != client.caption:
            client.caption = cleaned
            client.save(update_fields=["caption", "updated_at"])
            client_updated += 1

    order_updated = 0
    for order in Order.objects.exclude(notes__isnull=True).exclude(notes=""):
        cleaned = normalize_multiline_text(order.notes)
        if cleaned != order.notes:
            order.notes = cleaned
            order.save(update_fields=["notes", "updated_at"])
            order_updated += 1

    print(f"Mijoz caption: {client_updated} ta yangilandi")
    print(f"Buyurtma notes: {order_updated} ta yangilandi")


if __name__ == "__main__":
    main()
    sys.exit(0)