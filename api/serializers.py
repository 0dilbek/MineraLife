from rest_framework import serializers
from clients.models import Client, ClientPhoneNumber

from orders.models import Order


class ClientPhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientPhoneNumber
        fields = ['phone_number', 'is_primary']


class ClientSerializer(serializers.ModelSerializer):
    phone_numbers = ClientPhoneNumberSerializer(many=True, read_only=True)
    caption = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 
            'name', 
            'phone_numbers', 
            'caption', 
            'latitude', 
            'longitude'
        ]

    def get_caption(self, obj):
        return obj.get_caption_display_text()


class OrderSerializer(serializers.ModelSerializer):
    notes = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_summary = serializers.CharField(source='get_payment_summary', read_only=True)
    total_price = serializers.DecimalField(
        source='get_total_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    total_paid = serializers.DecimalField(
        source='get_total_paid',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    courier_name = serializers.CharField(source='courier.username', read_only=True, allow_null=True)

    def get_notes(self, obj):
        return obj.get_notes_display_text()

    class Meta:
        model = Order
        fields = [
            'id',
            'inquantity',
            'outquantity',
            'price',
            'total_price',
            'cash_amount',
            'card_amount',
            'perechesleniya_amount',
            'debt_amount',
            'total_paid',
            'payment_summary',
            'status',
            'status_display',
            'effective_date',
            'notes',
            'courier_name',
            'created_at',
            'updated_at'
        ]
