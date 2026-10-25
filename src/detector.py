# import cv2
# import torch
# import numpy as np
# import yaml
# from ultralytics import YOLO
# from typing import List, Dict, Any, Tuple
# import math
# from threading import Lock
# import time

# class EnhancedObjectDetector:
#     def __init__(self, config_path: str = "config.yaml"):
#         with open(config_path, 'r') as f:
#             self.config = yaml.safe_load(f)
        
#         yolo_config = self.config['yolo']
#         self.model_path = yolo_config['model_path']
#         self.confidence_threshold = yolo_config['confidence_threshold']
#         self.iou_threshold = yolo_config['iou_threshold']
#         self.detection_frequency = yolo_config['detection_frequency']
#         # Use optimized inference size from config for speed (can be increased for accuracy)
#         self.inference_size = yolo_config['inference_size']
#         self.half_precision = yolo_config.get('half_precision', False)
        
#         # Inference caching to avoid redundant detections
#         self.last_detection_time = 0
#         self.last_detections = []
#         self.inference_lock = Lock()
#         # NO CACHING/SKIPPING - Run detection every single frame for real-time accuracy
#         self.detection_interval = 0.001  # ~1000 FPS max (will be limited by GPU/CPU)
        
#         # Enhanced COCO class names
#         self.class_names = [
#             'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 
#             'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
#             'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
#             'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
#             'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
#             'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
#             'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
#             'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
#             'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
#             'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
#             'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
#             'toothbrush'
#         ]
        
#         # Important objects for navigation guidance
#         self.important_objects = [
#             'person', 'chair', 'dining table', 'bed', 'couch', 'car', 'bicycle', 
#             'motorcycle', 'bus', 'truck', 'bottle', 'cup', 'backpack', 'handbag'
#         ]
        
#         # Static objects that don't move
#         self.static_objects = ['chair', 'dining table', 'bed', 'couch', 'tv', 'laptop', 
#                               'refrigerator', 'sink', 'toilet', 'bottle', 'cup', 'book']
        
#         # Obstacle categories for better guidance
#         self.obstacle_categories = {
#             'high_priority': ['person', 'car', 'motorcycle', 'bicycle', 'bus', 'truck'],
#             'medium_priority': ['chair', 'dining table', 'bed', 'couch', 'bench'],
#             'low_priority': ['bottle', 'cup', 'backpack', 'handbag', 'book'],
#             'static_obstacles': ['chair', 'dining table', 'bed', 'couch', 'tv', 'refrigerator', 'sink', 'toilet']
#         }
        
#         # Wall detection parameters
#         self.wall_detection_enabled = True
#         self.edge_threshold1 = 50
#         self.edge_threshold2 = 150
        
#         # Initialize YOLO model
#         try:
#             self.model = YOLO(self.model_path)
#             self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
#             self.model.to(self.device)
#             # Disable PyTorch gradient computation for faster inference
#             torch.set_grad_enabled(False)
#             # Enable model caching for faster inference
#             if hasattr(self.model, 'model'):
#                 self.model.model.float() if not self.half_precision else self.model.model.half()
#             print(f"🚀 Enhanced YOLO model loaded on {self.device.upper()}")
#             print(f"📦 Static object detection: ENABLED")
#             print(f"🎯 Tracking {len(self.important_objects)} important objects")
#             print(f"⚡ Full resolution inference (640x640) - all features enabled")
#         except Exception as e:
#             print(f"❌ Error loading YOLO model: {e}")
#             print("📥 Downloading YOLOv8n model...")
#             self.model = YOLO('yolov8n.pt')
#             self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
#             self.model.to(self.device)
#             torch.set_grad_enabled(False)
    
#     def detect_enhanced(self, frame: np.ndarray) -> List[Dict[str, Any]]:
#         """Enhanced detection with focus on important objects and better filtering"""
#         try:
#             if frame is None or frame.size == 0:
#                 return self.last_detections  # Return cached detections
            
