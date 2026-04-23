"""
Script A — Face Enrollment
Extracts a 128-d face encoding from an image and saves the user's
profile into the PostgreSQL database.

Usage (inside the virtual environment):
    python enroll_face.py \
        --image photos/john.jpg \
        --name "John Doe" \
        --national-id "NID-123456" \
        --employee-id "EMP-001" \
        --designation "Software Engineer" \
        --department "Engineering" \
        --dob "1995-06-15" \
        --gender "Male" \
        --blood-group "O+" \
        --phone "+8801700000000" \
        --email "john@example.com" \
        --address "123 Main St, Dhaka" \
        --emergency-name "Jane Doe" \
        --emergency-phone "+8801711111111"
"""

import argparse
import os
import shutil
import sys

import face_recognition
import numpy as np

from db_config import get_connection

# Directory where profile photos are stored
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")


def ensure_photo_dir():
    """Create the photos directory if it doesn't exist."""
    os.makedirs(PHOTO_DIR, exist_ok=True)


def extract_encoding(image_path: str) -> np.ndarray:
    """Load an image and return the 128-d face encoding."""
    if not os.path.isfile(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        print("[ERROR] No face detected in the image. Please use a clear photo.")
        sys.exit(1)

    if len(encodings) > 1:
        print(f"[WARNING] {len(encodings)} faces detected. Using the first one.")

    return encodings[0]


def save_photo(image_path: str, employee_id: str) -> str:
    """Copy the photo to the photos/ directory and return the saved path."""
    ensure_photo_dir()
    ext = os.path.splitext(image_path)[1] or ".jpg"
    safe_name = (employee_id or "unknown").replace(" ", "_")
    dest = os.path.join(PHOTO_DIR, f"{safe_name}{ext}")
    shutil.copy2(image_path, dest)
    return dest


def enroll_user(args):
    """Insert the user profile and face encoding into the database."""
    print(f"\n{'='*50}")
    print("  FACE ENROLLMENT SYSTEM")
    print(f"{'='*50}\n")

    # --- Step 1: Extract face encoding ---
    print("[1/3] Extracting face encoding ...")
    encoding = extract_encoding(args.image)
    print(f"      ✓ Encoding extracted ({len(encoding)}-d vector)")

    # --- Step 2: Save photo ---
    print("[2/3] Saving profile photo ...")
    photo_path = save_photo(args.image, args.employee_id or args.name)
    print(f"      ✓ Photo saved to {photo_path}")

    # --- Step 3: Insert into database ---
    print("[3/3] Saving to database ...")
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO user_profiles (
                full_name, date_of_birth, gender, blood_group,
                national_id, employee_id,
                designation, department,
                phone, email, address,
                emergency_contact_name, emergency_contact_phone,
                profile_photo_path, face_encoding
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s
            )
            RETURNING id;
            """,
            (
                args.name,
                args.dob or None,
                args.gender,
                args.blood_group,
                args.national_id,
                args.employee_id,
                args.designation,
                args.department,
                args.phone,
                args.email,
                args.address,
                args.emergency_name,
                args.emergency_phone,
                photo_path,
                encoding.tolist(),
            ),
        )

        user_id = cur.fetchone()[0]
        conn.commit()

        print(f"      ✓ User enrolled with ID: {user_id}")
        print(f"\n{'='*50}")
        print(f"  ✅  {args.name} enrolled successfully!")
        print(f"{'='*50}\n")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n[ERROR] Database error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Enroll a face into the recognition database."
    )

    # Required
    parser.add_argument("--image", required=True, help="Path to the face image")
    parser.add_argument("--name", required=True, help="Full name of the person")

    # ID Card Info
    parser.add_argument("--national-id", default=None, help="National ID number")
    parser.add_argument("--employee-id", default=None, help="Employee ID")

    # Organization
    parser.add_argument("--designation", default=None, help="Job designation / title")
    parser.add_argument("--department", default=None, help="Department name")

    # Personal
    parser.add_argument("--dob", default=None, help="Date of birth (YYYY-MM-DD)")
    parser.add_argument("--gender", default=None, help="Gender")
    parser.add_argument("--blood-group", default=None, help="Blood group (e.g. O+)")

    # Contact
    parser.add_argument("--phone", default=None, help="Phone number")
    parser.add_argument("--email", default=None, help="Email address")
    parser.add_argument("--address", default=None, help="Physical address")

    # Emergency
    parser.add_argument("--emergency-name", default=None, help="Emergency contact name")
    parser.add_argument("--emergency-phone", default=None, help="Emergency contact phone")

    args = parser.parse_args()
    enroll_user(args)


if __name__ == "__main__":
    main()
