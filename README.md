# 🔍 Real-Time Face Recognition & Security Alert System

A high-speed security system powered by **OpenCV**, **face_recognition (dlib)**, **YOLOv8** (Weapon Detection), and **PostgreSQL**, with automated WhatsApp alerts.

---

## ✨ Features
- **Real-Time Face Recognition**: High-speed matching using `dlib` and PostgreSQL.
- **Weapon Detection**: YOLOv8 integration to detect threats (e.g., guns, knives).
- **Automated WhatsApp Alerts**: Instant background alerts via CallMeBot API with suspect details and threat level.
- **Professional UI Overlay**: Futuristic HUD with profile cards, threat banners, and status tracking.
- **Secure Configuration**: Environment variables for sensitive keys and credentials.

---

## 📁 Project Structure

```
├── requirements.txt          # Python dependencies
├── schema.sql                # PostgreSQL table creation
├── db_config.py              # Database connection config
├── enroll_face.py            # Script A: Enroll a user's face
├── recognize_faces.py        # Script B: Real-time webcam recognition
├── photos/                   # Stored profile photos (auto-created)
└── README.md                 # This file
```

---

## ⚙️ Prerequisites

1. **Python 3.8+** installed
2. **PostgreSQL** installed and running
3. **CMake** installed (`winget install Kitware.CMake` or download from [cmake.org](https://cmake.org/download/))
4. **Visual Studio Build Tools** with C++ workload (required by `dlib`)
   - Download from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Select "Desktop development with C++" during installation
5. A working **webcam**

---

## 🚀 Setup Instructions

### 1. Create a Virtual Environment (Local Install)

Open a terminal in the project folder:

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)


# Activate it (Linux / macOS)
# source venv/bin/activate
```

> ⚠️ **All commands below must be run with the virtual environment activated.**

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> If `face_recognition` fails to install, ensure CMake and C++ Build Tools are properly installed.

### 3. Set Up the PostgreSQL Database

Open `psql` or pgAdmin and run:

```sql
-- Create the database
CREATE DATABASE face_recognition_db;

-- Connect to it
\c face_recognition_db

-- Run the schema file
\i schema.sql
```

Or from the terminal:

```bash
psql -U postgres -c "CREATE DATABASE face_recognition_db;"
psql -U postgres -d face_recognition_db -f schema.sql
```

### 4. Setup Database and WhatsApp Credentials

Create a `.env` file in the root directory and add your database and API credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=face_recognition_db
DB_USER=postgres
DB_PASSWORD=your_password_here

ALERT_PHONE_NUMBER=+1234567890
CALLMEBOT_API_KEY=your_api_key_here
```

**How to get your CallMeBot API Key:**
1. Add the phone number `+34 624 54 81 55` to your contacts.
2. Send the message `"I allow callmebot to send me messages"` to that number via WhatsApp.
3. The bot will reply with your API Key. Paste it into your `.env` file!

---

## 👤 Script A: Enroll a Face

Enroll a person by providing their photo and profile details:

```bash
python enroll_face.py \
    --image path/to/photo.jpg \
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
```

**Required arguments:** `--image` and `--name`
**All other arguments are optional.**

### Minimal enrollment:

```bash
python enroll_face.py --image photo.jpg --name "John Doe"
```

---

## 📹 Script B: Real-Time Recognition

Start the webcam-based recognition system:

```bash
python recognize_faces.py
```

### What you'll see:

| Scenario | Visual |
|---|---|
| **Known face** | Cyan/green tech-style bounding box + floating profile card |
| **Unknown face** | Red bounding box + "ACCESS DENIED" banner |

### Controls:
- Press **`q`** to quit

### Performance optimizations:
- Frame resized to 25% for fast processing
- Every other frame is processed
- Targets 30+ FPS

---

## 🗄️ Database Schema

| Column | Type | Description |
|---|---|---|
| `id` | SERIAL (PK) | Auto-increment ID |
| `full_name` | VARCHAR(150) | Person's full name |
| `date_of_birth` | DATE | Date of birth |
| `gender` | VARCHAR(20) | Gender |
| `blood_group` | VARCHAR(10) | Blood group |
| `national_id` | VARCHAR(50) | National ID (unique) |
| `employee_id` | VARCHAR(50) | Employee ID (unique) |
| `designation` | VARCHAR(100) | Job title |
| `department` | VARCHAR(100) | Department |
| `phone` | VARCHAR(20) | Phone number |
| `email` | VARCHAR(150) | Email address |
| `address` | TEXT | Physical address |
| `emergency_contact_name` | VARCHAR(150) | Emergency contact |
| `emergency_contact_phone` | VARCHAR(20) | Emergency phone |
| `profile_photo_path` | TEXT | Path to stored photo |
| `face_encoding` | DOUBLE PRECISION[] | 128-d face vector |
| `created_at` | TIMESTAMP | Record creation time |
| `updated_at` | TIMESTAMP | Last update time |

---

## 🛑 Troubleshooting

| Issue | Solution |
|---|---|
| `dlib` won't install | Install CMake + Visual Studio C++ Build Tools |
| No face detected | Use a clear, well-lit photo with one visible face |
| Webcam not opening | Check if another app is using the camera |
| DB connection error | Verify credentials in your `.env` file and ensure PostgreSQL is running |
| Low FPS | Decrease `RESIZE_FACTOR` or increase `PROCESS_EVERY_N_FRAMES` in `recognize_faces.py` |
