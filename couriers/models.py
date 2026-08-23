from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class CourierRoute(models.Model):
    """Kuryerning kunlik marshrutini saqlash"""
    courier = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='routes',
        verbose_name="Kuryer"
    )
    date = models.DateField(verbose_name="Sana")
    route_data = models.JSONField(
        verbose_name="Marshrut ma'lumotlari",
        help_text="Marshrut koordinatalari va tartib",
        default=list
    )
    color = models.CharField(
        max_length=7,
        default="#2563eb",
        verbose_name="Marshrut rangi",
        help_text="Hex format: #RRGGBB"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kuryer marshruty"
        verbose_name_plural = "Kuryer marshrutlari"
        unique_together = ('courier', 'date')
        ordering = ['-date', 'courier__username']

    def __str__(self):
        return f"{self.courier.username} - {self.date}"


class CourierLocation(models.Model):
    """Kuryerning eng so'nggi jonli joylashuvi (har doim bitta yozuv, ustidan yoziladi)"""
    courier = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='live_location',
        verbose_name="Kuryer"
    )
    latitude = models.FloatField(verbose_name="Kenglik")
    longitude = models.FloatField(verbose_name="Uzunlik")
    accuracy = models.FloatField(null=True, blank=True, verbose_name="Aniqlik (metr)")
    altitude = models.FloatField(null=True, blank=True, verbose_name="Balandlik (metr)")
    speed = models.FloatField(null=True, blank=True, verbose_name="Tezlik (m/s)")
    bearing = models.FloatField(null=True, blank=True, verbose_name="Yo'nalish (gradus)")
    is_mocked = models.BooleanField(default=False, verbose_name="Soxta joylashuv")
    captured_at = models.DateTimeField(default=timezone.now, verbose_name="Qurilmada olingan vaqti")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqti")

    class Meta:
        verbose_name = "Kuryer joylashuvi"
        verbose_name_plural = "Kuryerlar joylashuvi"

    def __str__(self):
        return f"{self.courier.username} @ {self.latitude:.5f},{self.longitude:.5f}"
