from django.conf import settings
from django.db.models import Count, Sum


def site_config(request):
    debt_context = {
        "active_debtor_count": 0,
        "active_debt_order_count": 0,
        "active_debt_total": 0,
    }
    if request.user.is_authenticated:
        from orders.models import Order

        totals = Order.objects.filter(is_debt=True).aggregate(
            client_count=Count("client_id", distinct=True),
            order_count=Count("id"),
            total=Sum("debt_amount"),
        )
        debt_context = {
            "active_debtor_count": totals["client_count"] or 0,
            "active_debt_order_count": totals["order_count"] or 0,
            "active_debt_total": totals["total"] or 0,
        }

    return {
        "brand_name": settings.SITE_NAME,
        "reports_password": settings.REPORTS_PASSWORD,
        "admin_ui_mode": "classic",
        "ui_base_template": "base.html",
        **debt_context,
    }
