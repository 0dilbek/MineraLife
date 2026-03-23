from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.timezone import localdate
from django.db.models import Q

from clients.models import Client
from orders.models import Order
from .serializers import ClientSerializer, OrderSerializer


@api_view(['GET'])
@permission_classes([AllowAny])  # Yoki IsAuthenticated ishlatishingiz mumkin
def get_client_orders(request):
    """
    Client nomini kiritib, client ma'lumotlari va bugungi orderlarni olish
    
    Query params:
        - name: Client nomi (kamida 2 ta belgi)
    
    Example: /api/orders/client/?name=Akmal
    """
    client_name = request.query_params.get('name', '').strip()
    
    if not client_name:
        return Response({
            'error': 'Client nomi kiritilishi shart',
            'message': 'Query parameter "name" ni kiriting'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if len(client_name) < 2:
        return Response({
            'error': 'Client nomi kamida 2 ta belgidan iborat bo\'lishi kerak'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Client qidirish (nom bo'yicha, case-insensitive, faqat to'liq moslik)
    clients = Client.objects.filter(
        Q(name__iexact=client_name)
    ).prefetch_related('phone_numbers')
    
    if not clients.exists():
        return Response({
            'error': 'Client topilmadi',
            'message': f'"{client_name}" nomli client topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Agar bir nechta client topilsa
    if clients.count() > 1:
        return Response({
            'message': 'Bir nechta client topildi',
            'clients': ClientSerializer(clients, many=True).data,
            'hint': 'Aniqroq nom kiriting yoki client ID sini ishlating'
        }, status=status.HTTP_200_OK)
    
    # Bitta client topildi
    client = clients.first()
    today = localdate()
    
    # Bugungi orderlar
    today_orders = Order.objects.filter(
        client=client,
        effective_date=today
    ).select_related('courier').order_by('-created_at')
    
    return Response({
        'client': ClientSerializer(client).data,
        'today_orders': OrderSerializer(today_orders, many=True).data,
        'date': today.isoformat()
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_client_orders_by_id(request, client_id):
    """
    Client ID orqali ma'lumotlar va bugungi orderlarni olish
    
    Example: /api/orders/client/123/
    """
    try:
        client = Client.objects.prefetch_related('phone_numbers').get(id=client_id)
    except Client.DoesNotExist:
        return Response({
            'error': 'Client topilmadi',
            'message': f'ID: {client_id} bo\'lgan client topilmadi'
        }, status=status.HTTP_404_NOT_FOUND)
    
    today = localdate()
    
    # Bugungi orderlar
    today_orders = Order.objects.filter(
        client=client,
        effective_date=today
    ).select_related('courier').order_by('-created_at')
    
    return Response({
        'client': ClientSerializer(client).data,
        'today_orders': OrderSerializer(today_orders, many=True).data,
        'date': today.isoformat()
    }, status=status.HTTP_200_OK)
