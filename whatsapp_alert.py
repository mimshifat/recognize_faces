import os
import time
import threading
import cv2
import urllib.parse
import urllib.request
from datetime import datetime
from alert_config import ALERT_CONFIG
from threat_logger import log_threat_event

class WhatsAppAlerter:
    def __init__(self):
        self.config = ALERT_CONFIG
        self.last_alert_time = {} # dict mapping person_id (or 'Unknown') to timestamp
        self.is_sending = False # prevent multiple concurrent sends
        
    def _send_message_thread(self, phone_no, text_message):
        try:
            self.is_sending = True
            apikey = self.config.get("callmebot_apikey", "")
            
            if not apikey:
                print("[ERROR] CallMeBot API key is missing. Please add it to alert_config.py")
                return
                
            print(f"[INFO] Sending background WhatsApp alert to {phone_no} via CallMeBot...")
            
            # Clean and encode parameters
            clean_phone = str(phone_no).replace("+", "")
            encoded_message = urllib.parse.quote_plus(text_message)
            
            # Format URL for CallMeBot
            url = f"https://api.callmebot.com/whatsapp.php?phone={clean_phone}&text={encoded_message}&apikey={apikey}"
            
            # Send HTTP GET request
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            
            if response.getcode() == 200:
                print("[INFO] Background WhatsApp alert sent successfully!")
            else:
                print(f"[ERROR] CallMeBot returned status code: {response.getcode()}")
                
        except Exception as e:
            print(f"[ERROR] Failed to send WhatsApp alert via CallMeBot: {e}")
        finally:
            self.is_sending = False

    def trigger_alert(self, threat_type, confidence, profile, frame):
        if not self.config["enabled"]:
            return

        # Track person ID for cooldown (use "Unknown" if no profile)
        person_id = profile["id"] if profile else "Unknown"
        person_name = profile["full_name"] if profile else "UNIDENTIFIED"
        
        # Check cooldown
        current_time = time.time()
        last_time = self.last_alert_time.get(person_id, 0)
        
        if current_time - last_time < self.config["cooldown_seconds"]:
            return # Skip, still in cooldown
            
        # Update cooldown timestamp
        self.last_alert_time[person_id] = current_time
        
        # Save snapshot
        snapshot_path = None
        current_dt = datetime.now()
        dt_str = current_dt.strftime("%Y%m%d_%H%M%S")
        
        if self.config["save_snapshots"]:
            snapshot_name = f"alert_{dt_str}.jpg"
            snapshot_path = os.path.join(self.config["snapshot_dir"], snapshot_name)
            cv2.imwrite(snapshot_path, frame)
            
        has_alert_sent = not self.is_sending
        
        # Log to DB
        log_threat_event(
            threat_type=threat_type,
            confidence=confidence,
            user_profile_id=profile["id"] if profile else None,
            person_name=person_name,
            snapshot_path=snapshot_path,
            alert_sent=has_alert_sent
        )

        if self.is_sending:
            return

        # Build message
        dt_pretty = current_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        if profile:
            message = (
                f"🚨 *SECURITY ALERT* 🚨\\n\\n"
                f"⚔️ *Threat*: {threat_type.upper()} detected ({int(confidence*100)}% confidence)\\n"
                f"📅 *Time*: {dt_pretty}\\n\\n"
                f"👤 *Person Identified*:\\n"
                f"   • Name: {profile['full_name']}\\n"
                f"   • Phone: {profile['phone']}\\n"
                f"   • Email: {profile['email']}\\n"
                f"   • Blood Group: {profile['blood_group']}\\n\\n"
                f"⚠️ Immediate attention required!"
            )
        else:
            message = (
                f"🚨 *SECURITY ALERT* 🚨\\n\\n"
                f"⚔️ *Threat*: {threat_type.upper()} detected ({int(confidence*100)}% confidence)\\n"
                f"📅 *Time*: {dt_pretty}\\n\\n"
                f"👤 *Person*: UNIDENTIFIED (not in database)\\n\\n"
                f"⚠️ CRITICAL: Unknown person with weapon!"
            )
            
        # Send in background thread to avoid freezing video feed
        t = threading.Thread(
            target=self._send_message_thread, 
            args=(self.config["phone_number"], message)
        )
        t.daemon = True
        t.start()
