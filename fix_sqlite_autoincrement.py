#!/usr/bin/env python3
"""MySQL dan import qilingan SQLite bazada auth_user.id autoincrement muammosini tuzatish."""

import sqlite3
import sys

TARGET_DB = "db.sqlite3"

SEQUENCE_TABLES = [
    "auth_user",
    "auth_group",
    "auth_permission",
    "auth_group_permissions",
    "auth_user_groups",
    "auth_user_user_permissions",
    "clients_client",
    "clients_clientphonenumber",
    "couriers_courierroute",
    "django_admin_log",
    "django_content_type",
    "django_migrations",
    "orders_order",
    "products_product",
]


def auth_user_needs_fix(cur):
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='auth_user'")
    row = cur.fetchone()
    if not row:
        return False
    return "AUTOINCREMENT" not in (row[0] or "").upper()


def fix_auth_user(cur):
    if not auth_user_needs_fix(cur):
        return False

    cur.executescript(
        """
        CREATE TABLE "auth_user_fixed" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "password" varchar(128) NOT NULL,
            "last_login" datetime NULL,
            "is_superuser" bool NOT NULL,
            "username" varchar(150) NOT NULL UNIQUE,
            "first_name" varchar(150) NOT NULL,
            "last_name" varchar(150) NOT NULL,
            "email" varchar(254) NOT NULL,
            "is_staff" bool NOT NULL,
            "is_active" bool NOT NULL,
            "date_joined" datetime NOT NULL
        );
        INSERT INTO auth_user_fixed (
            id, password, last_login, is_superuser, username, first_name, last_name,
            email, is_staff, is_active, date_joined
        )
        SELECT
            id, password, last_login, is_superuser, username, first_name, last_name,
            email, is_staff, is_active, date_joined
        FROM auth_user;
        DROP TABLE auth_user;
        ALTER TABLE auth_user_fixed RENAME TO auth_user;
        """
    )
    return True


def refresh_sqlite_sequences(cur):
    for table in SEQUENCE_TABLES:
        try:
            cur.execute(f"SELECT MAX(id) FROM {table}")
            max_id = cur.fetchone()[0]
            if max_id is not None:
                cur.execute(
                    "INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                    (table, max_id),
                )
        except sqlite3.OperationalError:
            pass


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else TARGET_DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")

    fixed = fix_auth_user(cur)
    refresh_sqlite_sequences(cur)

    cur.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    conn.close()

    if fixed:
        print(f"{db_path}: auth_user autoincrement tuzatildi.")
    else:
        print(f"{db_path}: auth_user allaqachon to'g'ri.")
    print("sqlite_sequence yangilandi.")


if __name__ == "__main__":
    main()