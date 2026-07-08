from django.db import models
from django.core.validators import RegexValidator

from common.text_utils import normalize_multiline_text


class ClientPhoneNumber(models.Model):
    """Mijoz telefon raqamlari"""
    
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='phone_numbers')
    phone_number = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9\s\-\(\)]{7,20}$',
                message="Telefon raqam noto'g'ri formatda. Masalan: +998901234567"
            )
        ],
        help_text="Mijoz telefon raqami"
    )
    is_primary = models.BooleanField(default=False, help_text="Asosiy telefon raqammi?")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
        verbose_name = "Mijoz telefon raqami"
        verbose_name_plural = "Mijoz telefon raqamlari"
    
    def __str__(self):
        primary_text = " (Asosiy)" if self.is_primary else ""
        return f"{self.phone_number}{primary_text}"
    
    def save(self, *args, **kwargs):
        # Agar bu telefon asosiy qilib belgilansa, boshqalarini asosiy emas qilish
        if self.is_primary:
            ClientPhoneNumber.objects.filter(
                client=self.client, 
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Client(models.Model):
    name = models.CharField(max_length=255, unique=True)
    longitude = models.FloatField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    is_departed = models.BooleanField(default=False, help_text="Mijoz endi bizdan buyurtma olmayaptimi?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.caption:
            self.caption = normalize_multiline_text(self.caption)
        super().save(*args, **kwargs)

    def get_caption_display_text(self):
        return normalize_multiline_text(self.caption) or ""

    def get_all_phone_numbers(self):
        """Barcha telefon raqamlarni olish"""
        primary_phones = self.phone_numbers.filter(is_primary=True)
        other_phones = self.phone_numbers.filter(is_primary=False)
        return list(primary_phones) + list(other_phones)
    
    def get_phone_numbers_display(self):
        """Telefon raqamlarni ko'rsatish uchun string"""
        phones = self.get_all_phone_numbers()
        if not phones:
            return "Telefon raqam yo'q"
        
        result = []
        for phone in phones:
            text = phone.phone_number
            if phone.is_primary:
                text += " (Asosiy)"
            result.append(text)
        
        return " | ".join(result)
    
    def get_primary_phone(self):
        """Asosiy telefon raqamni olish"""
        primary = self.phone_numbers.filter(is_primary=True).first()
        if primary:
            return primary.phone_number
        # Agar asosiy yo'q bo'lsa, birinchi telefon raqamini qaytarish
        first_phone = self.phone_numbers.first()
        return first_phone.phone_number if first_phone else None

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['name'], name='unique_client_name')
        ]
        
