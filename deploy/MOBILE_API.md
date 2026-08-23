# MineraLife Courier mobile API

Mobil API bazaviy manzili:

```text
https://mineralife.uz/api/mobile/v1/
```

Kirishdan tashqari barcha so'rovlarda quyidagi sarlavha bo'lishi kerak:

```http
Authorization: Token <token>
```

## Endpointlar

| Method | Endpoint | Vazifasi |
| --- | --- | --- |
| `POST` | `auth/login/` | Kuryer login/paroli orqali token olish |
| `POST` | `auth/logout/` | Joriy tokenni bekor qilish |
| `GET` | `me/` | Kuryer profili va oxirgi joylashuvi |
| `GET` | `dashboard/?date=YYYY-MM-DD` | Kunlik statistika, buyurtmalar va marshrut |
| `GET` | `orders/?date=YYYY-MM-DD&status=pending` | Kuryerning buyurtmalarini filtrlash |
| `GET` | `orders/<id>/` | Kuryerga tegishli buyurtma tafsiloti |
| `PATCH` | `orders/<id>/` | Bugungi buyurtma, to'lov va holatni yangilash |
| `GET` | `location/` | Kuryerning serverdagi oxirgi joylashuvi |
| `POST` | `location/` | Native GPS nuqtasini serverga yuborish |

API faqat faol, `couriers` guruhiga biriktirilgan foydalanuvchini qabul qiladi.
Kuryer faqat o'z buyurtmalarini ko'radi va faqat bugungi buyurtmani tahrirlaydi.

## Serverga chiqarish

Kod yangilangandan keyin loyiha virtual muhitida:

```bash
cd /home/MineraLife
source .venv/bin/activate
python manage.py migrate
python manage.py check
sudo systemctl restart mineralife
sudo systemctl status mineralife --no-pager
```

Nginx butun domenni Gunicorn'ning `127.0.0.1:8027` manziliga uzatayotgan bo'lsa,
`/api/mobile/v1/` uchun alohida `location` bloki kerak emas.

Tekshirish:

```bash
curl -X POST https://mineralife.uz/api/mobile/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"KURYER_LOGIN","password":"KURYER_PAROL"}'
```

Javobdagi token bilan:

```bash
curl https://mineralife.uz/api/mobile/v1/dashboard/ \
  -H 'Authorization: Token TOKENNI_SHU_YERGA_QOYING'
```
