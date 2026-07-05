from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone

from common.text_utils import normalize_multiline_text


class Order(models.Model):
    client = models.ForeignKey('clients.Client', on_delete=models.CASCADE, related_name='orders')
    courier = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    inquantity = models.PositiveIntegerField(default=0)
    outquantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=18000.00, help_text="Bir dona uchun narx")
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

    def get_price_display(self):
        """Narxni ko'rsatish uchun"""
        if self.outquantity > 0:
            return f"{self.get_total_price():,.0f} so'm ({self.outquantity} x {self.price:,.0f})"
        return f"{self.price:,.0f} so'm"

    def get_notes_display_text(self):
        return normalize_multiline_text(self.notes) or ""

    def get_payment_summary(self):
        """To'lov turlari bo'yicha qisqa matn"""
        parts = []
        if self.cash_amount:
            parts.append(f"💵 {self.cash_amount:,.0f}")
        if self.card_amount:
            parts.append(f"💳 {self.card_amount:,.0f}")
        if self.perechesleniya_amount:
            parts.append(f"🏦 {self.perechesleniya_amount:,.0f}")
        if self.debt_amount:
            parts.append(f"📝 {self.debt_amount:,.0f}")
        return " | ".join(parts) if parts else "—"

    def save(self, *args, **kwargs):
        if self.notes:
            self.notes = normalize_multiline_text(self.notes)

        just_cancelled = False
        if self.pk and self.status == 'cancelled':
            previous_status = Order.objects.filter(pk=self.pk).values_list('status', flat=True).first()
            just_cancelled = previous_status != 'cancelled'

        super().save(*args, **kwargs)

        if just_cancelled:
            Order.objects.create(
                client=self.client,
                courier=self.courier,
                price=self.price,
                status='pending',
                effective_date=self.effective_date + timezone.timedelta(days=1),
                notes=self.notes,
            )
    

