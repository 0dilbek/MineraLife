from rest_framework import serializers
from clients.models import Client, ClientPhoneNumber
from orders.models import Order


class ClientPhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientPhoneNumber
        fields = ['phone_number', 'is_primary']


class ClientSerializer(serializers.ModelSerializer):
    phone_numbers = ClientPhoneNumberSerializer(many=True, read_only=True)
    
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


class OrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    total_price = serializers.DecimalField(
        source='get_total_price', 
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    courier_name = serializers.CharField(source='courier.username', read_only=True, allow_null=True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'inquantity',
            'outquantity',
            'price',
            'total_price',
            'status',
            'status_display',
            'payment_method',
            'payment_method_display',
            'effective_date',
            'notes',
            'courier_name',
            'created_at',
            'updated_at'
        ]
