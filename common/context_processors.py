from django.conf import settings


def site_config(request):
    admin_ui_mode = None
    if request.user.is_authenticated and request.user.is_superuser:
        admin_ui_mode = request.session.get("admin_ui_mode")

    return {
        "brand_name": settings.SITE_NAME,
        "reports_password": settings.REPORTS_PASSWORD,
        "admin_ui_mode": admin_ui_mode,
        "ui_base_template": (
            "base_modern.html" if admin_ui_mode == "modern" else "base.html"
        ),
    }