#             # Check if enough time has passed for new detection
#             current_time = time.time()
#             if current_time - self.last_detection_time < self.detection_interval:
#                 return self.last_detections  # Return cached detections
            
#             with self.inference_lock:
#                 # Run YOLO inference with optimized settings
#                 results = self.model(
#                     frame, 
#                     conf=self.confidence_threshold, 
#                     iou=self.iou_threshold,
#                     imgsz=self.inference_size,
#                     verbose=False
#                 )
                
#                 detections = []
#                 for result in results:
#                     # Use arrays exposed by ultralytics for robustness
#                     boxes = getattr(result, 'boxes', None)
#                     if boxes is None:
#                         continue

#                     try:
#                         xyxy = boxes.xyxy.cpu().numpy()  # (N,4)
#                         confs = boxes.conf.cpu().numpy()  # (N,)
#                         cls_ids = boxes.cls.cpu().numpy().astype(int)  # (N,)
#                     except Exception:
#                         # Fallback: iterate box objects
#                         for box in boxes:
#                             try:
#                                 coords = box.xyxy[0].cpu().numpy()
#                                 x1, y1, x2, y2 = coords.tolist()
#                                 confidence = float(box.conf[0].cpu().numpy())
#                                 class_id = int(box.cls[0].cpu().numpy())
#                             except Exception:
#                                 continue
#                             if class_id >= len(self.class_names):
#                                 continue
#                             class_name = self.class_names[class_id]
#                             # Relaxed size filter to include small objects (phones)
#                             bbox_area = max(1.0, (x2 - x1) * (y2 - y1))
#                             frame_area = max(1.0, frame.shape[0] * frame.shape[1])
#                             if bbox_area / frame_area < 0.0005:
#                                 continue
#                             adjusted_confidence = float(confidence)
#                             detections.append({
#                                 'bbox': [float(x1), float(y1), float(x2), float(y2)],
#                                 'confidence': adjusted_confidence,
#                                 'class_id': class_id,
#                                 'class_name': class_name,
#                                 'is_static': class_name in self.static_objects,
#                                 'is_important': class_name in self.important_objects
#                             })
#                         continue

#                     frame_area = max(1.0, frame.shape[0] * frame.shape[1])
#                     for i in range(len(xyxy)):
#                         x1, y1, x2, y2 = map(float, xyxy[i])
#                         if x2 <= x1 or y2 <= y1:
#                             continue

#                         bbox_area = (x2 - x1) * (y2 - y1)
#                         # Allow smaller objects like phones (lower threshold)
#                         if bbox_area / frame_area < 0.0005:
#                             continue

#                         confidence = float(confs[i])
#                         class_id = int(cls_ids[i])
#                         if class_id >= len(self.class_names):
#                             continue

#                         class_name = self.class_names[class_id]

#                         # Use configured minimum confidence if available (audio-guidance level)
#                         min_conf_global = self.config.get('audio', {}).get('min_confidence', 0.6)
#                         min_conf_static = self.config.get('static_objects', {}).get('min_confidence', 0.25)
#                         min_conf = max(min_conf_static, min_conf_global)
#                         # Do not over-filter important objects; accept if in important_objects
#                         if (class_name not in self.important_objects) and (confidence < min_conf):
#                             continue

#                         adjusted_confidence = confidence * (1.2 if class_name in self.static_objects else 1.0)
#                         adjusted_confidence = min(1.0, adjusted_confidence)

#                         detections.append({
#                             'bbox': [float(x1), float(y1), float(x2), float(y2)],
#                             'confidence': float(adjusted_confidence),
#                             'class_id': class_id,
#                             'class_name': class_name,
#                             'is_static': class_name in self.static_objects,
#                             'is_important': class_name in self.important_objects
#                         })
            
#             # Update cache
#             self.last_detection_time = current_time
#             self.last_detections = detections
            
#             # Sort by importance (important objects first, then by confidence)
#             detections.sort(key=lambda x: (x['is_important'], x['confidence']), reverse=True)
            
