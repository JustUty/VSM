import psycopg2
from psycopg2 import sql

DB_CONFIG = {
    "host": "217.198.83.165",
    "port": 9030,
    "database": "vsm_service_trains",
    "user": "tmp",
    "password": "ngqU-5Gk9J"
}


def inspect_table(conn, table_name):
    cur = conn.cursor()

    print(f"\n{'=' * 80}")
    print(f"TABLE: {table_name}")
    print('=' * 80)

    try:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table_name,))

        columns = cur.fetchall()

        if not columns:
            print(f"Table '{table_name}' not found or has no columns")
            return

        print("\nCOLUMN STRUCTURE:")
        print("-" * 50)
        for col in columns:
            col_name = col[0]
            col_type = col[1]
            nullable = "YES" if col[2] == "YES" else "NO"
            print(f"   {col_name:<30} {col_type:<20} (nullable: {nullable})")

        cur.execute(sql.SQL('SELECT COUNT(*) FROM {};').format(sql.Identifier(table_name)))
        count = cur.fetchone()[0]
        print(f"\nTotal rows: {count:,}")

        if count > 0:
            cur.execute(sql.SQL('SELECT * FROM {} LIMIT 5;').format(sql.Identifier(table_name)))
            rows = cur.fetchall()

            print("\nSAMPLE DATA (first 5 rows):")
            print("-" * 50)

            col_names = [col[0] for col in columns]

            for i, row in enumerate(rows, 1):
                print(f"\n   Row {i}:")
                for j, col_name in enumerate(col_names):
                    if j < len(row):
                        val = row[j]
                        if val is not None:
                            val_str = str(val)
                            if len(val_str) > 80:
                                val_str = val_str[:77] + "..."
                            print(f"      {col_name:<30} = {val_str}")
                        else:
                            print(f"      {col_name:<30} = NULL")
        else:
            print("\nTable is empty")

    except psycopg2.Error as e:
        print(f"Error inspecting table '{table_name}': {e}")

    cur.close()


def show_trains_list(conn):
    cur = conn.cursor()

    print(f"\n{'=' * 80}")
    print("TRAINS LIST (table 'trains')")
    print('=' * 80)

    try:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'trains' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)

        columns = cur.fetchall()
        print("\nTable 'trains' structure:")
        for col in columns:
            print(f"   {col[0]}: {col[1]}")

        cur.execute('SELECT * FROM "trains" LIMIT 30;')
        rows = cur.fetchall()

        if rows:
            print(f"\nTrains found (first 30):")
            col_names = [col[0] for col in columns]

            for i, row in enumerate(rows, 1):
                print(f"\n   Train #{i}:")
                for j, col_name in enumerate(col_names):
                    if j < len(row):
                        val = row[j]
                        if val is not None:
                            print(f"      {col_name}: {val}")
                        else:
                            print(f"      {col_name}: NULL")
        else:
            print("\nTable 'trains' is empty")

    except psycopg2.Error as e:
        print(f"Error getting trains list: {e}")

    cur.close()


def show_events_sample(conn, table_name):
    cur = conn.cursor()

    print(f"\n{'=' * 80}")
    print(f"EVENTS SAMPLE FROM '{table_name}'")
    print('=' * 80)

    try:
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table_name,))

        columns = cur.fetchall()
        print("\nTable structure:")
        for col in columns:
            print(f"   {col[0]}: {col[1]}")

        possible_train_fields = ['train_id', 'zugnr', 'train_number', 'train_no', 'trip_nr']
        train_field = None

        for col in columns:
            if col[0].lower() in possible_train_fields or 'train' in col[0].lower():
                train_field = col[0]
                break

        if train_field:
            print(f"\nFound train number field: '{train_field}'")

            cur.execute(sql.SQL('SELECT DISTINCT {} FROM "{}" LIMIT 10;').format(
                sql.Identifier(train_field),
                sql.Identifier(table_name)
            ))
            train_numbers = cur.fetchall()

            if train_numbers:
                print(f"\nUnique train numbers (first 10):")
                for tn in train_numbers:
                    print(f"   - {tn[0]}")

                first_train = train_numbers[0][0]
                print(f"\nSample events for train {first_train} (first 3):")

                cur.execute(sql.SQL('''
                    SELECT * FROM "{}" 
                    WHERE {} = %s 
                    LIMIT 3;
                ''').format(sql.Identifier(table_name), sql.Identifier(train_field)), (first_train,))

                events = cur.fetchall()
                col_names = [col[0] for col in columns]

                for i, event in enumerate(events, 1):
                    print(f"\n   Event {i}:")
                    for j, col_name in enumerate(col_names):
                        if j < len(event):
                            val = event[j]
                            if val is not None:
                                val_str = str(val)[:60]
                                print(f"      {col_name}: {val_str}")
            else:
                print("No train number data found")
        else:
            print("\nNo train number field found")

    except psycopg2.Error as e:
        print(f"Error viewing events: {e}")

    cur.close()


def main():
    try:
        print("Connecting to database...")
        print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"   Database: {DB_CONFIG['database']}")
        print(f"   User: {DB_CONFIG['user']}")

        conn = psycopg2.connect(**DB_CONFIG)
        print("Connection successful\n")

        tables_to_inspect = [
            "trains",
            "events",
            "velaro_events",
            "master_data",
            "sensors"
        ]

        for table in tables_to_inspect:
            inspect_table(conn, table)

        show_trains_list(conn)

        if "events" in tables_to_inspect:
            show_events_sample(conn, "events")

        if "velaro_events" in tables_to_inspect:
            show_events_sample(conn, "velaro_events")

        conn.close()
        print(f"\n{'=' * 80}")
        print("Analysis complete")
        print('=' * 80)

    except psycopg2.OperationalError as e:
        print(f"\nDatabase connection error:")
        print(f"   {e}")
        print("\nPossible reasons:")
        print("   - Incorrect host or port")
        print("   - Incorrect login or password")
        print("   - Database unavailable (check VPN/network)")
        print("   - Firewall blocking connection")
    except Exception as e:
        print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    main()