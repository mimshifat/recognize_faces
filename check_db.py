import psycopg2
from db_config import DB_CONFIG

def check_table():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_profiles');")
        exists = cur.fetchone()[0]
        print(f"Table 'user_profiles' exists: {exists}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_table()
