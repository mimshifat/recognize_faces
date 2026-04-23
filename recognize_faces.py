"""
Script B — Real-Time Face Recognition (Professional UI)
Opens the webcam, loads known face encodings from PostgreSQL, and performs
real-time face matching with a sleek, modern overlay UI.

Usage (inside the virtual environment):
    python recognize_faces.py

Press 'q' to quit.
"""

import math
import time

import cv2
import numpy as np
import face_recognition
import mediapipe as mp

from db_config import get_connection
from weapon_detector import WeaponDetector
from whatsapp_alert import WhatsAppAlerter

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
RESIZE_FACTOR = 0.25            # Scale down for speed (0.25 = 25%)
TOLERANCE = 0.50                # Face match tolerance (lower = stricter)
PROCESS_EVERY_N_FRAMES = 3     # Skip frames for performance (increased from 2)
WEAPON_EVERY_N_FRAMES = 6      # Run weapon detection less often (every 6th frame)
CARD_WIDTH = 320                # Profile card width in pixels
CARD_ALPHA = 0.85               # Card background transparency
GLOW_INTENSITY = 0.4            # Glow effect intensity
VIRTUAL_BG_PATH = "background.jpg" # Path to the default background image

# ──────────────────────────────────────────────
# COLOR PALETTE  (BGR)
# ──────────────────────────────────────────────
# -- Accent / Verified
CLR_NEON_CYAN   = (255, 255, 0)
CLR_NEON_GREEN  = (0, 255, 160)
CLR_TEAL        = (200, 200, 0)
CLR_AQUA_GLOW   = (200, 200, 0)

# -- Denied
CLR_NEON_RED    = (80, 80, 255)
CLR_RED_GLOW    = (60, 60, 200)
CLR_DARK_RED    = (30, 30, 140)

# -- Neutrals
CLR_WHITE       = (255, 255, 255)
CLR_LIGHT_GRAY  = (200, 200, 200)
CLR_MID_GRAY    = (140, 140, 140)
CLR_DARK        = (30, 30, 30)
CLR_DARKER      = (20, 20, 20)
CLR_PANEL_BG    = (35, 35, 40)
CLR_HEADER_BG   = (45, 45, 55)

# -- Labels
CLR_LABEL       = (180, 160, 100)
CLR_VALUE       = (240, 240, 240)
CLR_ACCENT_BAR  = (255, 200, 50)


# ──────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────
def load_known_faces():
    """Fetch all user profiles and face encodings from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, full_name, date_of_birth, gender, blood_group, nationality,
               phone, email, address, profile_photo_path, face_encoding
        FROM user_profiles ORDER BY id;
        """
    )
    rows = cur.fetchall()
    conn.close()

    encodings, profiles = [], []
    for row in rows:
        encodings.append(np.array(row[10], dtype=np.float64))
        profiles.append({
            "id": row[0],
            "full_name": row[1],
            "dob": str(row[2]) if row[2] else "N/A",
            "gender": row[3] or "N/A",
            "blood_group": row[4] or "N/A",
            "nationality": row[5] or "N/A",
            "phone": row[6] or "N/A",
            "email": row[7] or "N/A",
            "address": row[8] or "N/A",
            "photo_path": row[9],
        })
    print(f"[INFO] Loaded {len(encodings)} known face(s) from database.")
    return encodings, profiles


# ──────────────────────────────────────────────
# UI DRAWING UTILITIES
# ──────────────────────────────────────────────

def _overlay_rect(frame, pt1, pt2, color, alpha):
    """Draw a semi-transparent filled rectangle (ROI-optimized)."""
    fh, fw = frame.shape[:2]
    x1 = max(0, pt1[0])
    y1 = max(0, pt1[1])
    x2 = min(fw, pt2[0])
    y2 = min(fh, pt2[1])
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    rect = np.full_like(roi, color, dtype=np.uint8)
    cv2.addWeighted(rect, alpha, roi, 1 - alpha, 0, roi)
    frame[y1:y2, x1:x2] = roi


