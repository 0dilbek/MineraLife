from django.views.generic import ListView, CreateView, DetailView, TemplateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Prefetch, Sum
from .models import Order
from .forms import OrderForm
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta
from datetime import datetime, timedelta
from django.utils import timezone
from couriers.models import CourierRoute
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView
from django.contrib.auth.models import User, Group
from admin_panel.mixins import SuperuserRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
import json
from django.conf import settings

class OrderListView(SuperuserRequiredMixin, ListView):
    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 12
    ordering = "-created_at"

    # --- Sana parsing: bir nechta formatni qo‘llab-quvvatlaydi ---
    def _parse_date_safe(self, s: str | None):
        """
        YYYY-MM-DD (standart), MM/DD/YYYY yoki DD/MM/YYYY ko‘rinishlarini qabul qiladi.
        Brauzer/locale turlicha yuborganda ham ishlashi uchun.
        """
        if not s:
            return None
        # 1) standart (YYYY-MM-DD)
        d = parse_date(s)
        if d:
            return d
        # 2) muqobil formatlar
        for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    # --- GET dan oraliqni aniqlash + preset ---
    def _get_date_range(self):
        today = timezone.localdate()
        preset = (self.request.GET.get("preset") or "").lower()

        # Preset ustun (kecha/bugun/ertaga)
        if preset in {"yesterday", "today", "tomorrow"}:
            if preset == "yesterday":
                start = end = today - timedelta(days=1)
            elif preset == "tomorrow":
                start = end = today + timedelta(days=1)
            else:
                start = end = today
            return start, end, preset

        # Qo‘lda kiritilgan start/end
        start = self._parse_date_safe(self.request.GET.get("start_date"))
        end   = self._parse_date_safe(self.request.GET.get("end_date"))

        # Default: bugun
        if not start and not end:
            start = end = today

        # Bittasi yo‘q bo‘lsa ikkinchisiga teng
        if start and not end:
            end = start
        if end and not start:
            start = end

        # Noto‘g‘ri tartib bo‘lsa almashtiramiz
        if start and end and end < start:
            start, end = end, start

        # Agar aynan bitta kun bo‘lsa, avtomatik preset nomini ham qaytaramiz
        auto_preset = ""
        if start and end and start == end:
            if start == today:
                auto_preset = "today"
            elif start == today - timedelta(days=1):
                auto_preset = "yesterday"
            elif start == today + timedelta(days=1):
                auto_preset = "tomorrow"

        return start, end, auto_preset

    # --- Asosiy queryset: sana oraliq bo‘yicha filtrlash ---
    def get_queryset(self):
        qs = (Order.objects
              .select_related("client", "courier")
              .prefetch_related("client__phone_numbers")
              .order_by("-created_at"))

        start, end, _ = self._get_date_range()
        if start and end:
            qs = qs.filter(effective_date__range=(start, end))

        status = self.request.GET.get("status") or ""
        courier = self.request.GET.get("courier") or ""
        q = (self.request.GET.get("q") or "").strip()

        if status in {"pending", "completed", "cancelled"}:
            qs = qs.filter(status=status)

        if courier:
            try:
                qs = qs.filter(courier_id=int(courier))
            except ValueError:
                pass

        if q:
            qs = qs.filter(client__name__icontains=q)
        return qs

    # --- Template context ---
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        start, end, preset = self._get_date_range()
        today = timezone.localdate()
        ctx.update({
            "start_date": start,
            "end_date": end,
            "preset": preset,                     # tugmalarda “aktiv” ko‘rsatish uchun
            "today": today,
            "yesterday": today - timedelta(days=1),
            "tomorrow": today + timedelta(days=1),
            "selected_status": self.request.GET.get("status") or "",
            "selected_courier": self.request.GET.get("courier") or "",
            "q": (self.request.GET.get("q") or "").strip(),
        })

        filtered_qs = self.get_queryset()
        status_counts = {
            "all": filtered_qs.count(),
            "pending": filtered_qs.filter(status="pending").count(),
            "completed": filtered_qs.filter(status="completed").count(),
            "cancelled": filtered_qs.filter(status="cancelled").count(),
        }
        totals = filtered_qs.aggregate(
            cash_total=Sum("cash_amount"),
            card_total=Sum("card_amount"),
            perechesleniya_total=Sum("perechesleniya_amount"),
            debt_total=Sum("debt_amount"),
            inquantity_total=Sum("inquantity"),
            outquantity_total=Sum("outquantity"),
        )
        cash_total = totals["cash_total"] or 0
        card_total = totals["card_total"] or 0
        perechesleniya_total = totals["perechesleniya_total"] or 0

        ctx["status_counts"] = status_counts
        ctx["cash_total"] = cash_total
        ctx["card_total"] = card_total
        ctx["perechesleniya_total"] = perechesleniya_total
        ctx["debt_total"] = totals["debt_total"] or 0
        ctx["daily_total"] = cash_total + card_total + perechesleniya_total
        ctx["inquantity_total"] = totals["inquantity_total"] or 0
        ctx["outquantity_total"] = totals["outquantity_total"] or 0

        group = Group.objects.filter(name="couriers").first()
        ctx["couriers"] = (
            User.objects.filter(groups=group, is_active=True).order_by("username")
            if group else User.objects.none()
        )

        # Mini xarita: shu oraliqqa tushgan, koordinatasi bor buyurtmalar (50 taga cheklaymiz)
        map_qs = (filtered_qs
                  .filter(client__latitude__isnull=False,
                          client__longitude__isnull=False)
                  .order_by("-created_at")[:50])

        ctx["map_points"] = [
            {
                "id": o.id,
                "client": o.client.name,
                "lat": o.client.latitude,
                "lon": o.client.longitude,
                "status": o.get_status_display(),
                "price": float(o.get_total_price()),
                "notes": o.notes or "",
            }
            for o in map_qs
        ]
        return ctx


