import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from db_config import DB_CONFIG

def create_db():
    # Connect to the default 'postgres' database to create the new one
    conn_params = DB_CONFIG.copy()
    db_name = conn_params.pop('dbname')
    conn_params['dbname'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        if cur.fetchone():
            print(f"Database '{db_name}' already exists.")
        else:
            print(f"Creating database '{db_name}'...")
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created successfully.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

def create_tables():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("Reading schema.sql...")
        with open('schema.sql', 'r') as f:
            schema_sql = f.read()
            
        print("Executing schema.sql...")
        cur.execute(schema_sql)
        conn.commit()
        print("Tables created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_db()
    create_tables()
