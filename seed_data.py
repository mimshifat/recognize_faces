import face_recognition
import psycopg2
import os
from db_config import DB_CONFIG

def get_face_encoding(image_path):
    print(f"Loading image from {image_path}...")
    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        print("No face found in image.")
        return None
    return encodings[0].tolist()

def seed_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # User 1: Shifat
    img_path = 'Shifat.png'
    encoding = get_face_encoding(img_path)
    
    if encoding:
        print("Inserting Shifat's profile...")
        cur.execute("""
            INSERT INTO user_profiles (
                full_name, date_of_birth, gender, blood_group, nationality,
                national_id, phone, email, address, profile_photo_path, face_encoding
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, (
            'Md Mim Shifat', '2003-04-14', 'Male', 'B+', 'Bangladeshi',
            '1234567890', '+1234567890', 'dummy.email@example.com', 'Rajshahi, Bangladesh', 
            img_path, encoding
        ))
    
    # Demo User 2
    print("Inserting Demo User 1...")
    cur.execute("""
        INSERT INTO user_profiles (
            full_name, date_of_birth, blood_group, 
            phone, email, address, face_encoding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING
    """, (
        'Jane Doe', '1995-10-20', 'O-', 
        '+123456789', 'jane.doe@example.com', '123 Demo St, City', 
        [0.1]*128
    ))
    
    # Demo User 3
    print("Inserting Demo User 2...")
    cur.execute("""
        INSERT INTO user_profiles (
            full_name, date_of_birth, blood_group, 
            phone, email, address, face_encoding
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (email) DO NOTHING
    """, (
        'John Smith', '1988-05-12', 'A+', 
        '+987654321', 'john.smith@example.com', '456 Test Ave, Town', 
        [0.2]*128
    ))
    
    conn.commit()
    print("Data seeding completed.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    seed_data()
