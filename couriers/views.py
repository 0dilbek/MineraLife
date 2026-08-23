import json
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, FormView, UpdateView, DeleteView
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from .forms import CourierUserCreateForm, CourierUserUpdateForm, CourierUserPasswordForm, CourierOrderUpdateForm, CourierQuickCompleteForm, COURIER_GROUP_NAME
from admin_panel.mixins import SuperuserRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from orders.models import Order
from django.db.models import Sum, F
from django.shortcuts import render
from django.utils.timezone import localdate
# couriers/views.py
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from orders.models import Order
from couriers.models import CourierRoute, CourierLocation

# Kuryer joylashuvi "onlayn" hisoblanadigan muddat
COURIER_LOCATION_ONLINE_WINDOW = timedelta(minutes=10)


def _safe_parse_date(s: str):
    """YYYY-MM-DD ni date ga parse qiladi; xato bo‘lsa None qaytaradi."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _courier_selected_date(request):
    today = localdate()
    preset = (request.GET.get("preset") or "today").lower()

    if preset == "yesterday":
        return today - timedelta(days=1), "yesterday"
    if preset == "tomorrow":
        return today + timedelta(days=1), "tomorrow"

    requested_date = _safe_parse_date(request.GET.get("date"))
    if requested_date:
        if requested_date == today - timedelta(days=1):
            return requested_date, "yesterday"
        if requested_date == today + timedelta(days=1):
            return requested_date, "tomorrow"
        return requested_date, ""

    return today, "today"

@login_required
def courier_dashboard(request):
    today = localdate()
    selected_date, selected_preset = _courier_selected_date(request)
    can_edit_orders = selected_date == today
    qs = (Order.objects
          .select_related("client", "courier")
          .prefetch_related("client__phone_numbers")
          .filter(
              courier=request.user,
              effective_date=selected_date
          )
          .order_by("-created_at"))

    completed_qs = qs.filter(status="completed")
    pending_count = qs.filter(status="pending").count()
    completed_count = completed_qs.count()
    cancelled_count = qs.filter(status="cancelled").count()
    totals = completed_qs.aggregate(
        cash_total=Sum("cash_amount"),
        card_total=Sum("card_amount"),
        perechesleniya_total=Sum("perechesleniya_amount"),
        debt_total=Sum("debt_amount"),
    )
    quantity_totals = qs.aggregate(
        inquantity_total=Sum("inquantity"),
    )
    plan_totals = qs.exclude(status="cancelled").aggregate(
        outquantity_plan_total=Sum("outquantity"),
    )
    delivered_totals = completed_qs.aggregate(
        outquantity_delivered_total=Sum("outquantity"),
    )
    cash_total = totals["cash_total"] or 0
    card_total = totals["card_total"] or 0
    perechesleniya_total = totals["perechesleniya_total"] or 0
    debt_total = totals["debt_total"] or 0
    daily_total = cash_total + card_total + perechesleniya_total
    inquantity_total = quantity_totals["inquantity_total"] or 0
    outquantity_delivered_total = delivered_totals["outquantity_delivered_total"] or 0
    outquantity_plan_total = plan_totals["outquantity_plan_total"] or 0

    return render(request, "couriers/dashboard.html", {
        "orders": qs,
        "cash_total": cash_total,
        "card_total": card_total,
        "perechesleniya_total": perechesleniya_total,
        "debt_total": debt_total,
        "daily_total": daily_total,
        "inquantity_total": inquantity_total,
        "outquantity_delivered_total": outquantity_delivered_total,
        "outquantity_plan_total": outquantity_plan_total,
        "pending_count": pending_count,
        "completed_count": completed_count,
        "cancelled_count": cancelled_count,
        "today": today,
        "selected_date": selected_date,
        "selected_preset": selected_preset,
        "can_edit_orders": can_edit_orders,
    })

@login_required
def courier_order_update(request, pk):
    """Kurer buyurtma holatini va to'lov usulini tahrirlay oladi"""
    today = localdate()
    order = get_object_or_404(
        Order.objects.select_related("client").prefetch_related("client__phone_numbers"), 
        pk=pk, courier=request.user
    )
    readonly = order.effective_date != today

    # Formani har doim yaratish
    form = CourierOrderUpdateForm(instance=order)

    if request.method == "POST":
        if readonly:
            messages.error(request, "Bu sanadagi buyurtmani faqat ko'rish mumkin. O'zgartirish faqat bugungi buyurtmalar uchun.")
            return redirect("couriers:order_update", pk=order.pk)

        # Quick action - modal orqali tez bajarish
        if 'quick_action' in request.POST:
            status = request.POST.get('status')
            
            if status == 'completed':
                # Modal orqali kelgan ma'lumotlarni qayta ishlash
                quick_form = CourierQuickCompleteForm(request.POST, instance=order)
                if quick_form.is_valid():
                    order = quick_form.save(commit=False)
                    order.status = 'completed'
                    order.save()
                    messages.success(request, f"Buyurtma muvaffaqiyatli bajarildi! Oldim: {order.inquantity}, Berdim: {order.outquantity} dona")
                    return redirect("couriers:dashboard")
                else:
                    messages.error(request, "Formada xatoliklar bor. Iltimos, to'g'irlang.")
                    # Quick form xato bo'lsa, oddiy formani ko'rsatish
                    form = CourierOrderUpdateForm(instance=order)
            
            elif status == 'cancelled':
                # Oddiy bekor qilish
                order.status = 'cancelled'
                order.save()
                messages.success(request, "Buyurtma bekor qilindi!")
                return redirect("couriers:dashboard")
        
        # To'liq form - barcha ma'lumotlarni tahrirlash
        else:
            form = CourierOrderUpdateForm(request.POST, instance=order)
            if form.is_valid():
                form.save()
                messages.success(request, "Buyurtma muvaffaqiyatli yangilandi!")
                return redirect("couriers:dashboard")
            else:
                messages.error(request, "Formada xatoliklar bor. Iltimos, to'g'irlang.")

    return render(request, "couriers/order_update.html", {
        "order": order,
        "form": form,
        "readonly": readonly,
    })

