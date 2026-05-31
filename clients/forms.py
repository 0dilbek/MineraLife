# clients/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Client, ClientPhoneNumber


def _attrs(**kw):
    base = {
        "class": "w-full rounded-lg border border-gray-300 dark:border-gray-600 "
                 "bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 "
                 "px-4 py-2 outline-none focus:ring-2 focus:ring-blue-500"
    }
    base.update(kw)
    return base


class ClientPhoneNumberForm(forms.ModelForm):
    """Mijoz telefon raqami formasi"""
    
    class Meta:
        model = ClientPhoneNumber
        fields = ['phone_number', 'is_primary']
        widgets = {
            'phone_number': forms.TextInput(attrs=_attrs(placeholder="+998901234567")),
            'is_primary': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].label = "Telefon raqam"
        self.fields['is_primary'].label = "Asosiy raqam"


# Telefon raqamlar uchun inline formset
ClientPhoneNumberFormSet = inlineformset_factory(
    Client, 
    ClientPhoneNumber,
    form=ClientPhoneNumberForm,
    extra=1,  # 1 ta bo'sh form ko'rsatish
    can_delete=True,  # O'chirish imkoniyati
    min_num=1,  # Minimal 1 ta raqam kerak
    validate_min=True,  # Min validation yoqish
    max_num=10,  # Maksimal 10 ta raqam
)

class ClientForm(forms.ModelForm):
    # Bitta maydonda kiritish: "lat, lon"
    coordinates = forms.CharField(
        required=False,
        label="Koordinatalar (lat, lon)",
        widget=forms.TextInput(
            attrs=_attrs(placeholder="41.311081, 69.240562")
        ),
        help_text="Format: latitude, longitude (vergul bilan)",
    )

    class Meta:
        model = Client
        fields = ["name", "latitude", "longitude", "caption", "is_departed"]
        widgets = {
            "name": forms.TextInput(attrs=_attrs(placeholder="Ism Familiya")),
            # UI da bitta maydon orqali kiritiladi, shu sababli hidden qilib qo'yamiz
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "caption": forms.Textarea(attrs=_attrs(placeholder="Qo'shimcha ma'lumotlar")),
            "is_departed": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agar mavjud qiymatlar bo'lsa, coordinates maydonini to'ldirib qo'yamiz
        lat = self.initial.get("latitude") or (self.instance and getattr(self.instance, "latitude", None))
        lon = self.initial.get("longitude") or (self.instance and getattr(self.instance, "longitude", None))
        try:
            if lat is not None and lon is not None and self.fields.get("coordinates"):
                self.initial.setdefault("coordinates", f"{float(lat):.6f}, {float(lon):.6f}")
        except Exception:
            # agar floatga aylantirib bo'lmasa, shunchaki e'tiborsiz qoldiramiz
            pass

    def clean(self):
        data = super().clean()
        lat, lon = data.get("latitude"), data.get("longitude")
        coords = data.get("coordinates")

        # Agar coordinates maydoni to'ldirilgan bo'lsa, undan parslaymiz
        if coords:
            import re
            m = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$", coords)
            if not m:
                self.add_error("coordinates", "Koordinatalar formati: 41.311081, 69.240562 (vergul bilan ajratilgan)")
            else:
                try:
                    lat = float(m.group(1))
                    lon = float(m.group(2))
                    data["latitude"], data["longitude"] = lat, lon
                except ValueError:
                    self.add_error("coordinates", "Koordinatalarni raqam sifatida kiriting")

        # Agar bittasi kiritilsa, ikkinchisi ham bo‘lsin
        if (lat is None) ^ (lon is None):
            raise forms.ValidationError("Latitude va Longitude ikkalasi ham birga kiritilishi kerak (yoki ikkalasi ham bo‘sh).")

        # Diapazon tekshiruvi
        if lat is not None and not (-90 <= lat <= 90):
            self.add_error("coordinates", "Latitude -90 dan 90 gacha bo‘lishi kerak.")
        if lon is not None and not (-180 <= lon <= 180):
            self.add_error("coordinates", "Longitude -180 dan 180 gacha bo‘lishi kerak.")

        return data