class OrdersMapView(SuperuserRequiredMixin, TemplateView):
    template_name = "orders/order_map.html"

    # --- Sana parsing: bir nechta format ---
    def _parse_date_safe(self, s: str | None):
        if not s:
            return None
        d = parse_date(s)  # YYYY-MM-DD
        if d:
            return d
        for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
        return None

    def _get_date_range(self, request):
        today = timezone.localdate()
        preset = (request.GET.get("preset") or "").lower()

        if preset in {"yesterday", "today", "tomorrow"}:
            if preset == "yesterday":
                start = end = today - timedelta(days=1)
            elif preset == "tomorrow":
                start = end = today + timedelta(days=1)
            else:
                start = end = today
            return start, end, preset

        start = self._parse_date_safe(request.GET.get("start_date"))
        end   = self._parse_date_safe(request.GET.get("end_date"))

        if not start and not end:
            start = end = today
        if start and not end:
            end = start
        if end and not start:
            start = end
        if start and end and end < start:
            start, end = end, start

        auto = ""
        if start == end:
            if start == today:
                auto = "today"
            elif start == today - timedelta(days=1):
                auto = "yesterday"
            elif start == today + timedelta(days=1):
                auto = "tomorrow"

        return start, end, auto or preset

    def _courier_qs(self):
        g = Group.objects.filter(name="couriers").first()
        if not g:
            return User.objects.none()
        return User.objects.filter(groups=g, is_active=True).order_by("username")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = self.request

        # Sana oraliq
        start, end, preset = self._get_date_range(req)

        # Kurer filtri (bir yoki ko‘p qiymat)
        selected_ids = []
        if "courier" in req.GET:
            # ?courier=1&courier=3 kabi
            try:
                selected_ids = [int(x) for x in req.GET.getlist("courier") if x.strip()]
            except ValueError:
                selected_ids = []

        qs = (Order.objects
              .select_related("client", "courier")
              .filter(client__latitude__isnull=False,
                      client__longitude__isnull=False,
                      effective_date__range=(start, end))
              .order_by("-created_at"))

        if selected_ids:
            qs = qs.filter(courier_id__in=selected_ids)

        selected_assignment = req.GET.get("assignment", "").strip()
        if selected_assignment == "assigned":
            qs = qs.filter(courier_id__isnull=False)
        elif selected_assignment == "unassigned":
            qs = qs.filter(courier_id__isnull=True)

        selected_status = req.GET.get("status", "").strip()
        if selected_status in {"pending", "completed", "cancelled"}:
            qs = qs.filter(status=selected_status)

        ctx["points"] = [
            {
                "id": o.id,
                "client": o.client.name,
                "lat": o.client.latitude,
                "lon": o.client.longitude,
                "status": o.get_status_display(),
                "status_raw": o.status,
                "price": float(o.price),
                "date": o.effective_date.isoformat(),
                "courier": (o.courier.username if o.courier_id else None),
                "courier_id": o.courier_id,
                "inquantity": o.inquantity,
                "outquantity": o.outquantity,
                "notes": o.notes or "",
                "address": o.client.caption or "",
            }
            for o in qs
        ]

        ctx["start_date"] = start
        ctx["end_date"] = end
        ctx["preset"] = preset
        ctx["selected_couriers"] = selected_ids
        ctx["selected_assignment"] = selected_assignment
        ctx["selected_status"] = selected_status
        
        # Marshrut ma'lumotlarini olish
        routes = CourierRoute.objects.filter(
            date__range=(start, end)
        ).select_related('courier')
        
        routes_data = []
        for route in routes:
            routes_data.append({
                'courier_id': route.courier_id,
                'courier_name': route.courier.username,
                'date': route.date.isoformat(),
                'route_data': route.route_data,
                'color': route.color
            })
        
        # Kuryer ro'yxati (HTML uchun va JSON uchun)
        couriers_list = list(self._courier_qs().values("id", "username"))
        
        # JSON serialize qilish (template uchun)
        ctx["points"] = json.dumps(ctx["points"])
        ctx["couriers"] = couriers_list  # HTML dropdown uchun
        ctx["couriers_json"] = json.dumps(couriers_list)  # JavaScript uchun
        ctx["routes"] = json.dumps(routes_data)
        ctx["yandex_maps_api_key"] = settings.YANDEX_MAPS_API_KEY
        
        return ctx


