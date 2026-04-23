import psycopg2
from db_config import DB_CONFIG

def verify():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT id, full_name, email, gender, national_id, date_of_birth, blood_group FROM user_profiles;")
    rows = cur.fetchall()
    
    print(f"Total profiles in database: {len(rows)}")
    for row in rows:
        print(f"ID: {row[0]} | Name: {row[1]} | Email: {row[2]} | Gender: {row[3]} | NID: {row[4]} | DOB: {row[5]} | Blood: {row[6]}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    verify()
