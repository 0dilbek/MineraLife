from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "courier", "inquantity", "outquantity", "effective_date", "status", "get_payment_summary", "get_unit_price", "get_total_price_admin", "created_at")
    list_filter = ("status", "effective_date", "courier")
    search_fields = ("client__name", "courier__username", "notes")
    
    # Yangi buyurtma qo'shishda courier so'ralmasin
    exclude = []
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Yangi buyurtma qo'shishda courier maydonini ixtiyoriy qilish
        if 'courier' in form.base_fields:
            form.base_fields['courier'].required = False
        return form
    
    def get_payment_summary(self, obj):
        return obj.get_payment_summary()
    get_payment_summary.short_description = "To'lov"

    def get_unit_price(self, obj):
        return f"{obj.price:,.0f} so'm"
    get_unit_price.short_description = "Birlik narx"
    
    def get_total_price_admin(self, obj):
        return f"{obj.get_total_price():,.0f} so'm"
    get_total_price_admin.short_description = "Umumiy narx"
