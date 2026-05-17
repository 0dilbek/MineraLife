from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Sum, F, Count, Avg, Q, Case, When, IntegerField, DecimalField
from django.utils.timezone import now
from django.core.paginator import Paginator
from datetime import timedelta, date
from collections import defaultdict
from orders.models import Order
import json
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

def reports_view(request):
    # Foydalanuvchi filterini olish
    today = now().date()
    start = request.GET.get("start")
    end = request.GET.get("end")
    quick = request.GET.get("quick")  # default = None
    page_num = request.GET.get("page", 1)

    if quick == "today":
        start_date = today
        end_date = today
    elif quick == "week":
        # Haftaning boshidan (dushanba) bugungi kungacha
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif quick == "month":
        start_date = today.replace(day=1)
        end_date = today
    elif quick == "6months":
        start_date = today - timedelta(days=180)
        end_date = today
    elif quick == "year":
        start_date = today - timedelta(days=365)
        end_date = today
    elif start and end:
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
        except (ValueError, TypeError):
            # Fallback agar sanalar noto'g'ri bo'lsa
            start_date = today.replace(day=1)
            end_date = today
    else:
        # Default = joriy oy
        quick = "month"
        start_date = today.replace(day=1)
        end_date = today

    # Asosiy queryset - select_related bilan optimizatsiya
    qs = Order.objects.filter(
        effective_date__range=[start_date, end_date],
        status="completed"  # faqat tugagan buyurtmalar
    ).select_related("client", "courier")

    # === UMUMIY STATISTIKA ===
    pay_totals = qs.aggregate(
        cash_total=Sum("cash_amount"),
        card_total=Sum("card_amount"),
        pereches_total=Sum("perechesleniya_amount"),
        debt_total=Sum("debt_amount"),
    )
    cash_total = pay_totals["cash_total"] or 0
    card_total = pay_totals["card_total"] or 0
    pereches_total = pay_totals["pereches_total"] or 0
    debt_total = pay_totals["debt_total"] or 0
    total = cash_total + card_total + pereches_total + debt_total

    # Umumiy buyurtmalar soni va o'rtacha narx
    total_orders = qs.count()
    avg_order_value = qs.aggregate(avg=Avg(F("price") * F("outquantity")))["avg"] or 0
    
    # Jami sotilgan mahsulotlar miqdori
    total_sold = qs.aggregate(total=Sum("outquantity"))["total"] or 0
    total_received = qs.aggregate(total=Sum("inquantity"))["total"] or 0

    # === KUNLIK SAVDO DINAMIKASI (chiziqli diagramma uchun) ===
    daily_sales = defaultdict(lambda: {"revenue": 0, "orders": 0, "quantity": 0})
    
    for order in qs.values("effective_date").annotate(
        revenue=Sum(F("price") * F("outquantity")),
        orders_count=Count("id"),
        quantity=Sum("outquantity")
    ).order_by("effective_date"):
        date_str = order["effective_date"].strftime("%Y-%m-%d")
        daily_sales[date_str] = {
            "revenue": float(order["revenue"] or 0),
            "orders": order["orders_count"],
            "quantity": order["quantity"] or 0
        }
    
    # Sanalarni to'ldirish (bo'sh kunlar uchun)
    current = start_date
    chart_labels = []
    chart_revenue = []
    chart_orders = []
    chart_quantity = []
    
    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        chart_labels.append(date_str)
        chart_revenue.append(daily_sales[date_str]["revenue"])
        chart_orders.append(daily_sales[date_str]["orders"])
        chart_quantity.append(daily_sales[date_str]["quantity"])
        current += timedelta(days=1)

    # === KURYERLAR BO'YICHA STATISTIKA ===
    courier_stats = (
        qs.values("courier__id", "courier__username")
        .annotate(
            total_revenue=Sum(F("price") * F("outquantity")),
            total_orders=Count("id"),
            total_quantity=Sum("outquantity"),
            avg_order=Avg(F("price") * F("outquantity"))
        )
        .order_by("-total_revenue")
    )

    # === MIJOZLAR BO'YICHA STATISTIKA (pagination bilan) ===
    clients_summary = (
        qs.values("client__id", "client__name", "client__caption")
        .annotate(
            total_revenue=Sum(F("price") * F("outquantity")),
            total_orders=Count("id"),
            total_quantity=Sum("outquantity"),
            avg_order=Avg(F("price") * F("outquantity"))
        )
        .order_by("-total_revenue")
    )
    
    # Pagination
    paginator = Paginator(clients_summary, 50)  # Har sahifada 50 ta mijoz
    clients_page = paginator.get_page(page_num)

    # Mijozga qaysi kur'er xizmat qilganini olish (faqat ko'rinayotgan mijozlar uchun)
    client_ids = [c["client__id"] for c in clients_page]
    client_couriers = {}
    for order in qs.filter(client_id__in=client_ids).select_related("client", "courier"):
        if order.client_id not in client_couriers:
            client_couriers[order.client_id] = order.courier

    # === TOP MIJOZLAR (eng ko'p daromad keltirgan 10 ta) ===
    top_clients = clients_summary[:10]

    return render(request, "hisobotlar/reports.html", {
        "start_date": start_date,
        "end_date": end_date,
        "quick": quick,
        
        # Umumiy statistika
        "cash_total": cash_total,
        "card_total": card_total,
        "pereches_total": pereches_total,
        "debt_total": debt_total,
        "total": total,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
        "total_sold": total_sold,
        "total_received": total_received,
        
        # Diagramma ma'lumotlari
        "chart_labels": json.dumps(chart_labels),
        "chart_revenue": json.dumps(chart_revenue),
        "chart_orders": json.dumps(chart_orders),
        "chart_quantity": json.dumps(chart_quantity),
        
        # Kuryerlar statistikasi
        "courier_stats": courier_stats,
        
        # Mijozlar (pagination bilan)
        "clients_page": clients_page,
        "client_couriers": client_couriers,
        
        # Top mijozlar
        "top_clients": top_clients,
        "excel_available": EXCEL_AVAILABLE,
    })


