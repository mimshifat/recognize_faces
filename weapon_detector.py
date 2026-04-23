from ultralytics import YOLO

class WeaponDetector:
    def __init__(self, model_path="yolov8n.pt", confidence=0.10):
        # Initializing the YOLO model (downloads automatically if not present)
        print("[INFO] Loading YOLOv8 weapon detection model...")
        self.model = YOLO(model_path)
        self.confidence = confidence
        
        # COCO IDs for potential weapons (43: knife, 76: scissors)
        self.weapon_classes = {43: "Knife", 76: "Scissors"}
        self.weapon_class_ids = list(self.weapon_classes.keys())
        
    def detect(self, frame):
        """
        Returns a list of dicts: {"bbox": (top, right, bottom, left), "class_name": str, "conf": float}
        Optimized: uses imgsz=320, classes filter, and half precision where available.
        """
        detections = []
        # Run inference — key optimizations:
        #   imgsz=320   : process at 320px instead of default 640 (4x less pixels)
        #   classes=...  : ONLY detect knife(43) and scissors(76), skip all other 78 classes
        #   verbose=False: no console spam
        results = self.model(
            frame,
            imgsz=480,
            classes=self.weapon_class_ids,
            verbose=False,
            conf=self.confidence,
        )
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = box.conf[0].item()
                
                # Bounding box: YOLO gives (x1, y1, x2, y2)
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                detections.append({
                    "bbox": (y1, x2, y2, x1),
                    "class_name": self.weapon_classes[cls_id],
                    "conf": conf
                })
                    
        return detections
