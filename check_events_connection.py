import psycopg2

DB_CONFIG = {
    "host": "217.198.83.165",
    "port": 9030,
    "database": "vsm_service_trains",
    "user": "tmp",
    "password": "ngqU-5Gk9J"
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("Checking message code mapping")
print("=" * 60)

print("\n1. Sample message codes from velaro_events:")
try:
    cur.execute("SELECT DISTINCT messagecode FROM velaro_events LIMIT 10;")
    codes = cur.fetchall()
    for code in codes:
        print(f"   {code[0]}")
except Exception as e:
    print(f"   Error: {e}")

print("\n2. Sample name_or_code from master_data:")
try:
    cur.execute("""
        SELECT name_or_code, description_ru 
        FROM master_data 
        WHERE entry_type = 'Message' 
        LIMIT 10;
    """)
    master_codes = cur.fetchall()
    for row in master_codes:
        desc = row[1][:40] if row[1] else 'NULL'
        print(f"   {row[0]} -> {desc}")
except Exception as e:
    print(f"   Error: {e}")

print("\n3. Checking specific code '0072':")
try:
    cur.execute("""
        SELECT name_or_code, description_ru 
        FROM master_data 
        WHERE name_or_code = '0072' AND entry_type = 'Message';
    """)
    result = cur.fetchall()
    if result:
        print(f"   Found: {result[0][0]} -> {result[0][1]}")
    else:
        print("   Not found as exact match")

        # Пробуем найти без ведущих нулей
        cur.execute("""
            SELECT name_or_code, description_ru 
            FROM master_data 
            WHERE name_or_code = '72' AND entry_type = 'Message';
        """)
        result = cur.fetchall()
        if result:
            print(f"   Found as '72': {result[0][0]} -> {result[0][1]}")
        else:
            print("   Not found as '72' either")
except Exception as e:
    print(f"   Error: {e}")

print("\n4. Looking for any hex codes in master_data:")
try:
    cur.execute("""
        SELECT name_or_code, description_ru 
        FROM master_data 
        WHERE name_or_code ~ '^[0-9A-F]{4}$' 
        AND entry_type = 'Message'
        LIMIT 10;
    """)
    hex_codes = cur.fetchall()
    if hex_codes:
        print("   Found hex codes:")
        for row in hex_codes:
            desc = row[1][:40] if row[1] else 'NULL'
            print(f"      {row[0]} -> {desc}")
    else:
        print("   No hex format codes found")
except Exception as e:
    print(f"   Error: {e}")

cur.close()
conn.close()