def _rounded_rect(frame, pt1, pt2, color, radius, thickness=-1, alpha=1.0):
    """Draw a rectangle with rounded corners (filled or outline)."""
    x1, y1 = pt1
    x2, y2 = pt2
    r = min(radius, (x2 - x1) // 2, (y2 - y1) // 2)

    if alpha < 1.0 and thickness == -1:
        canvas = frame.copy()
    else:
        canvas = frame

    # Corners
    cv2.ellipse(canvas, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
    cv2.ellipse(canvas, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
    cv2.ellipse(canvas, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)
    cv2.ellipse(canvas, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)

    if thickness == -1:
        # Filled inside
        cv2.rectangle(canvas, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(canvas, (x1, y1 + r), (x1 + r, y2 - r), color, -1)
        cv2.rectangle(canvas, (x2 - r, y1 + r), (x2, y2 - r), color, -1)
    else:
        # Outline edges
        cv2.line(canvas, (x1 + r, y1), (x2 - r, y1), color, thickness)
        cv2.line(canvas, (x1 + r, y2), (x2 - r, y2), color, thickness)
        cv2.line(canvas, (x1, y1 + r), (x1, y2 - r), color, thickness)
        cv2.line(canvas, (x2, y1 + r), (x2, y2 - r), color, thickness)

    if alpha < 1.0 and thickness == -1:
        cv2.addWeighted(canvas, alpha, frame, 1 - alpha, 0, frame)


def _draw_glow_line(frame, pt1, pt2, color, thickness=2, glow_size=8):
    """Draw a line with a subtle glow (optimized — no frame copies)."""
    glow_color = tuple(max(0, int(c * GLOW_INTENSITY)) for c in color)
    # Single wider line instead of 4 blended copies
    cv2.line(frame, pt1, pt2, glow_color, thickness + 3)
    cv2.line(frame, pt1, pt2, color, thickness)


# ──────────────────────────────────────────────
# FACE BOUNDING BOX
# ──────────────────────────────────────────────

def draw_face_frame(frame, top, right, bottom, left, color, pulse_phase):
    """
    Draw a futuristic scanning frame around the face.
    Includes corner brackets, edge dots, and a pulsing scan-line.
    """
    h = bottom - top
    w = right - left
    corner_len = max(15, min(35, h // 3, w // 3))
    t = 2  # thickness

    # ── Outer glow rectangle (very faint) ──
    pad = 4
    overlay = frame.copy()
    cv2.rectangle(overlay, (left - pad, top - pad),
                  (right + pad, bottom + pad), color, 1)
    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

    # ── Corner brackets ──
    corners = [
        # top-left
        ((left, top), (left + corner_len, top), (left, top + corner_len)),
        # top-right
        ((right, top), (right - corner_len, top), (right, top + corner_len)),
        # bottom-left
        ((left, bottom), (left + corner_len, bottom), (left, bottom - corner_len)),
        # bottom-right
        ((right, bottom), (right - corner_len, bottom), (right, bottom - corner_len)),
    ]
    for origin, h_end, v_end in corners:
        cv2.line(frame, origin, h_end, color, t + 1)
        cv2.line(frame, origin, v_end, color, t + 1)

    # ── Small dots at corners ──
    dot_r = 3
    for corner in [(left, top), (right, top), (left, bottom), (right, bottom)]:
        cv2.circle(frame, corner, dot_r, CLR_WHITE, -1)

    # ── Pulsing horizontal scan-line ──
    scan_y = int(top + (h * ((math.sin(pulse_phase) + 1) / 2)))
    scan_y = max(top + 2, min(bottom - 2, scan_y))
    overlay = frame.copy()
    cv2.line(overlay, (left + 5, scan_y), (right - 5, scan_y), color, 1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    # ── Tiny cross-hairs at mid edges ──
    mid_x = (left + right) // 2
    mid_y = (top + bottom) // 2
    ch = 5  # crosshair half-length
    cv2.line(frame, (mid_x - ch, top), (mid_x + ch, top), color, 1)
    cv2.line(frame, (mid_x - ch, bottom), (mid_x + ch, bottom), color, 1)
    cv2.line(frame, (left, mid_y - ch), (left, mid_y + ch), color, 1)
    cv2.line(frame, (right, mid_y - ch), (right, mid_y + ch), color, 1)


# ──────────────────────────────────────────────
# PROFILE CARD (KNOWN FACE — VERIFIED)
# ──────────────────────────────────────────────

def draw_profile_card(frame, top, right, bottom, left, profile, pulse_phase):
    """Draw a sleek, floating profile information card."""
    fh, fw = frame.shape[:2]

    # ── Card geometry ──
    card_w = CARD_WIDTH
    padding = 14
    line_h = 26
    header_h = 42
    divider_h = 2
    status_h = 28

    fields = [
        ("\u2022 DOB",       profile["dob"]),
        ("\u2022 GENDER",    profile["gender"]),
        ("\u2022 BLOOD",     profile["blood_group"]),
        ("\u2022 NATIONALITY", profile["nationality"]),
        ("\u2022 PHONE",     profile["phone"]),
        ("\u2022 EMAIL",     profile["email"]),
    ]

    card_h = header_h + divider_h + padding + len(fields) * line_h + padding + status_h

    # Position card to the right of the face
    card_x = right + 20
    card_y = max(top - 20, 10)

    # Flip to left if off-screen
    if card_x + card_w > fw - 10:
        card_x = max(10, left - card_w - 20)

    # Shift up if off-screen bottom
    if card_y + card_h > fh - 10:
        card_y = max(10, fh - card_h - 10)

    # ── Card background with rounded corners ──
    _rounded_rect(frame,
                  (card_x, card_y),
                  (card_x + card_w, card_y + card_h),
                  CLR_PANEL_BG, 12, -1, CARD_ALPHA)

    # ── Card border ──
    _rounded_rect(frame,
                  (card_x, card_y),
                  (card_x + card_w, card_y + card_h),
                  CLR_TEAL, 12, 1)

    # ── Header background ──
    _rounded_rect(frame,
                  (card_x + 1, card_y + 1),
                  (card_x + card_w - 1, card_y + header_h),
                  CLR_HEADER_BG, 11, -1, 0.9)

    # ── Status indicator dot (pulsing) ──
    dot_alpha = 0.6 + 0.4 * ((math.sin(pulse_phase * 2) + 1) / 2)
    dot_color = tuple(int(c * dot_alpha) for c in CLR_NEON_GREEN)
    cv2.circle(frame, (card_x + padding + 5, card_y + header_h // 2), 5, dot_color, -1)
    cv2.circle(frame, (card_x + padding + 5, card_y + header_h // 2), 5, CLR_NEON_GREEN, 1)

    # ── Header text: Name ──
    name_x = card_x + padding + 18
    # Truncate name if too long
    display_name = profile["full_name"]
    max_name_px = card_w - 40
    while cv2.getTextSize(display_name, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)[0][0] > max_name_px and len(display_name) > 5:
        display_name = display_name[:-4] + "..."

    cv2.putText(frame, display_name,
                (name_x, card_y + 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, CLR_WHITE, 2)

    # "VERIFIED" sub-label
    cv2.putText(frame, "IDENTITY VERIFIED",
                (name_x, card_y + 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, CLR_NEON_GREEN, 1)

    # ── Accent divider line ──
    div_y = card_y + header_h + 1
    cv2.line(frame, (card_x + padding, div_y),
             (card_x + card_w - padding, div_y), CLR_TEAL, 1)

    # ── Fields ──
    y_cursor = div_y + padding + 14
    for label, value in fields:
        # Label
        cv2.putText(frame, label,
                    (card_x + padding, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, CLR_LABEL, 1)

        # Value
        val_x = card_x + padding + 90
        display_val = str(value)
        max_val_px = card_w - 110
        while cv2.getTextSize(display_val, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0][0] > max_val_px and len(display_val) > 3:
            display_val = display_val[:-4] + "..."

        cv2.putText(frame, display_val,
                    (val_x, y_cursor),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, CLR_VALUE, 1)
        y_cursor += line_h

    # ── Bottom status bar ──
    bar_y = card_y + card_h - status_h
    _overlay_rect(frame,
                  (card_x + 1, bar_y),
                  (card_x + card_w - 1, card_y + card_h - 1),
                  CLR_DARKER, 0.5)

    cv2.line(frame, (card_x + padding, bar_y),
             (card_x + card_w - padding, bar_y), CLR_TEAL, 1)

    # Confidence bar placeholder
    conf_text = f"DB ID: #{profile['id']}"
    cv2.putText(frame, conf_text,
                (card_x + padding, bar_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, CLR_MID_GRAY, 1)

    # Timestamp
    ts = time.strftime("%H:%M:%S")
    ts_w = cv2.getTextSize(ts, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0][0]
    cv2.putText(frame, ts,
                (card_x + card_w - padding - ts_w, bar_y + 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, CLR_MID_GRAY, 1)

    # ── Connecting line from face to card ──
    face_cx = right + 2
    face_cy = top + (bottom - top) // 3
    card_cx = card_x if card_x > right else card_x + card_w
    card_cy = card_y + header_h // 2

    # Elbow connector
    mid_x = (face_cx + card_cx) // 2
    _draw_glow_line(frame, (face_cx, face_cy), (mid_x, face_cy), CLR_TEAL, 1, 4)
    _draw_glow_line(frame, (mid_x, face_cy), (mid_x, card_cy), CLR_TEAL, 1, 4)
    _draw_glow_line(frame, (mid_x, card_cy), (card_cx, card_cy), CLR_TEAL, 1, 4)

    # Dot at junction
    cv2.circle(frame, (mid_x, face_cy), 3, CLR_WHITE, -1)
    cv2.circle(frame, (mid_x, card_cy), 3, CLR_WHITE, -1)


# ──────────────────────────────────────────────
# ACCESS DENIED CARD (UNKNOWN FACE)
# ──────────────────────────────────────────────

def draw_denied_overlay(frame, top, right, bottom, left, pulse_phase):
    """Draw a red 'ACCESS DENIED' overlay for unrecognized faces."""
    w = right - left

    # ── Banner below face ──
    banner_h = 40
    banner_y = bottom + 8
    banner_x = left

    _rounded_rect(frame,
                  (banner_x, banner_y),
                  (banner_x + w, banner_y + banner_h),
                  CLR_DARK_RED, 8, -1, 0.85)

    _rounded_rect(frame,
                  (banner_x, banner_y),
                  (banner_x + w, banner_y + banner_h),
                  CLR_NEON_RED, 8, 1)

    # Pulsing warning icon
    icon_x = banner_x + 18
    icon_y = banner_y + banner_h // 2
    icon_alpha = 0.6 + 0.4 * ((math.sin(pulse_phase * 3) + 1) / 2)
    icon_color = tuple(int(c * icon_alpha) for c in CLR_NEON_RED)

    # Triangle warning sign
    tri_size = 8
    pts = np.array([
        [icon_x, icon_y - tri_size],
        [icon_x - tri_size, icon_y + tri_size - 2],
        [icon_x + tri_size, icon_y + tri_size - 2],
    ], np.int32)
    cv2.polylines(frame, [pts], True, icon_color, 2)
    cv2.putText(frame, "!",
                (icon_x - 3, icon_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, icon_color, 2)

    # Text
    text = "ACCESS DENIED"
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
    text_x = banner_x + 35
    text_y = banner_y + banner_h // 2 + text_size[1] // 2
    cv2.putText(frame, text, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, CLR_WHITE, 2)

    # "UNKNOWN" sub-label
    sub_text = "UNREGISTERED"
    sub_size = cv2.getTextSize(sub_text, cv2.FONT_HERSHEY_SIMPLEX, 0.3, 1)[0]
    sub_x = banner_x + w - sub_size[0] - 12
    cv2.putText(frame, sub_text, (sub_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, CLR_NEON_RED, 1)


# ──────────────────────────────────────────────
# HEADS-UP DISPLAY (HUD)
# ──────────────────────────────────────────────

def draw_hud(frame, fps_val, known_count, active_faces, t, alerts_enabled, total_threats):
    """Draw a professional heads-up display."""
    fh, fw = frame.shape[:2]

    # ── Top-left info panel ──
    panel_w = 340
    panel_h = 92
    _rounded_rect(frame, (10, 10), (10 + panel_w, 10 + panel_h),
                  CLR_PANEL_BG, 8, -1, 0.7)
    _rounded_rect(frame, (10, 10), (10 + panel_w, 10 + panel_h),
                  CLR_TEAL, 8, 1)

    # Title
    cv2.putText(frame, "FACE RECOGNITION SYSTEM",
                (22, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.42, CLR_NEON_CYAN, 1)

    # Divider
    cv2.line(frame, (22, 38), (10 + panel_w - 12, 38), CLR_TEAL, 1)

    # Stats row
    # FPS
    fps_color = CLR_NEON_GREEN if fps_val >= 20 else CLR_NEON_RED
    cv2.putText(frame, f"FPS {fps_val:.0f}",
                (22, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.38, fps_color, 1)

    # DB count
    cv2.putText(frame, f"|  DB: {known_count}",
                (90, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.38, CLR_LIGHT_GRAY, 1)

    # Active faces
    cv2.putText(frame, f"|  ACTIVE: {active_faces}",
                (165, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.38, CLR_LIGHT_GRAY, 1)

    # Added weapon counts to HUD
    alert_status = "ON" if alerts_enabled else "OFF"
    alert_color = CLR_NEON_GREEN if alerts_enabled else CLR_NEON_RED
    cv2.putText(frame, f"|  ALERTS: {alert_status}",
                (245, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.38, alert_color, 1)

    # Timestamp
    ts = time.strftime("%H:%M:%S")
    cv2.putText(frame, ts,
                (22, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.35, CLR_MID_GRAY, 1)

    cv2.putText(frame, f"|  THREATS: {total_threats}",
                (120, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.38, CLR_NEON_RED if total_threats > 0 else CLR_LIGHT_GRAY, 1)

    # Live dot (pulsing)
    dot_alpha = 0.5 + 0.5 * ((math.sin(t * 4) + 1) / 2)
    dot_color = tuple(int(c * dot_alpha) for c in CLR_NEON_RED)
    cv2.circle(frame, (85, 71), 4, dot_color, -1)
    cv2.putText(frame, "LIVE",
                (93, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.32, CLR_NEON_RED, 1)

    # ── Bottom bar ──
    bar_h = 32
    _overlay_rect(frame, (0, fh - bar_h), (fw, fh), CLR_DARKER, 0.7)
    cv2.line(frame, (0, fh - bar_h), (fw, fh - bar_h), CLR_TEAL, 1)

    cv2.putText(frame, "SECURE AREA MONITORING  |  'q' exit  |  'r' reload DB | 'a' toggle alerts | 'b' switch BG",
                (15, fh - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, CLR_LIGHT_GRAY, 1)

    # ── Corner decorations ──
    dec_len = 30
    dec_clr = CLR_TEAL
    # Top-right
    cv2.line(frame, (fw - dec_len - 10, 10), (fw - 10, 10), dec_clr, 1)
    cv2.line(frame, (fw - 10, 10), (fw - 10, 10 + dec_len), dec_clr, 1)
    # Bottom-left
    cv2.line(frame, (10, fh - bar_h - 10), (10 + dec_len, fh - bar_h - 10), dec_clr, 1)
    cv2.line(frame, (10, fh - bar_h - 10), (10, fh - bar_h - 10 - dec_len), dec_clr, 1)


# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────

def main():
    print("\n" + "=" * 55)
    print("  REAL-TIME SECURE MONITORING SYSTEM — Pro Edition")
    print("  (Face Recognition + Threat Detection)")
    print("=" * 55)

    # Initialize Threat Detection
    weapon_detector = WeaponDetector()
    alerter = WhatsAppAlerter()
    alerts_enabled = True
    total_threats = 0

    # Load known faces from DB
    known_encodings, known_profiles = load_known_faces()
    if len(known_encodings) == 0:
        print("[WARNING] No faces enrolled. Run enroll_face.py first.")

    # Open webcam
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

    frame_count = 0
    face_locations = []
    face_names = []
    face_profiles = []
    threats = []

    # Virtual Background
    use_virtual_bg = False  # Disabled by default for performance — press 'b' to toggle
    bg_img = cv2.imread(VIRTUAL_BG_PATH)
    bg_resized = None
    if bg_img is None:
        print(f"[WARNING] Could not load background image: {VIRTUAL_BG_PATH}. Virtual background disabled.")
    
    mp_selfie = mp.solutions.selfie_segmentation
    selfie_seg = mp_selfie.SelfieSegmentation(model_selection=1)
    cached_vbg_frame = None  # cache the virtual-bg blended frame

    # FPS
    prev_time = time.time()
    fps_val = 0.0
    fps_smooth = 30.0  # smoothed FPS for display

    print("[INFO] Webcam started. Press 'q' to quit, 'r' to reload DB.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to grab frame.")
            break

        frame_count += 1
        current_time = time.time()
        pulse_phase = current_time * 3  # for animations

        # ── Virtual Background (runs every other frame, caches result) ──
        if use_virtual_bg and bg_img is not None:
            if bg_resized is None or bg_resized.shape[:2] != frame.shape[:2]:
                bg_resized = cv2.resize(bg_img, (frame.shape[1], frame.shape[0]))
            
            if frame_count % 2 == 0:
                # Process segmentation every other frame
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = selfie_seg.process(rgb_frame)
                mask = results.segmentation_mask
                # Use simple threshold instead of expensive GaussianBlur
                condition_smooth = np.stack((mask,) * 3, axis=-1)
                cached_vbg_frame = condition_smooth  # cache the mask
            
            if cached_vbg_frame is not None:
                frame = (cached_vbg_frame * frame + (1 - cached_vbg_frame) * bg_resized).astype(np.uint8)

        # ── Process every N-th frame ──
        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            small_frame = cv2.resize(frame, (0, 0),
                                     fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

            face_names = []
            face_profiles = []

            for enc in face_encodings:
                name = "Unknown"
                profile = None

                if len(known_encodings) > 0:
                    distances = face_recognition.face_distance(known_encodings, enc)
                    best_idx = np.argmin(distances)
                    if distances[best_idx] <= TOLERANCE:
                        profile = known_profiles[best_idx]
                        name = profile["full_name"]

                face_names.append(name)
                face_profiles.append(profile)

        # ── Weapon detection (staggered — runs less frequently) ──
        if frame_count % WEAPON_EVERY_N_FRAMES == 0:
            # Pass original frame, YOLO handles resizing internally to imgsz=480
            threats = weapon_detector.detect(frame)
            if threats:
                total_threats += len(threats)

        # ── Calculate FPS ──
        dt = current_time - prev_time
        if dt > 0:
            fps_val = 1.0 / dt
            fps_smooth = fps_smooth * 0.9 + fps_val * 0.1  # exponential smoothing
        prev_time = current_time

        # ── Draw results ──
        scale = int(1 / RESIZE_FACTOR)
        active_count = len(face_locations)

        for i, (top, right, bottom, left) in enumerate(face_locations):
            top *= scale
            right *= scale
            bottom *= scale
            left *= scale

            if i < len(face_names):
                name = face_names[i]
                profile = face_profiles[i]
            else:
                name = "Unknown"
                profile = None

            if name != "Unknown" and profile is not None:
                # ✅ Known — cyan frame + profile card
                draw_face_frame(frame, top, right, bottom, left,
                                CLR_NEON_CYAN, pulse_phase)
                draw_profile_card(frame, top, right, bottom, left,
                                  profile, pulse_phase)
            else:
                # ❌ Unknown — red frame + denied overlay
                draw_face_frame(frame, top, right, bottom, left,
                                CLR_NEON_RED, pulse_phase)
                draw_denied_overlay(frame, top, right, bottom, left,
                                    pulse_phase)

        # ── Draw Weapons and Trigger Alerts ──
        try:
            for threat in threats:
                t_top, t_right, t_bottom, t_left = threat["bbox"]
                cls_name = threat["class_name"]
                conf = threat["conf"]
                
                # Draw red box around weapon
                cv2.rectangle(frame, (t_left, t_top), (t_right, t_bottom), CLR_NEON_RED, 3)
                cv2.putText(frame, f"{cls_name} {int(conf*100)}%", (t_left, t_top - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, CLR_NEON_RED, 2)
                
                # Full-screen Alert Banner
                banner_h = 60
                w = frame.shape[1]
                _overlay_rect(frame, (0, 0), (w, banner_h), CLR_DARK_RED, 0.8)
                cv2.rectangle(frame, (0, 0), (w, banner_h), CLR_NEON_RED, 2)
                
                # Pulsing text
                alpha = 0.5 + 0.5 * ((math.sin(pulse_phase * 4) + 1) / 2)
                txt_color = tuple(int(c * alpha) for c in CLR_WHITE)
                cv2.putText(frame, f"⚠️ WEAPON DETECTED: {cls_name.upper()} ⚠️", (w//2 - 250, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, txt_color, 3)
                
                # Finding nearest face to link the threat
                closest_profile = None
                min_dist = float('inf')
                
                for i, (f_top, f_right, f_bottom, f_left) in enumerate(face_locations):
                    # Scale back face coords to original frame size
                    f_top *= scale
                    f_right *= scale
                    f_bottom *= scale
                    f_left *= scale
                    
                    # Center of face
                    fc_x = (f_left + f_right) / 2
                    fc_y = (f_top + f_bottom) / 2
                    
                    # Center of weapon
                    wc_x = (t_left + t_right) / 2
                    wc_y = (t_top + t_bottom) / 2
                    
                    dist = math.dist((fc_x, fc_y), (wc_x, wc_y))
                    if dist < min_dist:
                        min_dist = dist
                        if i < len(face_profiles):
                            closest_profile = face_profiles[i]
                            
                # Trigger Alert
                if alerts_enabled:
                    alerter.trigger_alert(cls_name, conf, closest_profile, frame.copy())
        except Exception as e:
            print(f"[DEBUG] Error drawing weapons: {e}")

        # ── HUD ──
        draw_hud(frame, fps_smooth, len(known_encodings),
                 active_count, current_time, alerts_enabled, total_threats)

        # ── Display ──
        cv2.imshow("Face Recognition System", frame)

        # ── Keyboard input ──
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("r"):
            # Reload database
            print("[INFO] Reloading face database ...")
            known_encodings, known_profiles = load_known_faces()
        elif key == ord("b"):
            # Toggle Virtual Background
            use_virtual_bg = not use_virtual_bg
            status = "ENABLED" if use_virtual_bg else "DISABLED"
            print(f"[INFO] Virtual Background {status}")
        elif key == ord("a"):
            # Toggle Alerts
            alerts_enabled = not alerts_enabled
            status = "ON" if alerts_enabled else "OFF"
            alerter.config["enabled"] = alerts_enabled
            print(f"[INFO] WhatsApp Alerts {status}")

    selfie_seg.close()
    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] System shut down gracefully.")


if __name__ == "__main__":
    main()
