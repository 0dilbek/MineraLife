from django.conf import settings


def site_config(request):
    return {
        "brand_name": settings.SITE_NAME,
        "reports_password": settings.REPORTS_PASSWORD,
    }
