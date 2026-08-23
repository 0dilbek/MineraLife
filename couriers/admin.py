from django.contrib import admin
from django import forms
from .models import CourierRoute, CourierLocation


# Rang tanlovlari
COLOR_CHOICES = [
    ('#2563eb', '🔵 Ko\'k (Standart)'),
    ('#dc2626', '🔴 Qizil'),
    ('#16a34a', '🟢 Yashil'),
    ('#ca8a04', '🟡 Sariq'),
    ('#9333ea', '🟣 Binafsha'),
    ('#ea580c', '🟠 To\'q sariq'),
    ('#0891b2', '🔵 Moviy'),
    ('#e11d48', '🌸 Pushti'),
]


class CourierRouteAdminForm(forms.ModelForm):
    """Rang tanlash uchun maxsus form"""
    
    class Meta:
        model = CourierRoute
        fields = '__all__'
        widgets = {
            'color': forms.Select(choices=COLOR_CHOICES, attrs={
                'style': 'width: 250px; font-size: 14px;'
            }),
            'route_data': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Marshrut koordinatalari JSON formatda: [[lat1, lon1], [lat2, lon2], ...]',
                'class': 'vLargeTextField',
                'style': 'font-family: monospace;'
            }),
        }
        labels = {
            'color': 'Marshrut rangi',
            'route_data': 'Marshrut koordinatalari',
        }
        help_texts = {
            'color': 'Xaritada ko\'rsatiladigan marshrut chizig\'ining rangi',
            'route_data': 'JSON format: [[41.2995, 69.2401], [41.3111, 69.2797], ...]',
        }


@admin.register(CourierRoute)
class CourierRouteAdmin(admin.ModelAdmin):
    form = CourierRouteAdminForm
    list_display = ('courier', 'date', 'color_badge', 'route_points_count', 'created_at')
    list_filter = ('date', 'courier')
    search_fields = ('courier__username', 'courier__first_name', 'courier__last_name')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('courier', 'date', 'color')
        }),
        ('Marshrut', {
            'fields': ('route_data',),
            'description': 'Marshrut koordinatalarini JSON formatda kiriting. Har bir nuqta [latitude, longitude] formatida bo\'lishi kerak.'
        }),
        ('Qo\'shimcha ma\'lumotlar', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_badge(self, obj):
        """Rangni badge ko'rinishida ko'rsatish"""
        from django.utils.html import format_html
        # Rang nomini topish
        color_name = dict(COLOR_CHOICES).get(obj.color, 'Boshqa')
        return format_html(
            '<span style="display: inline-flex; align-items: center; gap: 8px;">'
            '<span style="width: 40px; height: 24px; background-color: {}; border: 2px solid #ddd; border-radius: 4px; display: inline-block;"></span>'
            '<span style="font-size: 13px;">{}</span>'
            '</span>',
            obj.color,
            color_name
        )
    color_badge.short_description = 'Rang'
    
    def route_points_count(self, obj):
        """Marshrut nuqtalari soni"""
        if obj.route_data and isinstance(obj.route_data, list):
            return f'{len(obj.route_data)} nuqta'
        return '—'
    route_points_count.short_description = 'Nuqtalar'


@admin.register(CourierLocation)
class CourierLocationAdmin(admin.ModelAdmin):
    list_display = ('courier', 'latitude', 'longitude', 'accuracy', 'speed', 'is_mocked', 'captured_at', 'updated_at')
    list_filter = ('courier', 'is_mocked')
    search_fields = ('courier__username',)
    readonly_fields = ('captured_at', 'updated_at')
