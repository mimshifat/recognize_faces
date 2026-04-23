import cv2

def test_webcam_indices(max_indices=5):
    print("--- Checking Webcam Indices ---")
    for i in range(max_indices):
        print(f"Testing Index {i}...", end=" ")
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) # Try DirectShow for better compatibility on Windows
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"SUCCESS! (Index {i})")
                cap.release()
                return i
            else:
                print("Opened but failed to read frame.")
            cap.release()
        else:
            print("Failed to open.")
    return None

if __name__ == "__main__":
    found_index = test_webcam_indices()
    if found_index is not None:
        print(f"\nFinal Result: Use Index {found_index}")
    else:
        print("\nFinal Result: No working webcam found.")