def export_excel(request):
    """Excel hisobotini eksport qilish - mijozlar bo'yicha to'lov turlari bilan"""
    if not EXCEL_AVAILABLE:
        return HttpResponse("openpyxl kutubxonasi o'rnatilmagan. pip install openpyxl", status=500)
    
    # Foydalanuvchi filterini olish (reports_view bilan bir xil)
    today = now().date()
    start = request.GET.get("start")
    end = request.GET.get("end")
    quick = request.GET.get("quick")

    if quick == "today":
        start_date = today
        end_date = today
    elif quick == "week":
        # Haftaning boshidan (dushanba) bugungi kungacha
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif quick == "month":
        start_date = today.replace(day=1)
        end_date = today
    elif quick == "6months":
        start_date = today - timedelta(days=180)
        end_date = today
    elif quick == "year":
        start_date = today - timedelta(days=365)
        end_date = today
    elif start and end:
        try:
            start_date = date.fromisoformat(start)
            end_date = date.fromisoformat(end)
        except (ValueError, TypeError):
            start_date = today.replace(day=1)
            end_date = today
    else:
        quick = "month"
        start_date = today.replace(day=1)
        end_date = today

    # Asosiy queryset
    qs = Order.objects.filter(
        effective_date__range=[start_date, end_date],
        status="completed"
    ).select_related("client", "courier")

    # Mijozlar bo'yicha to'lov turlari statistikasi
    clients_data = (
        qs.values("client__id", "client__name", "client__caption")
        .annotate(
            cash_total=Sum("cash_amount", output_field=DecimalField()),
            card_total=Sum("card_amount", output_field=DecimalField()),
            pereches_total=Sum("perechesleniya_amount", output_field=DecimalField()),
            debt_total=Sum("debt_amount", output_field=DecimalField()),
            total_orders=Count("id"),
            total_revenue=Sum(
                F("cash_amount") + F("card_amount") + F("perechesleniya_amount") + F("debt_amount"),
                output_field=DecimalField()
            )
        )
        .order_by("-total_revenue")
    )

    # Excel fayl yaratish
    wb = Workbook()
    ws = wb.active
    ws.title = "Mijozlar statistikasi"

    # Stillar
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    # Sarlavha
    ws.merge_cells('A1:H1')
    title_cell = ws['A1']
    title_cell.value = f"Mijozlar bo'yicha hisobot ({start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')})"
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = center_align
    ws.row_dimensions[1].height = 25

    # Ustun sarlavhalari
    headers = [
        "№",
        "Mijoz nomi",
        "Manzil",
        "Naqd (so'm)",
        "Karta (so'm)",
        "Perechesleniya (so'm)",
        "Qarz (so'm)",
        "JAMI (so'm)"
    ]

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = center_align

    # Ma'lumotlarni to'ldirish
    row_num = 4
    for idx, client in enumerate(clients_data, 1):
        ws.cell(row=row_num, column=1, value=idx).alignment = center_align
        ws.cell(row=row_num, column=2, value=client["client__name"])
        ws.cell(row=row_num, column=3, value=client["client__caption"] or "—")

        for col, key in [(4, "cash_total"), (5, "card_total"), (6, "pereches_total"), (7, "debt_total")]:
            cell = ws.cell(row=row_num, column=col, value=float(client[key] or 0))
            cell.alignment = right_align
            cell.number_format = '#,##0'

        total_cell = ws.cell(row=row_num, column=8, value=float(client["total_revenue"] or 0))
        total_cell.alignment = right_align
        total_cell.number_format = '#,##0'
        total_cell.font = Font(bold=True)

        for col in range(1, 9):
            ws.cell(row=row_num, column=col).border = border

        row_num += 1

    # Ustun kengliklarini sozlash
    column_widths = [5, 30, 25, 15, 15, 20, 15, 18]
    for idx, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    # Javob
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    filename = f"hisobot_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    wb.save(response)
    return response
