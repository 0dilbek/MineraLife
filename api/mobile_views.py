from datetime import datetime
from decimal import Decimal

from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from couriers.models import CourierLocation, CourierRoute
from orders.models import Order

from .mobile_serializers import (
    MobileLocationSerializer,
    MobileLocationStateSerializer,
    MobileLoginSerializer,
    MobileOrderSerializer,
    MobileOrderUpdateSerializer,
    MobileRouteSerializer,
)


COURIER_GROUP_NAME = 'couriers'


def _is_courier(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (user.is_superuser or user.groups.filter(name=COURIER_GROUP_NAME).exists())
    )


class IsActiveCourier(BasePermission):
    message = "Mobil ilovaga faqat faol kuryer kira oladi."

    def has_permission(self, request, view):
        return _is_courier(request.user)


class CourierAPIView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated, IsActiveCourier)


def _profile(user):
    display_name = user.get_full_name().strip() or user.username
    return {
        'id': user.id,
        'username': user.username,
        'display_name': display_name,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def _selected_date(request):
    raw_date = request.query_params.get('date')
    if not raw_date:
        return timezone.localdate()
    try:
        return datetime.strptime(raw_date, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValidationError({'date': 'Sana YYYY-MM-DD formatida bo\'lishi kerak.'}) from exc


def _orders_for(user, selected_date):
    return (
        Order.objects
        .select_related('client', 'courier')
        .prefetch_related('client__phone_numbers')
        .filter(courier=user, effective_date=selected_date)
        .order_by('status', '-created_at')
    )


def _decimal_string(value):
    return str(value or Decimal('0'))


def _summary(queryset):
    values = queryset.aggregate(
        pending_count=Count('id', filter=Q(status='pending')),
        completed_count=Count('id', filter=Q(status='completed')),
        cancelled_count=Count('id', filter=Q(status='cancelled')),
        cash_total=Sum('cash_amount', filter=Q(status='completed')),
        card_total=Sum('card_amount', filter=Q(status='completed')),
        transfer_total=Sum('perechesleniya_amount', filter=Q(status='completed')),
        debt_total=Sum('debt_amount', filter=Q(status='completed')),
        delivered_total=Sum('outquantity', filter=Q(status='completed')),
        received_total=Sum('inquantity'),
        planned_total=Sum('outquantity', filter=~Q(status='cancelled')),
    )
    cash = values['cash_total'] or Decimal('0')
    card = values['card_total'] or Decimal('0')
    transfer = values['transfer_total'] or Decimal('0')
    return {
        'pending_count': values['pending_count'],
        'completed_count': values['completed_count'],
        'cancelled_count': values['cancelled_count'],
        'cash_total': _decimal_string(cash),
        'card_total': _decimal_string(card),
        'transfer_total': _decimal_string(transfer),
        'debt_total': _decimal_string(values['debt_total']),
        'paid_total': _decimal_string(cash + card + transfer),
        'delivered_total': values['delivered_total'] or 0,
        'received_total': values['received_total'] or 0,
        'planned_total': values['planned_total'] or 0,
    }


class MobileLoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = MobileLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if not user or not _is_courier(user):
            return Response(
                {'detail': "Login yoki parol noto'g'ri, yoxud foydalanuvchi kuryer emas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response({'token': token.key, 'user': _profile(user)})


class MobileLogoutView(CourierAPIView):
    def post(self, request):
        if request.auth:
            request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileMeView(CourierAPIView):
    def get(self, request):
        location = getattr(request.user, 'live_location', None)
        return Response({
            'user': _profile(request.user),
            'location': (
                MobileLocationStateSerializer(location).data if location else None
            ),
        })


class MobileDashboardView(CourierAPIView):
    def get(self, request):
        selected_date = _selected_date(request)
        queryset = _orders_for(request.user, selected_date)
        route = CourierRoute.objects.filter(
            courier=request.user, date=selected_date
        ).first()
        return Response({
            'date': selected_date.isoformat(),
            'can_edit': selected_date == timezone.localdate(),
            'summary': _summary(queryset),
            'orders': MobileOrderSerializer(queryset, many=True).data,
            'route': MobileRouteSerializer(route).data if route else None,
        })


class MobileOrderListView(CourierAPIView):
    def get(self, request):
        selected_date = _selected_date(request)
        queryset = _orders_for(request.user, selected_date)
        status_filter = request.query_params.get('status')
        if status_filter:
            valid_statuses = {choice[0] for choice in Order._meta.get_field('status').choices}
            if status_filter not in valid_statuses:
                raise ValidationError({'status': "Noto'g'ri buyurtma holati."})
            queryset = queryset.filter(status=status_filter)
        return Response({
            'date': selected_date.isoformat(),
            'results': MobileOrderSerializer(queryset, many=True).data,
        })


class MobileOrderDetailView(CourierAPIView):
    def get_object(self, request, order_id):
        queryset = (
            Order.objects
            .select_related('client', 'courier')
            .prefetch_related('client__phone_numbers')
            .filter(courier=request.user)
        )
        return get_object_or_404(queryset, pk=order_id)

    def get(self, request, order_id):
        return Response(MobileOrderSerializer(self.get_object(request, order_id)).data)

    @transaction.atomic
    def patch(self, request, order_id):
        order = self.get_object(request, order_id)
        if order.effective_date != timezone.localdate():
            return Response(
                {'detail': "Faqat bugungi buyurtmani o'zgartirish mumkin."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = MobileOrderUpdateSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        order.refresh_from_db()
        return Response(MobileOrderSerializer(order).data)


class MobileLocationView(CourierAPIView):
    def get(self, request):
        location = CourierLocation.objects.filter(courier=request.user).first()
        if not location:
            return Response({'location': None})
        return Response({'location': MobileLocationStateSerializer(location).data})

    @transaction.atomic
    def post(self, request):
        serializer = MobileLocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        current = CourierLocation.objects.select_for_update().filter(
            courier=request.user
        ).first()
        if current and payload['captured_at'] < current.captured_at:
            return Response({
                'accepted': False,
                'reason': 'stale_location',
                'location': MobileLocationStateSerializer(current).data,
            })

        location, _ = CourierLocation.objects.update_or_create(
            courier=request.user,
            defaults=payload,
        )
        return Response({
            'accepted': True,
            'location': MobileLocationStateSerializer(location).data,
        })
