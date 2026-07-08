from decimal import Decimal

from django import forms


class EmptyZeroNumberInput(forms.NumberInput):
    def format_value(self, value):
        if value in (0, 0.0, "0", "0.0", "0.00", Decimal("0"), Decimal("0.0"), Decimal("0.00")):
            return ""
        return super().format_value(value)
