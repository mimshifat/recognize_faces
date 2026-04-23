import cv2
import face_recognition
import numpy as np
import os
from recognize_faces import load_known_faces

def test_on_image(image_path):
    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        return

    print(f"\n--- Testing Recognition Logic ---")
    print(f"Image Source: {image_path}")
    
    # Load known faces from your database
    known_encodings, known_profiles = load_known_faces()
    
    if not known_encodings:
        print("[ERROR] No faces enrolled in the database. Run seed_data.py first.")
        return

    # Load and process test image
    print("[INFO] Processing image and generating encodings...")
    image = face_recognition.load_image_file(image_path)
    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    print(f"[INFO] Faces detected in image: {len(face_encodings)}")
    
    for i, enc in enumerate(face_encodings):
        distances = face_recognition.face_distance(known_encodings, enc)
        best_idx = np.argmin(distances)
        
        # Use the same tolerance (0.5) as the main project
        if distances[best_idx] <= 0.5:
            profile = known_profiles[best_idx]
            print(f"| Face {i+1}: [MATCH FOUND] -> {profile['full_name']} (ID: {profile['id']})")
            print(f"| Confidence Score (Distance): {distances[best_idx]:.4f}")
        else:
            print(f"| Face {i+1}: [UNKNOWN]")

if __name__ == "__main__":
    # Test using the Shifat.png image you provided
    test_on_image("Shifat.png")
