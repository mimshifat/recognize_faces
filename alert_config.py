import os
from dotenv import load_dotenv

load_dotenv()

#   Create the snapshots directory immediately
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "alert_snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

ALERT_CONFIG = {
    "enabled": True,
    # Phone number including country code (e.g., "+8801787929436")
    "phone_number": os.getenv("ALERT_PHONE_NUMBER", ""), 
    
    # CallMeBot API Key (Get this by sending "I allow callmebot to send me messages" to +34 624 54 81 55)
    "callmebot_apikey": os.getenv("CALLMEBOT_API_KEY", ""),
    
    "cooldown_seconds": 15,             # Min time between alerts for the same person/threat
    "save_snapshots": True,             # Save frame screenshots on detection
    "snapshot_dir": SNAPSHOT_DIR,
}
