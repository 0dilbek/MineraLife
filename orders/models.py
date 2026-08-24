from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.text_utils import normalize_multiline_text


class Order(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='orders')
    courier = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    inquantity = models.PositiveIntegerField(default=0)
    outquantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=19000.00, help_text="Bir dona uchun narx")
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Kutilmoqda'),
        ('completed', 'Bajardi'),
        ('cancelled', 'Bekor qilingan'),
    ], default='pending')
    effective_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    # To'lov turlari bo'yicha alohida summalar
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Naqd to'lov summasi")
    card_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Karta to'lov summasi")
    perechesleniya_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Perechisleniya summasi")
    debt_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Qarz summasi")
    is_debt = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Buyurtma yopilmagan qarz sifatida belgilanganmi?",
    )
    debt_marked_at = models.DateTimeField(null=True, blank=True)
    debt_marked_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_debt_orders',
    )
    debt_closed_at = models.DateTimeField(null=True, blank=True)
    debt_closed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='closed_debt_orders',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        indexes = [
            models.Index(fields=['effective_date', 'status'], name='order_date_status_idx'),
            models.Index(fields=['client', 'effective_date'], name='order_client_date_idx'),
            models.Index(fields=['courier', 'effective_date'], name='order_courier_date_idx'),
            models.Index(fields=['-created_at'], name='order_created_idx'),
        ]

    def __str__(self):
        return f"#{self.id} - {self.client.name} ({self.get_status_display()})"

    def get_total_price(self):
        """Umumiy narx: berdim miqdor * birlik narx"""
        return self.outquantity * self.price

    def get_total_paid(self):
        """Jami to'langan summa"""
        return self.cash_amount + self.card_amount + self.perechesleniya_amount + self.debt_amount

    def get_outstanding_amount(self):
        """Naqd/karta/o'tkazmadan keyin qolgan to'lanmagan summa."""
        paid = self.cash_amount + self.card_amount + self.perechesleniya_amount
        return max(self.get_total_price() - paid, 0)

    def mark_as_debt(self, user):
        """Kutilayotgan yoki bajarilgan buyurtmani faol qarzga belgilaydi."""
        if self.is_debt:
            raise ValidationError("Bu buyurtma allaqachon faol qarz sifatida belgilangan.")
        if self.status not in {'pending', 'completed'}:
            raise ValidationError(
                "Faqat kutilayotgan yoki bajarilgan buyurtmani qarzga belgilash mumkin."
            )
        outstanding_amount = self.get_outstanding_amount()
        if outstanding_amount <= 0:
            raise ValidationError(
                "Qarz summasi 0. Avval berilgan miqdor va to'lov summalarini tekshiring."
            )
        self.status = 'completed'
        self.is_debt = True
        self.debt_amount = outstanding_amount
        self.debt_marked_at = timezone.now()
        self.debt_marked_by = user
        self.debt_closed_at = None
        self.debt_closed_by = None
        self.save(update_fields=[
            'status', 'is_debt', 'debt_amount', 'debt_marked_at',
            'debt_marked_by', 'debt_closed_at', 'debt_closed_by', 'updated_at',
        ])

    def close_debt(self, user):
        """Faol qarzni yopadi; moliyaviy tarix uchun qarz summasini saqlaydi."""
        if not self.is_debt:
            raise ValidationError("Bu buyurtmada faol qarz yo'q.")
        self.is_debt = False
        self.debt_closed_at = timezone.now()
        self.debt_closed_by = user
        self.save(update_fields=['is_debt', 'debt_closed_at', 'debt_closed_by', 'updated_at'])

    def get_price_display(self):
        """Narxni ko'rsatish uchun"""
        if self.outquantity > 0:
            return f"{self.get_total_price():,.0f} so'm ({self.outquantity} x {self.price:,.0f})"
        return f"{self.price:,.0f} so'm"

    def get_notes_display_text(self):
        return normalize_multiline_text(self.notes) or ""

    def get_payment_breakdown(self):
        """Faqat 0 dan katta to'lov summalari."""
        mapping = (
            ("cash", "Naqd", self.cash_amount),
            ("card", "Karta", self.card_amount),
            ("perechesleniya", "Perechisleniya", self.perechesleniya_amount),
            ("debt", "Qarz", self.debt_amount),
        )
        return [
            {"key": key, "label": label, "amount": amount}
            for key, label, amount in mapping
            if amount
        ]

    def get_payment_summary(self):
        """To'lov turlari bo'yicha qisqa matn"""
        parts = [
            f"{item['label']}: {item['amount']:,.0f}"
            for item in self.get_payment_breakdown()
        ]
        return " · ".join(parts) if parts else "—"

    def _schedule_pending_copy_for_next_day(self):
        """Bekor qilingan buyurtmani ertaga yangi 'kutilmoqda' buyurtma sifatida qo'shadi."""
        next_date = self.effective_date + timezone.timedelta(days=1)
        clean_fields = {
            "courier": self.courier,
            "price": self.price,
            "inquantity": self.inquantity,
            "outquantity": self.outquantity,
            "cash_amount": 0,
            "card_amount": 0,
            "perechesleniya_amount": 0,
            "debt_amount": 0,
            "notes": self.notes or "",
        }

        existing = Order.objects.filter(
            client=self.client,
            effective_date=next_date,
            status="pending",
        ).order_by("pk").first()

        if existing:
            for field, value in clean_fields.items():
                setattr(existing, field, value)
            existing.save(update_fields=[*clean_fields.keys(), "updated_at"])
            return existing

        return Order.objects.create(
            client=self.client,
            status="pending",
            effective_date=next_date,
            **clean_fields,
        )

    def save(self, *args, **kwargs):
        if self.notes:
            self.notes = normalize_multiline_text(self.notes)

        just_cancelled = False
        if self.pk and self.status == 'cancelled':
            previous_status = Order.objects.filter(pk=self.pk).values_list('status', flat=True).first()
            just_cancelled = previous_status != 'cancelled'

        super().save(*args, **kwargs)

        if just_cancelled:
            self._schedule_pending_copy_for_next_day()
    