#             return detections[:15]  # Limit to top 15 detections
            
#         except Exception as e:
#             print(f"❌ Enhanced detection error: {e}")
#             return []
    
#     def detect_important_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
#         """Detect only important objects for navigation"""
#         all_detections = self.detect_enhanced(frame)
#         important_detections = [det for det in all_detections if det['is_important']]
#         return important_detections
    
#     def get_class_names(self) -> List[str]:
#         """Get list of class names"""
#         return self.class_names
    
#     def get_important_objects(self) -> List[str]:
#         """Get list of important objects"""
#         return self.important_objects
    
#     def get_static_objects(self) -> List[str]:
#         """Get list of static objects"""
#         return self.static_objects
    
#     def detect_walls_and_obstacles(self, frame: np.ndarray) -> List[Dict[str, Any]]:
#         """Detect walls and large obstacles using edge detection and depth estimation"""
#         if not self.wall_detection_enabled:
#             return []
        
#         try:
#             # Convert to grayscale for edge detection
#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
#             # Apply Gaussian blur to reduce noise
#             blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
#             # Edge detection using Canny
#             edges = cv2.Canny(blurred, self.edge_threshold1, self.edge_threshold2)
            
#             # Find contours
#             contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
#             wall_detections = []
#             frame_height, frame_width = frame.shape[:2]
            
#             for contour in contours:
#                 # Filter contours by area
#                 area = cv2.contourArea(contour)
#                 if area < 1000:  # Skip small contours
#                     continue
                
#                 # Get bounding rectangle
#                 x, y, w, h = cv2.boundingRect(contour)
                
#                 # Calculate aspect ratio to identify walls
#                 aspect_ratio = w / h if h > 0 else 0
                
#                 # Wall characteristics: high aspect ratio (horizontal) or tall (vertical)
#                 is_wall = aspect_ratio > 3.0 or aspect_ratio < 0.3
                
#                 if is_wall:
#                     # Estimate distance based on size and position
#                     distance = self._estimate_wall_distance(w, h, frame_width, frame_height)
                    
#                     # Determine wall position
#                     wall_position = self._get_wall_position(x, y, w, h, frame_width, frame_height)
                    
#                     wall_detections.append({
#                         'bbox': [float(x), float(y), float(x + w), float(y + h)],
#                         'confidence': 0.8,  # High confidence for walls
#                         'class_id': -1,  # Special ID for walls
#                         'class_name': 'wall',
#                         'is_static': True,
#                         'is_important': True,
#                         'distance': distance,
#                         'position': wall_position,
#                         'obstacle_type': 'wall',
#                         'danger_level': 'medium' if distance < 2.0 else 'low'
#                     })
            
#             return wall_detections
            
#         except Exception as e:
#             print(f"❌ Wall detection error: {e}")
#             return []
    
#     def _estimate_wall_distance(self, width: int, height: int, frame_width: int, frame_height: int) -> float:
#         """Estimate distance to wall based on size and position"""
#         # Walls that span most of the frame are closer
#         width_ratio = width / frame_width
#         height_ratio = height / frame_height
        
#         # If wall spans most of the width, it's likely close
#         if width_ratio > 0.8:
#             return 1.5  # Close wall
#         elif width_ratio > 0.5:
#             return 3.0  # Medium distance
#         else:
#             return 5.0  # Far wall
    
#     def _get_wall_position(self, x: int, y: int, w: int, h: int, frame_width: int, frame_height: int) -> str:
#         """Determine wall position relative to user"""
#         center_x = x + w // 2
#         center_y = y + h // 2
        
#         # Horizontal position
#         if center_x < frame_width * 0.3:
#             horizontal = "left"
#         elif center_x > frame_width * 0.7:
#             horizontal = "right"
#         else:
#             horizontal = "ahead"
        
#         # Vertical position (for walls)
#         if center_y < frame_height * 0.3:
#             vertical = "above"
#         elif center_y > frame_height * 0.7:
#             vertical = "below"
#         else:
#             vertical = "at eye level"
        
