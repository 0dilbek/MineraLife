#!/usr/bin/env python3
"""zahira_nusxa.sql (MySQL dump) dan db.sqlite3 ga yangi/ yangilangan ma'lumotlarni sinxronlash."""

import os
import shutil
import sqlite3
import sys

from common.text_utils import normalize_multiline_text
from fix_sqlite_autoincrement import fix_auth_user, refresh_sqlite_sequences
from mysql_to_sqlite import convert_mysql_to_sqlite, split_sql_statements

SOURCE_SQL = "zahira_nusxa.sql"
TEMP_DB = "zahira_temp.db"
TARGET_DB = "db.sqlite3"

PAYMENT_FIELD_MAP = {
    "cash": "cash_amount",
    "card": "card_amount",
    "perechesleniya": "perechesleniya_amount",
    "debt": "debt_amount",
}


def build_temp_db():
    if os.path.exists(TEMP_DB):
        os.remove(TEMP_DB)

    with open(SOURCE_SQL, "r", encoding="utf-8") as f:
        mysql_sql = f.read()

    sqlite_sql = convert_mysql_to_sqlite(mysql_sql)
    conn = sqlite3.connect(TEMP_DB)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")
    for stmt in split_sql_statements(sqlite_sql):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)
    conn.commit()
    conn.close()


def payment_amounts(payment_method, outquantity, price):
    total = float(outquantity) * float(price) if outquantity else 0
    amounts = {field: 0 for field in PAYMENT_FIELD_MAP.values()}
    field = PAYMENT_FIELD_MAP.get(payment_method)
    if field:
        amounts[field] = total
    return amounts


def order_row_to_target(row):
    (
        order_id,
        price,
        status,
        effective_date,
        notes,
        created_at,
        updated_at,
        client_id,
        courier_id,
        payment_method,
        inquantity,
        outquantity,
    ) = row
    amounts = payment_amounts(payment_method, outquantity, price)
    return (
        order_id,
        status,
        effective_date,
        notes,
        created_at,
        updated_at,
        client_id,
        courier_id,
        inquantity,
        outquantity,
        amounts["card_amount"],
        amounts["cash_amount"],
        amounts["debt_amount"],
        amounts["perechesleniya_amount"],
        price,
    )


def fetch_ids(cur, table):
    cur.execute(f"SELECT id FROM {table}")
    return {row[0] for row in cur.fetchall()}


def sync_clients(src, dst):
    src_cur = src.cursor()
    dst_cur = dst.cursor()
    src_ids = fetch_ids(src_cur, "clients_client")
    dst_ids = fetch_ids(dst_cur, "clients_client")
    missing = sorted(src_ids - dst_ids)

    inserted = 0
    updated = 0
    for client_id in missing:
        src_cur.execute(
            "SELECT id, name, longitude, latitude, created_at, updated_at, caption "
            "FROM clients_client WHERE id = ?",
            (client_id,),
        )
        row = list(src_cur.fetchone())
        row[6] = normalize_multiline_text(row[6])
        dst_cur.execute(
            "INSERT INTO clients_client "
            "(id, name, longitude, latitude, created_at, updated_at, caption, is_departed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            row,
        )
        inserted += 1

    for client_id in sorted(src_ids & dst_ids):
        src_cur.execute(
            "SELECT name, longitude, latitude, created_at, updated_at, caption "
            "FROM clients_client WHERE id = ?",
            (client_id,),
        )
        src_row = src_cur.fetchone()
        dst_cur.execute(
            "SELECT name, longitude, latitude, created_at, updated_at, caption "
            "FROM clients_client WHERE id = ?",
            (client_id,),
        )
        dst_row = dst_cur.fetchone()
        if src_row != dst_row and src_row[4] >= dst_row[4]:
            cleaned_row = list(src_row)
            cleaned_row[5] = normalize_multiline_text(cleaned_row[5])
            dst_cur.execute(
                "UPDATE clients_client SET name=?, longitude=?, latitude=?, created_at=?, "
                "updated_at=?, caption=? WHERE id=?",
                (*cleaned_row, client_id),
            )
            updated += 1

    return inserted, updated


def sync_phones(src, dst):
    src_cur = src.cursor()
    dst_cur = dst.cursor()
    src_ids = fetch_ids(src_cur, "clients_clientphonenumber")
    dst_ids = fetch_ids(dst_cur, "clients_clientphonenumber")
    missing = sorted(src_ids - dst_ids)

    inserted = 0
    updated = 0
    for phone_id in missing:
        src_cur.execute(
            "SELECT id, phone_number, is_primary, created_at, client_id "
            "FROM clients_clientphonenumber WHERE id = ?",
            (phone_id,),
        )
        dst_cur.execute(
            "INSERT INTO clients_clientphonenumber "
            "(id, phone_number, is_primary, created_at, client_id) VALUES (?, ?, ?, ?, ?)",
            src_cur.fetchone(),
        )
        inserted += 1

    for phone_id in sorted(src_ids & dst_ids):
        src_cur.execute(
            "SELECT phone_number, is_primary, created_at, client_id "
            "FROM clients_clientphonenumber WHERE id = ?",
            (phone_id,),
        )
        src_row = src_cur.fetchone()
        dst_cur.execute(
            "SELECT phone_number, is_primary, created_at, client_id "
            "FROM clients_clientphonenumber WHERE id = ?",
            (phone_id,),
        )
        dst_row = dst_cur.fetchone()
        if src_row != dst_row:
            dst_cur.execute(
                "UPDATE clients_clientphonenumber SET phone_number=?, is_primary=?, "
                "created_at=?, client_id=? WHERE id=?",
                (*src_row, phone_id),
            )
            updated += 1

    return inserted, updated