@login_required
def courier_map(request):
    today = localdate()
    selected_date, selected_preset = _courier_selected_date(request)
    can_edit_orders = selected_date == today
    qs = (Order.objects
          .select_related("client", "courier")
          .prefetch_related("client__phone_numbers")
          .filter(
              courier=request.user,
              effective_date=selected_date,
              client__latitude__isnull=False,
              client__longitude__isnull=False
          )
          .order_by("-created_at"))

    points = [{
        "id": o.id,
        "client": o.client.name,
        "phone": o.client.get_phone_numbers_display() or "",
        "caption": o.client.get_caption_display_text(),
        "lat": o.client.latitude,
        "lon": o.client.longitude,
        "status": o.get_status_display(),
        "status_raw": o.status,  # ('pending'...'completed'...'cancelled')
        "inquantity": o.inquantity,
        "outquantity": o.outquantity,
        "price": float(o.get_total_price()),
        "date": o.effective_date.isoformat(),
        "payment": o.get_payment_summary(),
        "notes": o.get_notes_display_text(),
    } for o in qs]

    map_totals = qs.filter(status="completed").aggregate(
        cash=Sum("cash_amount"),
        card=Sum("card_amount"),
        perechesleniya=Sum("perechesleniya_amount"),
        debt=Sum("debt_amount"),
    )
    stats = {k: (v or 0) for k, v in map_totals.items()}

    # Kuryerning bugungi marshrutini olish
    route = None
    try:
        courier_route = CourierRoute.objects.get(courier=request.user, date=selected_date)
        route = {
            'route_data': courier_route.route_data,
            'color': courier_route.color
        }
    except CourierRoute.DoesNotExist:
        pass

    return render(request, "couriers/map.html", {
        "points": json.dumps(points),
        "route": json.dumps(route) if route else 'null',
        "stats": stats,
        "today": today,
        "selected_date": selected_date,
        "selected_preset": selected_preset,
        "can_edit_orders": can_edit_orders,
    })


