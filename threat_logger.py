from db_config import get_connection

def log_threat_event(threat_type, confidence, user_profile_id, person_name, snapshot_path, alert_sent):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO threat_events (
                threat_type, confidence, user_profile_id, person_name, snapshot_path, alert_sent
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (threat_type, float(confidence), user_profile_id, person_name, snapshot_path, alert_sent)
        )
        conn.commit()
    except Exception as e:
        print(f"[ERROR] Could not log threat event to DB: {e}")
    finally:
        if conn:
            conn.close()
