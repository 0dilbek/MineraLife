from django.views.generic import ListView
from .models import Client
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, DeleteView, UpdateView
from django.contrib import messages
from .models import Client
from .forms import ClientForm, ClientPhoneNumberFormSet
from admin_panel.mixins import SuperuserRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from datetime import timedelta

from django.db.models import Count, Max, Min, OuterRef, Q, Subquery
from django.utils import timezone
from django.core.paginator import Paginator
import json

class ClientListView(SuperuserRequiredMixin, ListView):
    model = Client
    template_name = 'clients/clients_list.html'
    context_object_name = 'clients'
    paginate_by = 12  # har sahifada nechta yozuv
    ordering = '-created_at'  # xohlasangiz
    
    def get_queryset(self):
        from orders.models import Order

        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())
        last_order = (
            Order.objects
            .filter(client=OuterRef("pk"))
            .order_by("-effective_date", "-created_at", "-pk")
        )
        queryset = (
            Client.objects
            .prefetch_related('phone_numbers')
            .annotate(
                phone_count=Count("phone_numbers", distinct=True),
                first_order_date=Min("orders__effective_date"),
                last_order_id=Subquery(last_order.values("pk")[:1]),
                last_order_date=Subquery(last_order.values("effective_date")[:1]),
            )
            .order_by(self.ordering)
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | 
                Q(phone_numbers__phone_number__icontains=q)
            ).distinct()

        status_filter = self.request.GET.get("status", "").strip()
        if status_filter == "new":
            queryset = queryset.filter(is_departed=False, first_order_date__gte=week_start, first_order_date__lte=today)
        elif status_filter == "active":
            queryset = queryset.filter(is_departed=False, last_order_id__isnull=False)
        elif status_filter == "departed":
            queryset = queryset.filter(is_departed=True)
        elif status_filter == "no_orders":
            queryset = queryset.filter(last_order_id__isnull=True)
        elif status_filter == "no_phone":
            queryset = queryset.filter(phone_count=0)
        elif status_filter == "no_location":
            queryset = queryset.filter(Q(latitude__isnull=True) | Q(longitude__isnull=True))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        context["status"] = self.request.GET.get("status", "")
        context["new_clients_start"] = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        context["today"] = timezone.localdate()
        context["client_filters"] = [
            {"key": "", "label": "Barchasi"},
            {"key": "new", "label": "Yangi mijozlar"},
            {"key": "active", "label": "Faollar"},
            {"key": "departed", "label": "Bizdan ketgan"},
            {"key": "no_orders", "label": "Buyurtmasiz"},
            {"key": "no_phone", "label": "Telefonsiz"},
            {"key": "no_location", "label": "Koordinatasiz"},
        ]
        return context

class ClientCreateView(SuperuserRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/client_form.html"
    success_url = reverse_lazy("clients:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['phone_formset'] = ClientPhoneNumberFormSet(self.request.POST)
        else:
            context['phone_formset'] = ClientPhoneNumberFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        phone_formset = context['phone_formset']
        
        with transaction.atomic():
            if phone_formset.is_valid():
                self.object = form.save()
                phone_formset.instance = self.object
                phone_formset.save()
                messages.success(self.request, "Mijoz muvaffaqiyatli qo'shildi.")
                return super().form_valid(form)
            else:
                messages.error(self.request, "Telefon raqamlarda xatolik bor. Iltimos tekshiring.")
                return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, "Formada xatolar bor. Iltimos, tekshirib qayta yuboring.")
        return super().form_invalid(form)

class ClientDetailView(SuperuserRequiredMixin, DetailView):
    model = Client
    template_name = "clients/client_detail.html"
    context_object_name = "client"
    
    def get_queryset(self):
        return Client.objects.prefetch_related('phone_numbers')

class ClientDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Client
    template_name = "clients/client_confirm_delete.html"
    context_object_name = "client"
    success_url = reverse_lazy("clients:list")

class ClientUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/client_form.html"
    context_object_name = "client"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['phone_formset'] = ClientPhoneNumberFormSet(self.request.POST, instance=self.object)
        else:
            context['phone_formset'] = ClientPhoneNumberFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        phone_formset = context['phone_formset']
        
        with transaction.atomic():
            if phone_formset.is_valid():
                self.object = form.save()
                phone_formset.instance = self.object
                phone_formset.save()
                messages.success(self.request, "Mijoz ma'lumotlari yangilandi.")
                return super().form_valid(form)
            else:
                messages.error(self.request, "Telefon raqamlarda xatolik bor. Iltimos tekshiring.")
                return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy("clients:detail", kwargs={"pk": self.object.pk})


@require_POST
@login_required
def toggle_client_departed(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Bu amal uchun ruxsat yo'q.")
        return redirect("clients:detail", pk=pk)

    client = get_object_or_404(Client, pk=pk)
    client.is_departed = not client.is_departed
    client.save(update_fields=["is_departed", "updated_at"])
    if client.is_departed:
        messages.success(request, f"{client.name} 'bizdan ketgan' deb belgilandi.")
    else:
        messages.success(request, f"{client.name} yana faol mijoz sifatida belgilandi.")
    return redirect("clients:detail", pk=pk)


@require_http_methods(["GET"])
def check_name_exists(request):
    """AJAX endpoint to check if client name already exists"""
    name = request.GET.get('name', '').strip()
    client_id = request.GET.get('client_id', None)
    
    if not name:
        return JsonResponse({'exists': False})
    
    # Check if name exists
    query = Client.objects.filter(name__iexact=name)
    
    # If updating existing client, exclude current client from check
    if client_id:
        query = query.exclude(pk=client_id)
    
    exists = query.exists()
    
    return JsonResponse({'exists': exists, 'name': name})


@login_required
def clients_map(request):
    """Barcha mijozlarni xaritada ko'rsatish"""
    # Oxirgi buyurtma sanasini annotate qilish
    clients = Client.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).prefetch_related('phone_numbers').annotate(
        last_order_date=Max('orders__effective_date')
    )
    
    points = [{
        "id": c.id,
        "name": c.name,
        "phone": c.get_phone_numbers_display(),
        "caption": c.get_caption_display_text() or "",
        "lat": c.latitude,
        "lon": c.longitude,
        "is_departed": c.is_departed,
        "last_order_date": c.last_order_date.isoformat() if c.last_order_date else None,
    } for c in clients]
    
    return render(request, "clients/clients_map.html", {
        "points": json.dumps(points),
        "total_clients": clients.count(),
        "yandex_maps_api_key": settings.YANDEX_MAPS_API_KEY,
    })