@login_required
@require_POST
def courier_update_location(request):
    """Kuryer brauzeridan davriy ravishda kelayotgan joylashuvni saqlaydi"""
    try:
        data = json.loads(request.body)
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"success": False, "error": "Noto'g'ri joylashuv ma'lumoti"}, status=400)

    accuracy = data.get("accuracy")
    try:
        accuracy = float(accuracy) if accuracy is not None else None
    except (TypeError, ValueError):
        accuracy = None

    CourierLocation.objects.update_or_create(
        courier=request.user,
        defaults={
            "latitude": lat,
            "longitude": lon,
            "accuracy": accuracy,
            "captured_at": timezone.now(),
        },
    )
    return JsonResponse({"success": True})


@user_passes_test(lambda u: u.is_superuser)
def courier_live_locations(request):
    """Admin xaritasi uchun barcha kuryerlarning so'nggi (onlayn) joylashuvi"""
    cutoff = timezone.now() - COURIER_LOCATION_ONLINE_WINDOW
    locations = (CourierLocation.objects
                 .select_related("courier")
                 .filter(updated_at__gte=cutoff)
                 .order_by("courier__username"))

    now_ts = timezone.now()
    data = [{
        "courier_id": loc.courier_id,
        "courier": loc.courier.username,
        "lat": loc.latitude,
        "lon": loc.longitude,
        "accuracy": loc.accuracy,
        "speed": loc.speed,
        "bearing": loc.bearing,
        "is_mocked": loc.is_mocked,
        "captured_at": loc.captured_at.isoformat(),
        "updated_at": loc.updated_at.isoformat(),
        "seconds_ago": int((now_ts - loc.updated_at).total_seconds()),
    } for loc in locations]

    return JsonResponse({"locations": data})


class StaffOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

def _courier_qs():
    group, _ = Group.objects.get_or_create(name=COURIER_GROUP_NAME)
    return User.objects.filter(groups=group).order_by("-date_joined")

class CourierListView(SuperuserRequiredMixin, ListView):
    template_name = "couriers/courier_list.html"
    context_object_name = "couriers"
    paginate_by = 12
    def get_queryset(self):
        return _courier_qs()

class CourierDetailView(SuperuserRequiredMixin, DetailView):
    template_name = "couriers/courier_detail.html"
    context_object_name = "courier"
    def get_object(self, queryset=None):
        return get_object_or_404(User, pk=self.kwargs["pk"], id__in=_courier_qs().values_list("id", flat=True))

class CourierCreateView(SuperuserRequiredMixin, FormView):
    template_name = "couriers/courier_form.html"
    form_class = CourierUserCreateForm
    success_url = reverse_lazy("couriers:list")
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

class CourierUpdateView(SuperuserRequiredMixin, UpdateView):
    model = User
    form_class = CourierUserUpdateForm
    template_name = "couriers/courier_form.html"
    context_object_name = "courier"
    def get_queryset(self):
        return _courier_qs()
    def get_success_url(self):
        return reverse_lazy("couriers:detail", kwargs={"pk": self.object.pk})

class CourierPasswordUpdateView(SuperuserRequiredMixin, FormView):
    template_name = "couriers/courier_password.html"
    form_class = CourierUserPasswordForm
    def dispatch(self, request, *args, **kwargs):
        self.courier = get_object_or_404(User, pk=kwargs["pk"], id__in=_courier_qs().values_list("id", flat=True))
        return super().dispatch(request, *args, **kwargs)
    def form_valid(self, form):
        self.courier.set_password(form.cleaned_data["password1"])
        self.courier.save()
        return redirect("couriers:detail", pk=self.courier.pk)
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["courier"] = self.courier
        return ctx

class CourierDeleteView(SuperuserRequiredMixin, DeleteView):
    template_name = "couriers/courier_confirm_delete.html"
    context_object_name = "courier"
    success_url = reverse_lazy("couriers:list")
    def get_object(self, queryset=None):
        return get_object_or_404(User, pk=self.kwargs["pk"], id__in=_courier_qs().values_list("id", flat=True))
