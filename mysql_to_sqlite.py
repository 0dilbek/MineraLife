import re
import sqlite3
import os

INPUT_SQL = "db-backup-june.sql"
OUTPUT_DB = "zahira.db"

def convert_mysql_to_sqlite(sql):
    lines = sql.splitlines()
    result = []

    for line in lines:
        # MySQL maxsus kommentlarni o'chirish /*!...*/
        line = re.sub(r'/\*![^*]*\*/', '', line)
        line = re.sub(r'/\*!.*?\*/', '', line)

        # Bo'sh komment qoldiqlari
        if line.strip() in ('', ';'):
            continue

        # MySQL-only statements
        skip_patterns = [
            r'^\s*LOCK TABLES',
            r'^\s*UNLOCK TABLES',
            r'^\s*SET @',
            r'^\s*SET NAMES',
            r'^\s*SET TIME_ZONE',
        ]
        if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
            continue

        result.append(line)

    sql_out = '\n'.join(result)

    # ENGINE=... DEFAULT CHARSET=... ni o'chirish
    sql_out = re.sub(
        r'\)\s*ENGINE\s*=\s*\w+[^;]*;',
        ');',
        sql_out,
        flags=re.IGNORECASE
    )

    # AUTO_INCREMENT column definition ichida
    sql_out = re.sub(r'\bAUTO_INCREMENT\b', '', sql_out, flags=re.IGNORECASE)
    sql_out = re.sub(r'\bAUTO_INCREMENT\s*=\s*\d+', '', sql_out, flags=re.IGNORECASE)

    # DEFAULT CHARSET / COLLATE column darajasida
    sql_out = re.sub(r'\bCHARACTER SET\s+\w+', '', sql_out, flags=re.IGNORECASE)
    sql_out = re.sub(r'\bCOLLATE\s+\w+', '', sql_out, flags=re.IGNORECASE)
    sql_out = re.sub(r'\bDEFAULT CHARSET\s*=\s*\w+', '', sql_out, flags=re.IGNORECASE)

    # tinyint(1) → INTEGER
    sql_out = re.sub(r'\btinyint\(\d+\)', 'INTEGER', sql_out, flags=re.IGNORECASE)

    # bigint(N) / int(N) → INTEGER
    sql_out = re.sub(r'\bbigint\b', 'INTEGER', sql_out, flags=re.IGNORECASE)
    sql_out = re.sub(r'\bint\(\d+\)', 'INTEGER', sql_out, flags=re.IGNORECASE)

    # datetime(6) → TEXT
    sql_out = re.sub(r'\bdatetime\(\d+\)', 'TEXT', sql_out, flags=re.IGNORECASE)
    sql_out = re.sub(r'\bdatetime\b', 'TEXT', sql_out, flags=re.IGNORECASE)

    # CREATE TABLE ichidagi KEY/UNIQUE KEY larni to'g'rilash
    sql_out = convert_create_tables(sql_out)

    # MySQL backslash escape (\') → SQLite double quote escape ('')
    sql_out = convert_string_escapes(sql_out)

    return sql_out


def convert_string_escapes(sql):
    """MySQL string ichidagi \' ni '' ga o'zgartirish (SQLite uchun)"""
    result = []
    i = 0
    while i < len(sql):
        c = sql[i]
        if c == "'":
            result.append(c)
            i += 1
            # String ichiga kirdik
            while i < len(sql):
                c2 = sql[i]
                if c2 == '\\' and i + 1 < len(sql) and sql[i+1] == "'":
                    # \' → ''
                    result.append("''")
                    i += 2
                elif c2 == '\\' and i + 1 < len(sql):
                    # boshqa escape (\n, \t va h.k.) — qoldirish
                    result.append(c2)
                    result.append(sql[i+1])
                    i += 2
                elif c2 == "'":
                    result.append(c2)
                    i += 1
                    break
                else:
                    result.append(c2)
                    i += 1
        else:
            result.append(c)
            i += 1
    return ''.join(result)


