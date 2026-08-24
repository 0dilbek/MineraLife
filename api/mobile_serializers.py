from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from clients.models import Client
from couriers.models import CourierLocation, CourierRoute
from orders.models import Order


class MobileClientSerializer(serializers.ModelSerializer):
    phone_numbers = serializers.SerializerMethodField()
    primary_phone = serializers.SerializerMethodField()
    caption = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            'id', 'name', 'phone_numbers', 'primary_phone', 'caption',
            'latitude', 'longitude',
        )

    def get_phone_numbers(self, obj):
        return [
            {
                'number': phone.phone_number,
                'is_primary': phone.is_primary,
            }
            for phone in obj.get_all_phone_numbers()
        ]

    def get_primary_phone(self, obj):
        return obj.get_primary_phone()

    def get_caption(self, obj):
        return obj.get_caption_display_text()


class MobileOrderSerializer(serializers.ModelSerializer):
    client = MobileClientSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_price = serializers.DecimalField(
        source='get_total_price', max_digits=14, decimal_places=2, read_only=True
    )
    total_paid = serializers.DecimalField(
        source='get_total_paid', max_digits=14, decimal_places=2, read_only=True
    )
    payment_summary = serializers.CharField(source='get_payment_summary', read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id', 'client', 'inquantity', 'outquantity', 'price',
            'total_price', 'cash_amount', 'card_amount',
            'perechesleniya_amount', 'debt_amount', 'total_paid',
            'payment_summary', 'status', 'status_display', 'is_debt',
            'debt_marked_at', 'effective_date',
            'notes', 'can_edit', 'created_at', 'updated_at',
        )

    def get_can_edit(self, obj):
        return obj.effective_date == timezone.localdate() and not obj.is_debt


class MobileOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            'inquantity', 'outquantity', 'cash_amount', 'card_amount',
            'perechesleniya_amount', 'debt_amount', 'status', 'notes',
        )
        extra_kwargs = {
            'inquantity': {'min_value': 0},
            'outquantity': {'min_value': 0},
            'cash_amount': {'min_value': Decimal('0')},
            'card_amount': {'min_value': Decimal('0')},
            'perechesleniya_amount': {'min_value': Decimal('0')},
            'debt_amount': {'min_value': Decimal('0')},
        }

    def validate(self, attrs):
        status_value = attrs.get('status', self.instance.status)
        inquantity = attrs.get('inquantity', self.instance.inquantity)
        outquantity = attrs.get('outquantity', self.instance.outquantity)
        if status_value == 'completed' and inquantity == 0 and outquantity == 0:
            raise serializers.ValidationError(
                "Bajarilgan buyurtmada 'oldim' yoki 'berdim' 0 dan katta bo'lishi kerak."
            )
        return attrs


class MobileLocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    accuracy = serializers.FloatField(required=False, allow_null=True, min_value=0)
    altitude = serializers.FloatField(required=False, allow_null=True)
    speed = serializers.FloatField(required=False, allow_null=True, min_value=0)
    bearing = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=360)
    is_mocked = serializers.BooleanField(required=False, default=False)
    captured_at = serializers.DateTimeField(required=False, default=timezone.now)

    def validate_captured_at(self, value):
        if value > timezone.now() + timezone.timedelta(minutes=5):
            raise serializers.ValidationError("Joylashuv vaqti kelajakda bo'lishi mumkin emas.")
        return value


class MobileLocationStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourierLocation
        fields = (
            'latitude', 'longitude', 'accuracy', 'altitude', 'speed',
            'bearing', 'is_mocked', 'captured_at', 'updated_at',
        )


class MobileRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourierRoute
        fields = ('date', 'route_data', 'color', 'updated_at')


class MobileLoginSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
