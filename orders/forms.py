from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order
from clients.models import Client
from django.contrib.auth.models import User
from common.widgets import EmptyZeroNumberInput


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
            "price", "status", "effective_date",
            "cash_amount", "card_amount", "perechesleniya_amount", "debt_amount",
            "notes"
        ]
        widgets = {
            "client": forms.Select(attrs=_attrs()),
            "courier": forms.Select(attrs=_attrs()),
            "inquantity": EmptyZeroNumberInput(attrs=_attrs(min=0, placeholder="oldim")),
            "outquantity": EmptyZeroNumberInput(attrs=_attrs(min=0, placeholder="berdim")),
            "price": forms.NumberInput(attrs=_attrs(step="1", min=0, placeholder="18000")),
            "status": forms.Select(attrs=_attrs()),
            "effective_date": forms.DateInput(attrs=_attrs(type="date")),
            "cash_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "card_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "perechesleniya_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "debt_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "notes": forms.Textarea(attrs=_attrs(rows=3, placeholder="Qo'shimcha izohlar...")),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(
            phone_numbers__isnull=False
        ).distinct().order_by('name')

        self.fields['courier'].queryset = User.objects.filter(
            is_active=True,
            groups__name='couriers'
        ).order_by('username')

        if not self.instance.pk:
            if "effective_date" not in self.initial:
                self.fields['effective_date'].initial = timezone.localdate()
            self.fields['price'].initial = 18000

        for field_name in ("inquantity", "outquantity", "cash_amount", "card_amount", "perechesleniya_amount", "debt_amount"):
            self.fields[field_name].required = False

        self.fields['effective_date'].help_text = "Buyurtma bajarilish sanasi"
        self.fields['inquantity'].help_text = "oldim miqdori"
        self.fields['outquantity'].help_text = "berdim miqdori"
        self.fields['cash_amount'].label = "💵 Naqd (so'm)"
        self.fields['card_amount'].label = "💳 Karta (so'm)"
        self.fields['perechesleniya_amount'].label = "🏦 Perechisleniya (so'm)"
        self.fields['debt_amount'].label = "📝 Qarz (so'm)"

    def clean_effective_date(self):
        date = self.cleaned_data.get('effective_date')
        if date:
            today = timezone.localdate()
            if date < today - timezone.timedelta(days=30):
                raise ValidationError("Sana juda eski (30 kundan ortiq)")
            if date > today + timezone.timedelta(days=365):
                raise ValidationError("Sana juda uzoq (1 yildan ortiq)")
        return date

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise ValidationError("Narx 0 dan katta bo'lishi kerak")
        if price and price > 10000000:
            raise ValidationError("Narx juda katta (10 million so'mdan ko'p)")
        return price

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("inquantity", "outquantity", "cash_amount", "card_amount", "perechesleniya_amount", "debt_amount"):
            if cleaned_data.get(field_name) in (None, ""):
                cleaned_data[field_name] = 0
        inquantity = cleaned_data.get('inquantity', 0) or 0
        outquantity = cleaned_data.get('outquantity', 0) or 0
        if inquantity < 0:
            raise ValidationError('"oldim" manfiy bo\'lmasligi kerak')
        if outquantity < 0:
            raise ValidationError('"berdim" manfiy bo\'lmasligi kerak')
        return cleaned_data


class SimpleOrderForm(forms.ModelForm):
    """Sodda buyurtma formasi - asosiy maydonlar bilan"""

    class Meta:
        model = Order
        fields = [
            "client", "courier", "price", "status", "effective_date",
            "cash_amount", "card_amount", "perechesleniya_amount", "debt_amount",
            "notes"
        ]
        widgets = {
            "client": forms.Select(attrs=_attrs()),
            "courier": forms.Select(attrs=_attrs()),
            "price": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0)),
            "status": forms.Select(attrs=_attrs()),
            "effective_date": forms.DateInput(attrs=_attrs(type="date")),
            "cash_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "card_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "perechesleniya_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "debt_amount": EmptyZeroNumberInput(attrs=_attrs(step="1", min=0, placeholder="0")),
            "notes": forms.Textarea(attrs=_attrs(rows=3)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(
            phone_numbers__isnull=False
        ).distinct().order_by('name')

        self.fields['courier'].queryset = User.objects.filter(
            is_active=True,
            groups__name='couriers'
        ).order_by('username')

        if not self.instance.pk and "effective_date" not in self.initial:
            self.fields['effective_date'].initial = timezone.localdate()

        for field_name in ("cash_amount", "card_amount", "perechesleniya_amount", "debt_amount"):
            self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ("cash_amount", "card_amount", "perechesleniya_amount", "debt_amount"):
            if cleaned_data.get(field_name) in (None, ""):
                cleaned_data[field_name] = 0
        return cleaned_data