def sync_routes(src, dst):
    src_cur = src.cursor()
    dst_cur = dst.cursor()
    src_ids = fetch_ids(src_cur, "couriers_courierroute")
    dst_ids = fetch_ids(dst_cur, "couriers_courierroute")
    missing = sorted(src_ids - dst_ids)

    inserted = 0
    for route_id in missing:
        src_cur.execute(
            "SELECT id, date, route_data, color, created_at, updated_at, courier_id "
            "FROM couriers_courierroute WHERE id = ?",
            (route_id,),
        )
        dst_cur.execute(
            "INSERT INTO couriers_courierroute "
            "(id, date, route_data, color, created_at, updated_at, courier_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            src_cur.fetchone(),
        )
        inserted += 1

    return inserted


def sync_orders(src, dst):
    src_cur = src.cursor()
    dst_cur = dst.cursor()
    src_ids = fetch_ids(src_cur, "orders_order")
    dst_ids = fetch_ids(dst_cur, "orders_order")
    missing = sorted(src_ids - dst_ids)

    inserted = 0
    updated = 0
    for order_id in missing:
        src_cur.execute(
            "SELECT id, price, status, effective_date, notes, created_at, updated_at, "
            "client_id, courier_id, payment_method, inquantity, outquantity "
            "FROM orders_order WHERE id = ?",
            (order_id,),
        )
        order_row = list(order_row_to_target(src_cur.fetchone()))
        order_row[3] = normalize_multiline_text(order_row[3])
        dst_cur.execute(
            "INSERT INTO orders_order "
            "(id, status, effective_date, notes, created_at, updated_at, client_id, courier_id, "
            "inquantity, outquantity, card_amount, cash_amount, debt_amount, "
            "perechesleniya_amount, price) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            order_row,
        )
        inserted += 1

    for order_id in sorted(src_ids & dst_ids):
        src_cur.execute(
            "SELECT id, price, status, effective_date, notes, created_at, updated_at, "
            "client_id, courier_id, payment_method, inquantity, outquantity "
            "FROM orders_order WHERE id = ?",
            (order_id,),
        )
        src_target = order_row_to_target(src_cur.fetchone())
        dst_cur.execute(
            "SELECT status, effective_date, notes, created_at, updated_at, client_id, courier_id, "
            "inquantity, outquantity, card_amount, cash_amount, debt_amount, "
            "perechesleniya_amount, price "
            "FROM orders_order WHERE id = ?",
            (order_id,),
        )
        dst_row = dst_cur.fetchone()
        src_compare = list(src_target[1:])
        src_compare[2] = normalize_multiline_text(src_compare[2])
        if tuple(src_compare) != dst_row and src_target[5] >= dst_row[4]:
            dst_cur.execute(
                "UPDATE orders_order SET status=?, effective_date=?, notes=?, created_at=?, "
                "updated_at=?, client_id=?, courier_id=?, inquantity=?, outquantity=?, "
                "card_amount=?, cash_amount=?, debt_amount=?, perechesleniya_amount=?, price=? "
                "WHERE id=?",
                (*src_compare, order_id),
            )
            updated += 1

    return inserted, updated


def print_counts(conn, label):
    cur = conn.cursor()
    tables = [
        "clients_client",
        "clients_clientphonenumber",
        "orders_order",
        "couriers_courierroute",
    ]
    print(f"\n{label}:")
    for table in tables:
        cur.execute(f"SELECT COUNT(*), MAX(id) FROM {table}")
        count, max_id = cur.fetchone()
        print(f"  {table}: {count} qator, max_id={max_id}")


def main():
    if not os.path.exists(SOURCE_SQL):
        print(f"Xato: {SOURCE_SQL} topilmadi", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(TARGET_DB):
        print(f"Xato: {TARGET_DB} topilmadi", file=sys.stderr)
        sys.exit(1)

    print("MySQL dump vaqtincha SQLite ga konvertatsiya qilinmoqda...")
    build_temp_db()

    src = sqlite3.connect(TEMP_DB)
    dst = sqlite3.connect(TARGET_DB)
    dst.execute("PRAGMA foreign_keys = OFF;")

    print_counts(src, "Manba (zahira_nusxa.sql)")
    print_counts(dst, "Maqsad (db.sqlite3) - oldin")

    results = {}
    results["clients"] = sync_clients(src, dst)
    results["phones"] = sync_phones(src, dst)
    results["routes"] = sync_routes(src, dst)
    results["orders"] = sync_orders(src, dst)

    fix_auth_user(dst.cursor())
    refresh_sqlite_sequences(dst.cursor())

    dst.commit()
    dst.execute("PRAGMA foreign_keys = ON;")

    print_counts(dst, "Maqsad (db.sqlite3) - keyin")

    print("\nSinxronlash natijasi:")
    print(f"  Mijozlar: {results['clients'][0]} yangi, {results['clients'][1]} yangilandi")
    print(f"  Telefonlar: {results['phones'][0]} yangi, {results['phones'][1]} yangilandi")
    print(f"  Marshrutlar: {results['routes']} yangi")
    print(f"  Buyurtmalar: {results['orders'][0]} yangi, {results['orders'][1]} yangilandi")

    src.close()
    dst.close()

    if os.path.exists(TEMP_DB):
        os.remove(TEMP_DB)

    print("\nTayyor: db.sqlite3 yangilandi.")


if __name__ == "__main__":
    main()