def convert_create_tables(sql):
    def fix_table(match):
        create_part = match.group(1)
        body = match.group(2)
        close = match.group(3)

        lines = body.split('\n')
        new_lines = []
        for line in lines:
            # UNIQUE KEY `keyname` (col1, col2) → UNIQUE (col1, col2)
            m = re.match(r'(\s*)UNIQUE KEY\s+`\w+`\s*(\([^)]+\))(,?)', line, re.IGNORECASE)
            if m:
                new_lines.append(f'{m.group(1)}UNIQUE {m.group(2)}{m.group(3)}')
                continue

            # KEY `keyname` (col) — oddiy index, o'chiramiz
            if re.match(r'\s*KEY\s+`', line, re.IGNORECASE):
                # Oldingi qatordan trailing comma olib tashlash kerak bo'lishi mumkin
                # Keyinroq fix_trailing_commas hal qiladi
                continue

            new_lines.append(line)

        cleaned = fix_trailing_commas(new_lines)
        return create_part + '\n'.join(cleaned) + close

    pattern = re.compile(
        r'(CREATE TABLE[^(]+\()\n(.*?)\n(\s*\)\s*;)',
        re.DOTALL | re.IGNORECASE
    )
    return pattern.sub(fix_table, sql)


def fix_trailing_commas(lines):
    non_empty = [(i, l) for i, l in enumerate(lines) if l.strip()]
    if not non_empty:
        return lines

    last_idx = non_empty[-1][0]
    last_line = lines[last_idx]

    if last_line.rstrip().endswith(','):
        lines[last_idx] = last_line.rstrip()[:-1]

    return lines


def split_sql_statements(sql):
    statements = []
    current = []
    in_string = False
    string_char = None
    i = 0

    while i < len(sql):
        c = sql[i]

        if in_string:
            current.append(c)
            if c == '\\':
                i += 1
                if i < len(sql):
                    current.append(sql[i])
            elif c == string_char:
                in_string = False
        else:
            if c in ("'", '"', '`'):
                in_string = True
                string_char = c
                current.append(c)
            elif c == '-' and i + 1 < len(sql) and sql[i+1] == '-':
                while i < len(sql) and sql[i] != '\n':
                    i += 1
                continue
            elif c == ';':
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(c)
        i += 1

    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


def run():
    print(f"O'qilmoqda: {INPUT_SQL}")
    with open(INPUT_SQL, 'r', encoding='utf-8') as f:
        mysql_sql = f.read()

    print("Konvertatsiya qilinmoqda...")
    sqlite_sql = convert_mysql_to_sqlite(mysql_sql)

    with open('converted.sql', 'w', encoding='utf-8') as f:
        f.write(sqlite_sql)
    print("Converted SQL saqlandi: converted.sql")

    if os.path.exists(OUTPUT_DB):
        os.remove(OUTPUT_DB)
        print(f"Eski {OUTPUT_DB} o'chirildi")

    print(f"SQLite DB yaratilmoqda: {OUTPUT_DB}")
    conn = sqlite3.connect(OUTPUT_DB)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = OFF;")

    statements = split_sql_statements(sqlite_sql)
    errors = []
    success = 0

    for i, stmt in enumerate(statements):
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
            success += 1
        except Exception as e:
            errors.append((i, stmt[:120], str(e)))

    conn.commit()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Jadvallar ro'yxati
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()

    conn.close()

    print(f"\nNatija: {success} statement muvaffaqiyatli bajarildi")
    if errors:
        print(f"\n{len(errors)} ta xato:")
        for i, stmt, err in errors[:15]:
            print(f"  [{i}] {stmt!r}... => {err}")
    else:
        print("Xatolar yo'q!")

    print(f"\nJadvallar ({len(tables)} ta):")
    for t in tables:
        print(f"  - {t[0]}")

    print(f"\nDB fayl tayyor: {OUTPUT_DB}")


if __name__ == '__main__':
    run()
