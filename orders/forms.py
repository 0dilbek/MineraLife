from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order
from clients.models import Client
from django.contrib.auth.models import User


def _attrs(**kw):
    base = {
        "class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 "
                 "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 "
                 "px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500"
    }
    base.update(kw); return base


class OrderForm(forms.ModelForm):
    """To'liq buyurtma formasi - barcha maydonlar bilan"""
    
    class Meta:
        model = Order
        fields = [
            "client", "courier", "inquantity", "outquantity", 
            "price", "status", "effective_date", "payment_method", "notes"
        ]
        widgets = {
            "client": forms.Select(attrs=_attrs()),
            "courier": forms.Select(attrs=_attrs()),
            "inquantity": forms.NumberInput(attrs=_attrs(min=0, placeholder="oldim")),
            "outquantity": forms.NumberInput(attrs=_attrs(min=0, placeholder="berdim")),
            "price": forms.NumberInput(attrs=_attrs(step="0.01", min=0, placeholder="18000")),
            "status": forms.Select(attrs=_attrs()),
            "effective_date": forms.DateInput(attrs=_attrs(type="date")),
            "payment_method": forms.Select(attrs=_attrs()),
            "notes": forms.Textarea(attrs=_attrs(rows=3, placeholder="Qo'shimcha izohlar...")),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Faqat telefon raqami bor mijozlarni ko'rsatish
        self.fields['client'].queryset = Client.objects.filter(
            phone_numbers__isnull=False
        ).distinct().order_by('name')
        
        # Faqat faol kurierlarni ko'rsatish
        self.fields['courier'].queryset = User.objects.filter(
            is_active=True, 
            groups__name='couriers'
        ).order_by('username')
        
        # Default sana - bugun
        if not self.instance.pk:  # Yangi buyurtma bo'lsa
            self.fields['effective_date'].initial = timezone.localdate()
            self.fields['price'].initial = 18000

        # Placeholder va help textlar
        self.fields['effective_date'].help_text = "Buyurtma bajarilish sanasi"
        self.fields['inquantity'].help_text = "oldim miqdori"
        self.fields['outquantity'].help_text = "berdim miqdori"
        
    def clean_effective_date(self):
        """Sana validatsiyasi"""
        date = self.cleaned_data.get('effective_date')
        if date:
            today = timezone.localdate()
            if date < today - timezone.timedelta(days=30):
                raise ValidationError("Sana juda eski (30 kundan ortiq)")
            if date > today + timezone.timedelta(days=365):
                raise ValidationError("Sana juda uzoq (1 yildan ortiq)")
        return date
        
    def clean_price(self):
        """Narx validatsiyasi"""
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise ValidationError("Narx 0 dan katta bo'lishi kerak")
        if price and price > 10000000:  # 10 million
            raise ValidationError("Narx juda katta (10 million so'mdan ko'p)")
        return price
        
    def clean(self):
        """Umumiy validatsiya"""
        cleaned_data = super().clean()
        inquantity = cleaned_data.get('inquantity', 0) or 0
        outquantity = cleaned_data.get('outquantity', 0) or 0
        
        # Debug uchun
        print(f"Form clean: inquantity={inquantity}, outquantity={outquantity}")
        
        # Miqdorlar hech bo'lmaganda 0 bo'lishi kerak (manfiy emas)
        if inquantity < 0:
            raise ValidationError("\"oldim\" manfiy bo'lmasligi kerak")
        if outquantity < 0:
            raise ValidationError("\"berdim\" manfiy bo'lmasligi kerak")
        
        # Ikkalasi ham 0 bo'lsa ogohlantiramiz, lekin bloklashmaymiz
        if inquantity == 0 and outquantity == 0:
            print("Warning: Ikkala miqdor ham 0")
            # ValidationError o'rniga faqat warning
        
        return cleaned_data


class SimpleOrderForm(forms.ModelForm):
    """Sodda buyurtma formasi - asosiy maydonlar bilan"""
    
    class Meta:
        model = Order
        fields = ["client", "courier", "price", "status", "effective_date", "payment_method", "notes"]
        widgets = {
            "client": forms.Select(attrs=_attrs()),
            "courier": forms.Select(attrs=_attrs()),
            "price": forms.NumberInput(attrs=_attrs(step="0.01", min=0)),
            "status": forms.Select(attrs=_attrs()),
            "effective_date": forms.DateInput(attrs=_attrs(type="date")),
            "payment_method": forms.Select(attrs=_attrs()),
            "notes": forms.Textarea(attrs=_attrs(rows=3)),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Faqat telefon raqami bor mijozlarni ko'rsatish
        self.fields['client'].queryset = Client.objects.filter(
            phone_numbers__isnull=False
        ).distinct().order_by('name')
        
        # Faqat faol kurierlarni ko'rsatish  
        self.fields['courier'].queryset = User.objects.filter(
            is_active=True,
            groups__name='couriers'
        ).order_by('username')
        
        # Default sana - bugun
        if not self.instance.pk:  # Yangi buyurtma bo'lsa
            self.fields['effective_date'].initial = timezone.localdate()