#         return f"{horizontal} {vertical}"
    
#     def analyze_obstacle_danger(self, detection: Dict[str, Any], frame_width: int, frame_height: int) -> Dict[str, Any]:
#         """Analyze obstacle danger level and provide guidance"""
#         bbox = detection['bbox']
#         class_name = detection['class_name']
        
#         # Calculate object size and position
#         x1, y1, x2, y2 = bbox
#         center_x = (x1 + x2) / 2
#         center_y = (y1 + y2) / 2
#         width = x2 - x1
#         height = y2 - y1
        
#         # Calculate distance (simplified)
#         bbox_area = width * height
#         frame_area = frame_width * frame_height
#         coverage_ratio = bbox_area / frame_area
        
#         # Distance estimation
#         if coverage_ratio > 0.1:
#             distance = 0.5  # Very close
#         elif coverage_ratio > 0.05:
#             distance = 1.0  # Close
#         elif coverage_ratio > 0.02:
#             distance = 2.0  # Medium
#         else:
#             distance = 4.0  # Far
        
#         # Position analysis
#         normalized_x = center_x / frame_width
#         if normalized_x < 0.25:
#             position = "far left"
#         elif normalized_x < 0.4:
#             position = "left"
#         elif normalized_x < 0.6:
#             position = "ahead"
#         elif normalized_x < 0.75:
#             position = "right"
#         else:
#             position = "far right"
        
#         # Danger level assessment
#         danger_level = "low"
#         if class_name in self.obstacle_categories['high_priority']:
#             if distance < 1.0:
#                 danger_level = "critical"
#             elif distance < 2.0:
#                 danger_level = "high"
#             else:
#                 danger_level = "medium"
#         elif class_name in self.obstacle_categories['medium_priority']:
#             if distance < 0.8:
#                 danger_level = "high"
#             elif distance < 1.5:
#                 danger_level = "medium"
#         else:
#             if distance < 0.5:
#                 danger_level = "medium"
        
#         # Generate guidance message
#         guidance = self._generate_obstacle_guidance(class_name, distance, position, danger_level)
        
#         return {
#             'distance': distance,
#             'position': position,
#             'danger_level': danger_level,
#             'guidance': guidance,
#             'obstacle_type': self._get_obstacle_type(class_name),
#             'requires_action': danger_level in ['critical', 'high']
#         }
    
#     def _get_obstacle_type(self, class_name: str) -> str:
#         """Categorize obstacle type"""
#         if class_name in self.obstacle_categories['high_priority']:
#             return 'moving_obstacle'
#         elif class_name in self.obstacle_categories['static_obstacles']:
#             return 'static_obstacle'
#         else:
#             return 'small_object'
    
#     def _generate_obstacle_guidance(self, class_name: str, distance: float, position: str, danger_level: str) -> str:
#         """Generate specific guidance for obstacle"""
#         if danger_level == "critical":
#             return f"STOP! {class_name} very close {position} at {distance:.1f} meters!"
#         elif danger_level == "high":
#             return f"Caution! {class_name} close {position} at {distance:.1f} meters"
#         elif danger_level == "medium":
#             return f"{class_name} {position} at {distance:.1f} meters"
#         else:
#             return f"{class_name} {position} at {distance:.1f} meters"
    
#     def detect_comprehensive(self, frame: np.ndarray) -> List[Dict[str, Any]]:
#         """Comprehensive detection including objects and walls"""
#         # Get regular object detections
#         object_detections = self.detect_enhanced(frame)
        
#         # Get wall detections
#         wall_detections = self.detect_walls_and_obstacles(frame)
        
#         # Combine and analyze all detections
#         all_detections = object_detections + wall_detections
        
#         # Add comprehensive analysis to each detection
#         frame_height, frame_width = frame.shape[:2]
#         enhanced_detections = []
        
