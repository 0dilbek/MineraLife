from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

ICON_PATHS = {
    "cash": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/>'
    ),
    "card": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>'
    ),
    "perechesleniya": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>'
    ),
    "debt": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>'
    ),
    "chart": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>'
    ),
    "chart-line": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M7 12l3-3 3 3 4-8M3 20h18"/>'
    ),
    "wallet": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8V6m0 12v-2m9-4a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    ),
    "users": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>'
    ),
    "trophy": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M5 3h14M7 3v2a5 5 0 0010 0V3M5 3v1a5 5 0 005 5m0-5v1a5 5 0 005-5M9 21h6m-3-4v4"/>'
    ),
    "search": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>'
    ),
    "lock-open": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/>'
    ),
    "x-circle": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    ),
    "check-circle": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    ),
    "clock": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M12 8v4l3 2m6-2a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    ),
    "map-pin": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M12 21s7-4.35 7-11a7 7 0 10-14 0c0 6.65 7 11 7 11z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10h.01"/>'
    ),
    "phone": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>'
    ),
    "calendar": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>'
    ),
    "user": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>'
    ),
    "clipboard": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>'
    ),
    "pencil": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>'
    ),
    "save": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/>'
    ),
    "trash": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>'
    ),
    "check": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>'
    ),
    "x": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>'
    ),
    "truck": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M9 17a2 2 0 11-4 0 2 2 0 014 0zm10 0a2 2 0 11-4 0 2 2 0 014 0zM13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10l2 2h8l2-2zM13 16h4l2-2V9h-6"/>'
    ),
    "warning": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>'
    ),
    "route": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M9 20l-5-2.5V5l5 2.5M9 20l6-3m-6 3V7.5m6 9.5l5 2.5V7l-5-2.5m0 12.5V4.5M9 7.5l6-3"/>'
    ),
    "coins": (
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" '
        'd="M12 8c-2.21 0-4 .895-4 2s1.79 2 4 2 4 .895 4 2-1.79 2-4 2m0-10V6m0 12v-2"/>'
    ),
}

PAYMENT_ICON_KEYS = {
    "cash": "cash",
    "card": "card",
    "pereches": "perechesleniya",
    "perechesleniya": "perechesleniya",
    "debt": "debt",
}


@register.simple_tag
def icon(name, css_class="h-4 w-4"):
    path = ICON_PATHS.get(name)
    if not path:
        return ""
    return mark_safe(
        f'<svg class="{escape(css_class)} inline-block shrink-0" fill="none" '
        f'stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'
    )


@register.simple_tag
def payment_icon(payment_key, css_class="h-4 w-4"):
    icon_name = PAYMENT_ICON_KEYS.get(payment_key, "wallet")
    return icon(icon_name, css_class)