# Buyurtmaga kuryer biriktirish API
@require_POST
@user_passes_test(lambda u: u.is_superuser)
def assign_courier_to_order(request, order_id):
    """Admin xaritadan buyurtmaga kuryer biriktiradi"""
    try:
        order = Order.objects.get(id=order_id)
        data = json.loads(request.body)
        courier_id = data.get('courier_id')
        
        if courier_id:
            courier = User.objects.get(id=courier_id)
            order.courier = courier
        else:
            order.courier = None
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Kuryer muvaffaqiyatli biriktirildi',
            'courier': order.courier.username if order.courier else None
        })
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Buyurtma topilmadi'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Kuryer topilmadi'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@user_passes_test(lambda u: u.is_superuser)
def bulk_assign_courier_to_orders(request):
    """Admin xaritada tanlangan buyurtmalarni bitta kuryerga biriktiradi."""
    try:
        data = json.loads(request.body)
        raw_order_ids = data.get("order_ids", [])
        courier_id = data.get("courier_id")

        if not isinstance(raw_order_ids, list):
            return JsonResponse({"success": False, "error": "Buyurtmalar ro'yxati noto'g'ri"}, status=400)

        order_ids = []
        for raw_id in raw_order_ids:
            try:
                order_ids.append(int(raw_id))
            except (TypeError, ValueError):
                return JsonResponse({"success": False, "error": "Buyurtma ID noto'g'ri"}, status=400)

        order_ids = list(dict.fromkeys(order_ids))
        if not order_ids:
            return JsonResponse({"success": False, "error": "Kamida bitta buyurtma tanlang"}, status=400)

        courier = None
        if courier_id:
            try:
                courier = User.objects.get(id=int(courier_id), is_active=True)
            except (TypeError, ValueError, User.DoesNotExist):
                return JsonResponse({"success": False, "error": "Kuryer topilmadi"}, status=404)

            courier_group = Group.objects.filter(name="couriers").first()
            if courier_group and not courier.groups.filter(id=courier_group.id).exists():
                return JsonResponse({"success": False, "error": "Tanlangan foydalanuvchi kuryer emas"}, status=400)

        updated_count = Order.objects.filter(id__in=order_ids).update(courier=courier)

        return JsonResponse({
            "success": True,
            "message": "Buyurtmalar muvaffaqiyatli yangilandi",
            "updated_count": updated_count,
            "courier": courier.username if courier else None,
        })
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON ma'lumot noto'g'ri"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# Kuryer marshrutini saqlash/o'chirish API
@require_POST
@user_passes_test(lambda u: u.is_superuser)
def save_courier_route(request):
    """Admin marshrut chizib, saqlaydi"""
    try:
        data = json.loads(request.body)
        courier_id = data.get('courier_id')
        date_str = data.get('date')
        route_data = data.get('route_data', [])
        color = data.get('color', '#2563eb')
        
        if not courier_id or not date_str:
            return JsonResponse({'success': False, 'error': 'Kuryer va sana majburiy'}, status=400)
        
        courier = User.objects.get(id=courier_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Marshrut mavjud bo'lsa yangilash, yo'q bo'lsa yaratish
        route, created = CourierRoute.objects.update_or_create(
            courier=courier,
            date=date,
            defaults={
                'route_data': route_data,
                'color': color
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Marshrut saqlandi' if created else 'Marshrut yangilandi',
            'route_id': route.id
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Kuryer topilmadi'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@user_passes_test(lambda u: u.is_superuser)
def delete_courier_route(request):
    """Marshrutni o'chirish"""
    try:
        data = json.loads(request.body)
        courier_id = data.get('courier_id')
        date_str = data.get('date')
        
        if not courier_id or not date_str:
            return JsonResponse({'success': False, 'error': 'Kuryer va sana majburiy'}, status=400)
        
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        deleted_count, _ = CourierRoute.objects.filter(
            courier_id=courier_id,
            date=date
        ).delete()
        
        if deleted_count > 0:
            return JsonResponse({'success': True, 'message': 'Marshrut o\'chirildi'})
        else:
            return JsonResponse({'success': False, 'error': 'Marshrut topilmadi'}, status=404)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


class OrderCreateView(SuperuserRequiredMixin, CreateView):
    model = Order
    form_class = OrderForm
    template_name = "orders/order_form.html"
    success_url = reverse_lazy("orders:list")

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get("client")
        if client_id:
            initial["client"] = client_id
        return initial


class OrderDetailView(SuperuserRequiredMixin, DetailView):
    model = Order
    template_name = "orders/order_detail.html"
    context_object_name = "order"
    
    def get_queryset(self):
        return Order.objects.select_related("client").prefetch_related("client__phone_numbers")

class OrderUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "orders/order_form.html"
    context_object_name = "order"
    
    def get_queryset(self):
        return Order.objects.select_related("client").prefetch_related("client__phone_numbers")

    def get_success_url(self):
        # Yangilangan buyurtmaning detail sahifasiga qaytamiz
        return reverse_lazy("orders:detail", kwargs={"pk": self.object.pk})


class OrderDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Order
    template_name = "orders/order_confirm_delete.html"
    context_object_name = "order"
    success_url = reverse_lazy("orders:list")
