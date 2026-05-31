from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from orders.models import Order

COURIER_GROUP_NAME = "couriers"

def _tw(**kw):
    base = {
        "class": "w-full rounded-lg border-2 border-gray-300 dark:border-gray-600 "
                 "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 "
                 "px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 "
                 "transition-colors duration-200 placeholder-gray-400 dark:placeholder-gray-500"
    }
    base.update(kw)
    return base


class CourierQuickCompleteForm(forms.ModelForm):
    """Tez bajarish formasi - oldim, berdim miqdorlar va izoh"""

    class Meta:
        model = Order
        fields = ["inquantity", "outquantity", "notes"]
        widgets = {
            "inquantity": forms.NumberInput(attrs=_tw(min=0, placeholder="oldim")),
            "outquantity": forms.NumberInput(attrs=_tw(min=0, placeholder="berdim", **{"data-price": "true"})),
            "notes": forms.Textarea(attrs=_tw(rows=2, placeholder="Qo'shimcha izohlar (ixtiyoriy)...")),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['inquantity'].label = "Oldim"
        self.fields['outquantity'].label = "Berdim"
        self.fields['notes'].label = "Izohlar"

        self.fields['inquantity'].help_text = "Mijozga yetkazilgan mahsulot miqdori"
        self.fields['outquantity'].help_text = "Mijozdan olingan mahsulot miqdori"
        self.fields['outquantity'].required = True

    def clean(self):
        cleaned_data = super().clean()
        inquantity = cleaned_data.get('inquantity', 0) or 0
        outquantity = cleaned_data.get('outquantity', 0) or 0

        if inquantity == 0 and outquantity == 0:
            raise ValidationError(
                "Hech bo'lmaganda kiruvchi yoki chiquvchi miqdor 0 dan katta bo'lishi kerak"
            )
        if inquantity < 0:
            raise ValidationError("Kiruvchi miqdor manfiy bo'lmasligi kerak")
        if outquantity < 0:
            raise ValidationError("Chiquvchi miqdor manfiy bo'lmasligi kerak")
        return cleaned_data


class CourierOrderUpdateForm(forms.ModelForm):
    """Kurer uchun buyurtma tahrirlash formasi - holat, to'lov summalar, miqdor"""

    class Meta:
        model = Order
        fields = [
            "inquantity", "outquantity", "status",
            "cash_amount", "card_amount", "perechesleniya_amount", "debt_amount",
            "notes"
        ]
        widgets = {
            "inquantity": forms.NumberInput(attrs=_tw(min=0, placeholder="oldim")),
            "outquantity": forms.NumberInput(attrs=_tw(min=0, placeholder="berdim")),
            "status": forms.Select(attrs=_tw()),
            "cash_amount": forms.NumberInput(attrs=_tw(step="1", min=0, placeholder="0")),
            "card_amount": forms.NumberInput(attrs=_tw(step="1", min=0, placeholder="0")),
            "perechesleniya_amount": forms.NumberInput(attrs=_tw(step="1", min=0, placeholder="0")),
            "debt_amount": forms.NumberInput(attrs=_tw(step="1", min=0, placeholder="0")),
            "notes": forms.Textarea(attrs=_tw(rows=3, placeholder="Qo'shimcha izohlar...")),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['status'].choices = [
            ('pending', 'Kutilmoqda'),
            ('completed', 'Bajardi'),
            ('cancelled', 'Bekor qilingan'),
        ]

        self.fields['inquantity'].label = "Oldim"
        self.fields['outquantity'].label = "Berdim"
        self.fields['status'].label = "Buyurtma holati"
        self.fields['cash_amount'].label = "Naqd (so'm)"
        self.fields['card_amount'].label = "Karta (so'm)"
        self.fields['perechesleniya_amount'].label = "Perechisleniya (so'm)"
        self.fields['debt_amount'].label = "Qarz (so'm)"
        self.fields['notes'].label = "Izohlar"

    def clean(self):
        cleaned_data = super().clean()
        inquantity = cleaned_data.get('inquantity', 0)
        outquantity = cleaned_data.get('outquantity', 0)

        if inquantity == 0 and outquantity == 0:
            raise ValidationError(
                "Hech bo'lmaganda oldim yoki berdim miqdor 0 dan katta bo'lishi kerak"
            )
        if inquantity < 0:
            raise ValidationError("Oldim miqdor manfiy bo'lmasligi kerak")
        if outquantity < 0:
            raise ValidationError("Berdim miqdor manfiy bo'lmasligi kerak")
        return cleaned_data


class CourierUserCreateForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs=_tw(placeholder="damas1")))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=_tw(placeholder="parol")))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=_tw(placeholder="parolni tasdiqlang")))
    is_active = forms.BooleanField(initial=True, required=False, label="Faol (login ishlasin)")

    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username=u).exists():
            raise ValidationError("Bu login band.")
        return u

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Parollar mos emas.")
        return data

    def save(self):
        data = self.cleaned_data
        user = User(username=data["username"], is_active=data.get("is_active", True))
        user.set_password(data["password1"])
        user.save()

        group, _ = Group.objects.get_or_create(name=COURIER_GROUP_NAME)
        user.groups.add(group)
        return user


class CourierUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["is_active"]
        widgets = {
            "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded"})
        }


class CourierUserPasswordForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=_tw(placeholder="yangi parol")))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=_tw(placeholder="tasdiqlash")))

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            raise ValidationError("Parollar mos emas.")
        return data