#         for detection in all_detections:
#             analysis = self.analyze_obstacle_danger(detection, frame_width, frame_height)
#             detection.update(analysis)
#             enhanced_detections.append(detection)
        
#         # Sort by danger level and priority
#         priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
#         enhanced_detections.sort(
#             key=lambda x: (
#                 priority_order.get(x.get('danger_level', 'low'), 1),
#                 x.get('confidence', 0)
#             ), 
#             reverse=True
#         )
        
#         return enhanced_detections

# # Compatibility alias
# ObjectDetector = EnhancedObjectDetector

import cv2
import torch
import numpy as np
import yaml
from ultralytics import YOLO
from typing import List, Dict, Any, Tuple
import math
from threading import Lock
import threading
import time

class EnhancedObjectDetector:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        yolo_config = self.config['yolo']
        self.model_path = yolo_config['model_path']
        self.confidence_threshold = yolo_config['confidence_threshold']
        self.iou_threshold = yolo_config['iou_threshold']
        self.detection_frequency = yolo_config['detection_frequency']
        self.inference_size = yolo_config['inference_size']
        self.half_precision = yolo_config.get('half_precision', False)
        
        # Get audio confidence threshold from config
        self.audio_confidence_threshold = self.config.get('audio', {}).get('confidence_threshold', 0.6)
        
        # Inference caching
        self.last_detection_time = 0
        self.last_detections = []
        self.inference_lock = Lock()
        self.detection_interval = 0.001  # ~1000 FPS max
        
        # Enhanced COCO class names
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
        
        # Important objects for navigation guidance
        self.important_objects = [
            'person', 'chair', 'dining table', 'bed', 'couch', 'car', 'bicycle', 
            'motorcycle', 'bus', 'truck', 'bottle', 'cup', 'backpack', 'handbag'
        ]
        
        # Static objects that don't move
        self.static_objects = ['chair', 'dining table', 'bed', 'couch', 'tv', 'laptop', 
                              'refrigerator', 'sink', 'toilet', 'bottle', 'cup', 'book']
        
        # Obstacle categories for better guidance
        self.obstacle_categories = {
            'high_priority': ['person', 'car', 'motorcycle', 'bicycle', 'bus', 'truck'],
            'medium_priority': ['chair', 'dining table', 'bed', 'couch', 'bench'],
            'low_priority': ['bottle', 'cup', 'backpack', 'handbag', 'book'],
            'static_obstacles': ['chair', 'dining table', 'bed', 'couch', 'tv', 'refrigerator', 'sink', 'toilet']
        }
        
        # Initialize YOLO model in background to avoid blocking startup
        self.model = None
        self.model_ready = False
        self.model_lock = Lock()

        def _load_model_bg():
            try:
                model = YOLO(self.model_path)
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                model.to(device)
                torch.set_grad_enabled(False)
                if hasattr(model, 'model'):
                    model.model.float() if not self.half_precision else model.model.half()
                with self.model_lock:
                    self.model = model
                    self.device = device
                    self.model_ready = True
                print(f"🚀 YOLO model loaded on {device.upper()} (background)")
            except Exception as e:
                print(f"❌ Background model load failed: {e}")
                try:
                    print("📥 Falling back to bundled yolov8n.pt model...")
                    model = YOLO('yolov8n.pt')
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                    model.to(device)
                    torch.set_grad_enabled(False)
                    if hasattr(model, 'model'):
                        model.model.float() if not self.half_precision else model.model.half()
                    with self.model_lock:
                        self.model = model
                        self.device = device
                        self.model_ready = True
                    print(f"✅ Fallback model loaded on {device.upper()}")
                except Exception as e2:
                    print(f"❌ Failed to load fallback model: {e2}")

        t = threading.Thread(target=_load_model_bg, daemon=True)
        t.start()

        # Frame slot & background inference thread to avoid blocking main loop
        self._frame_slot = None
        self._frame_lock = Lock()
        self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._inference_thread.start()
    
    def detect_enhanced(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Enhanced detection with focus on important objects and better filtering"""
        # Enqueue frame for background inference and return cached detections immediately
        try:
            if frame is None or frame.size == 0:
                return self.last_detections

            # Place latest frame into the single-slot buffer
            with self._frame_lock:
                # store a copy to avoid race conditions
                try:
                    self._frame_slot = frame.copy()
                except Exception:
                    self._frame_slot = frame

            # Return last cached detections immediately (non-blocking)
            return self.last_detections
        except Exception as e:
            print(f"❌ Enhanced detection enqueue error: {e}")
            return []

    def _inference_loop(self):
        """Background thread that runs inference on the latest enqueued frame."""
        while True:
            try:
                # only run if model ready
                if not getattr(self, 'model_ready', False) or self.model is None:
                    time.sleep(0.1)
                    continue

                frame = None
                with self._frame_lock:
                    if self._frame_slot is not None:
                        # grab frame and clear slot
                        try:
                            frame = self._frame_slot.copy()
                        except Exception:
                            frame = self._frame_slot
                        self._frame_slot = None

                if frame is None:
                    time.sleep(0.01)
                    continue

                # Throttle by detection_interval
                current_time = time.time()
                if current_time - self.last_detection_time < self.detection_interval:
                    time.sleep(max(0.0, self.detection_interval - (current_time - self.last_detection_time)))
                    continue

                # Run inference and process results
                try:
                    # Acquire model under lock
                    with self.model_lock:
                        model = self.model

                    with self.inference_lock:
                        results = model(
                            frame,
                            conf=self.confidence_threshold,
                            iou=self.iou_threshold,
                            imgsz=self.inference_size,
                            verbose=False
                        )

                    # Process results (reuse existing processing logic by calling an internal helper)
                    detections = []
                    for result in results:
                        boxes = getattr(result, 'boxes', None)
                        if boxes is None:
                            continue

                        try:
                            xyxy = boxes.xyxy.cpu().numpy()
                            confs = boxes.conf.cpu().numpy()
                            cls_ids = boxes.cls.cpu().numpy().astype(int)
                        except Exception:
                            for box in boxes:
                                try:
                                    coords = box.xyxy[0].cpu().numpy()
                                    x1, y1, x2, y2 = coords.tolist()
                                    confidence = float(box.conf[0].cpu().numpy())
                                    class_id = int(box.cls[0].cpu().numpy())
                                except Exception:
                                    continue
                                if class_id >= len(self.class_names):
                                    continue
                                class_name = self.class_names[class_id]
                                if confidence < self.audio_confidence_threshold and class_name not in self.important_objects:
                                    continue
                                bbox_area = max(1.0, (x2 - x1) * (y2 - y1))
                                frame_area = max(1.0, frame.shape[0] * frame.shape[1])
                                if bbox_area / frame_area < 0.0005:
                                    continue
                                detections.append({
                                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                                    'confidence': float(confidence),
                                    'class_id': class_id,
                                    'class_name': class_name,
                                    'is_static': class_name in self.static_objects,
                                    'is_important': class_name in self.important_objects
                                })
                            continue

                        frame_area = max(1.0, frame.shape[0] * frame.shape[1])
                        for i in range(len(xyxy)):
                            x1, y1, x2, y2 = map(float, xyxy[i])
                            if x2 <= x1 or y2 <= y1:
                                continue

                            bbox_area = (x2 - x1) * (y2 - y1)
                            if bbox_area / frame_area < 0.0005:
                                continue

                            confidence = float(confs[i])
                            class_id = int(cls_ids[i])
                            if class_id >= len(self.class_names):
                                continue

                            class_name = self.class_names[class_id]
                            if confidence < self.audio_confidence_threshold and class_name not in self.important_objects:
                                continue

                            adjusted_confidence = confidence * (1.2 if class_name in self.static_objects else 1.0)
                            adjusted_confidence = min(1.0, adjusted_confidence)

                            detections.append({
                                'bbox': [float(x1), float(y1), float(x2), float(y2)],
                                'confidence': float(adjusted_confidence),
                                'class_id': class_id,
                                'class_name': class_name,
                                'is_static': class_name in self.static_objects,
                                'is_important': class_name in self.important_objects
                            })

                    # Update cache and timestamp
                    detections.sort(key=lambda x: (
                        x['is_important'],
                        x['confidence'],
                        x['class_name'] in self.static_objects
                    ), reverse=True)
                    self.last_detection_time = time.time()
                    self.last_detections = detections[:15]

                except Exception as e:
                    print(f"❌ Background inference error: {e}")
                    # small pause to avoid tight error loop
                    time.sleep(0.05)

            except Exception:
                time.sleep(0.05)
    
    def detect_important_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect only important objects for navigation"""
        all_detections = self.detect_enhanced(frame)
        important_detections = [det for det in all_detections if det['is_important']]
        return important_detections
    
    # ... [Keep other methods unchanged, but ensure confidence is passed through] ...
    
    def analyze_obstacle_danger(self, detection: Dict[str, Any], frame_width: int, frame_height: int) -> Dict[str, Any]:
        """Analyze obstacle danger level and provide guidance"""
        bbox = detection['bbox']
        class_name = detection['class_name']
        confidence = detection.get('confidence', 0)
        
        # Calculate object size and position
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        width = x2 - x1
        height = y2 - y1
        
        # Calculate distance
        bbox_area = width * height
        frame_area = frame_width * frame_height
        coverage_ratio = bbox_area / frame_area
        
        # Distance estimation
        if coverage_ratio > 0.1:
            distance = 0.5  # Very close
        elif coverage_ratio > 0.05:
            distance = 1.0  # Close
        elif coverage_ratio > 0.02:
            distance = 2.0  # Medium
        else:
            distance = 4.0  # Far
        
        # Position analysis
        normalized_x = center_x / frame_width
        if normalized_x < 0.25:
            position = "far left"
        elif normalized_x < 0.4:
            position = "left"
        elif normalized_x < 0.6:
            position = "ahead"
        elif normalized_x < 0.75:
            position = "right"
        else:
            position = "far right"
        
        # Danger level assessment with confidence consideration
        danger_level = "low"
        if confidence >= self.audio_confidence_threshold:
            if class_name in self.obstacle_categories['high_priority']:
                if distance < 1.0:
                    danger_level = "critical"
                elif distance < 2.0:
                    danger_level = "high"
                else:
                    danger_level = "medium"
            elif class_name in self.obstacle_categories['medium_priority']:
                if distance < 0.8:
                    danger_level = "high"
                elif distance < 1.5:
                    danger_level = "medium"
            else:
                if distance < 0.5:
                    danger_level = "medium"
        else:
            # Low confidence objects are always low danger
            danger_level = "low"
        
        # Generate guidance message
        guidance = self._generate_obstacle_guidance(class_name, distance, position, danger_level, confidence)
        
        return {
            'distance': distance,
            'position': position,
            'danger_level': danger_level,
            'guidance': guidance,
            'obstacle_type': self._get_obstacle_type(class_name),
            'requires_action': danger_level in ['critical', 'high'],
            'confidence': confidence
        }
    
    def _generate_obstacle_guidance(self, class_name: str, distance: float, position: str, danger_level: str, confidence: float) -> str:
        """Generate specific guidance for obstacle with confidence consideration"""
        if confidence < self.audio_confidence_threshold:
            return f"Possible {class_name} {position}"
        
        if danger_level == "critical":
            return f"STOP! {class_name} very close {position}!"
        elif danger_level == "high":
            return f"Caution! {class_name} close {position}"
        elif danger_level == "medium":
            return f"{class_name} {position}"
        else:
            return f"{class_name} {position}"
    
    # ... [Keep rest of the methods unchanged] ...

# Compatibility alias
ObjectDetector = EnhancedObjectDetector