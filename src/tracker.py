import numpy as np
import yaml
import cv2
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Any
import time

class MovementTracker:
    """Simple movement tracking"""
    
    def __init__(self):
        self.object_movements = {}
        
    def update_movement(self, track_id, bbox, frame_width, frame_height, timestamp):
        """Simple movement detection - always return moving for testing"""
        # For now, always return moving to ensure audio triggers
        self.object_movements[track_id] = 'moving'
        return 'moving'
    
    def get_movement_state(self, track_id):
        """Get movement state"""
        return self.object_movements.get(track_id, 'moving')
    
    def cleanup_old_tracks(self, current_time, max_age=5.0):
        """Clean up old tracks"""
        pass

class KalmanBoxTracker:
    """Kalman filter based tracker"""
    count = 0  # Static counter for track IDs
    
    def __init__(self, bbox, class_id, class_name, config, confidence: float = 1.0):
        # Initialize Kalman filter
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        
        # State transition matrix
        self.kf.F = np.array([
            [1,0,0,0,1,0,0],
            [0,1,0,0,0,1,0],
            [0,0,1,0,0,0,1],
            [0,0,0,1,0,0,0],
            [0,0,0,0,1,0,0],
            [0,0,0,0,0,1,0],
            [0,0,0,0,0,0,1]
        ])
        
        # Measurement function
        self.kf.H = np.array([
            [1,0,0,0,0,0,0],
            [0,1,0,0,0,0,0],
            [0,0,1,0,0,0,0],
            [0,0,0,1,0,0,0]
        ])
        
        # Initialize covariance matrices
        self.kf.R = np.eye(4) * 0.1  # Measurement noise
        self.kf.P = np.eye(7) * 10   # Covariance matrix
        self.kf.P[4:,4:] *= 1000     # Give high uncertainty to velocities
        self.kf.Q = np.eye(7) * 0.01 # Process noise
        
        # Initialize state
        self.kf.x[:4] = self.convert_bbox_to_z(bbox)
        
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 1
        self.hit_streak = 1
        self.age = 1
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = float(confidence)
        
        # Velocity tracking for approach detection
        self.position_history = []  # Store (bbox_center_x, bbox_center_y, bbox_area, timestamp)
        self.velocity_x = 0  # Pixels per second
        self.velocity_y = 0
        self.approach_rate = 0  # Negative = approaching, Positive = moving away
    
    def update(self, bbox, confidence: float = None):
        """Update with observed bbox and track velocity"""
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        
        z = self.convert_bbox_to_z(bbox)
        self.kf.update(z)
        
        # Update position history for velocity calculation
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        bbox_area = (x2 - x1) * (y2 - y1)
        
        current_time = time.time()
        self.position_history.append((center_x, center_y, bbox_area, current_time))
        
        # Keep only last 10 positions (about 0.3 seconds at 30 FPS)
        if len(self.position_history) > 10:
            self.position_history.pop(0)
        
        # Calculate velocity when we have enough history
        if len(self.position_history) >= 3:
            self._update_velocity()
        # update confidence if provided
        if confidence is not None:
            try:
                self.confidence = float(confidence)
            except Exception:
                pass
    
    def predict(self):
        """Advance state and return predicted bbox"""
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0
            
        self.kf.predict()
        self.age += 1
        
        if self.time_since_update > 0:
            self.hit_streak = 0
            
        self.time_since_update += 1
        
        current_state = self.convert_x_to_bbox(self.kf.x)
        self.history.append(current_state)
        
        return current_state
    
    def get_state(self):
        """Return current bbox estimate"""
        return self.convert_x_to_bbox(self.kf.x)
    
    def _update_velocity(self):
        """Calculate velocity and approach rate from position history"""
        if len(self.position_history) < 2:
            return
        
        # Get oldest and newest positions
        oldest = self.position_history[0]
        newest = self.position_history[-1]
        
        old_x, old_y, old_area, old_time = oldest
        new_x, new_y, new_area, new_time = newest
        
        dt = new_time - old_time
        if dt <= 0:
            return
        
        # Velocity in pixels per second
        self.velocity_x = (new_x - old_x) / dt if dt > 0 else 0
        self.velocity_y = (new_y - old_y) / dt if dt > 0 else 0
        
        # Approach rate: negative = getting closer, positive = moving away
        # Based on bbox area change (larger area = closer)
        area_change = new_area - old_area
        self.approach_rate = -area_change / dt if dt > 0 else 0  # Negative for approaching
    
    def get_approach_score(self):
        """Get how fast object is approaching (0-100 scale)"""
        if self.approach_rate < 0:  # Approaching
            # Scale to 0-100: larger negative rate = higher score
            return min(100, abs(self.approach_rate) * 2)  # Adjust multiplier for sensitivity
        return 0
    
    def get_velocity_magnitude(self):
        """Get speed of object movement in pixels per second"""
        return (self.velocity_x ** 2 + self.velocity_y ** 2) ** 0.5
    
    @staticmethod
    def convert_bbox_to_z(bbox):
        """Convert bbox to format [x, y, w, h]"""
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        x = x1 + w/2.0
        y = y1 + h/2.0
        return np.array([x, y, w, h]).reshape((4, 1))
    
    @staticmethod
    def convert_x_to_bbox(x, score=None):
        """Convert state vector to bbox format [x1, y1, x2, y2]"""
        if len(x.shape) == 2:
            w = x[2][0]
            h = x[3][0]
            x_center = x[0][0]
            y_center = x[1][0]
        else:
            w = x[2]
            h = x[3]
            x_center = x[0]
            y_center = x[1]
            
        x1 = x_center - w/2.0
        y1 = y_center - h/2.0
        x2 = x_center + w/2.0
        y2 = y_center + h/2.0
        
        if score is None:
            return np.array([x1, y1, x2, y2])
        else:
            return np.array([x1, y1, x2, y2, score])

class ObjectTracker:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.trackers = []
        self.frame_count = 0
        self.max_age = self.config['tracking']['max_age']
        self.min_hits = self.config['tracking']['min_hits']
        self.iou_threshold = self.config['tracking']['iou_threshold']
        
        # Optimization: reduce max_age for low-end devices to free memory faster
        device_profile = self.config.get('device_profile', 'auto')
        if device_profile == 'low':
            self.max_age = max(5, int(self.max_age / 2))  # Reduce max_age for low-end
            print(f"⚡ Tracker optimized for low-end device (max_age={self.max_age})")
        
        # Movement tracking
        self.movement_tracker = MovementTracker()
        self.frame_size = None
        
        print(f"🎯 Tracking {self.min_hits} min hits, {self.max_age} max age, {self.iou_threshold} IOU threshold")
    
    def update(self, detections, frame):
        """Track objects across frames - predict and update tracks"""
        self.frame_count += 1
        
        if self.frame_size is None:
            self.frame_size = (frame.shape[1], frame.shape[0])
        
        current_time = time.time()
        ret = []
        
        print(f"🔍 TRACKER: Processing {len(detections)} detections, {len(self.trackers)} existing trackers")

        # First, predict all existing trackers to their next state
        for trk in self.trackers:
            trk.predict()

        # Create/update tracks for ALL detections
        for det in detections:
            # Track every detected class
            existing_track = None
            for trk in self.trackers:
                if trk.class_name == det['class_name']:
                    # Simple overlap check
                    if self.simple_overlap(trk.get_state(), det['bbox']):
                        existing_track = trk
                        break

            if existing_track:
                # Update existing track (also pass confidence if available)
                existing_track.update(det['bbox'], det.get('confidence', None))
                print(f"✅ Updated track {existing_track.id} for {det['class_name']}")
            else:
                # Create new tracker for every detection
                trk = KalmanBoxTracker(
                    det['bbox'], 
                    det['class_id'],
                    det['class_name'],
                    self.config['kalman'],
                    confidence=det.get('confidence', 1.0)
                )
                self.trackers.append(trk)
                print(f"🆕 Created track {trk.id} for {det['class_name']}")
        
        # Return ALL valid (non-dead) tracks
        i = len(self.trackers)
        for trk in reversed(self.trackers):
            i -= 1
            # If track is old and has not been updated, mark for removal
            if trk.time_since_update > self.max_age:
                self.trackers.pop(i)
                print(f"🗑️ Removed dead track {trk.id}")
            else:
                # Return valid track
                d = trk.get_state()
                movement_state = self.movement_tracker.update_movement(
                    trk.id, d, self.frame_size[0], self.frame_size[1], current_time
                )
                
                ret.append({
                    'bbox': d,
                    'track_id': trk.id,
                    'class_id': trk.class_id,
                    'class_name': trk.class_name,
                    'confidence': getattr(trk, 'confidence', 1.0),
                    'age': trk.age,
                    'hits': trk.hits,
                    'movement_relative': movement_state,
                    'approach_score': trk.get_approach_score(),  # NEW: Approach urgency (0-100)
                    'velocity_magnitude': trk.get_velocity_magnitude(),  # NEW: Speed in pixels/sec
                    'approach_rate': trk.approach_rate  # NEW: Rate of approach (negative = closer)
                })
        
        # Clean up movement history
        self.movement_tracker.cleanup_old_tracks(current_time)
        
        print(f"🎯 Returning {len(ret)} tracks to main system")
        return ret
    
    def simple_overlap(self, bbox1, bbox2):
        """Simple overlap check between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return False
        
        # If centers are close, consider it the same object
        center1_x = (x1_1 + x2_1) / 2
        center1_y = (y1_1 + y2_1) / 2
        center2_x = (x1_2 + x2_2) / 2
        center2_y = (y1_2 + y2_2) / 2
        
        distance = np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
        
        # If centers are within 100 pixels, consider it the same object
        return distance < 100
    
    def iou(self, box1, box2):
        """Calculate IoU between two boxes"""
        # Determine coordinates of intersection rectangle
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        # Calculate area of intersection
        if x2 < x1 or y2 < y1:
            return 0.0
            
        intersection = (x2 - x1) * (y2 - y1)
        
        # Calculate area of both boxes
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        # Avoid division by zero
        union = area1 + area2 - intersection
        if union <= 0:
            return 0.0
        
        # Calculate IoU
        iou = intersection / float(union)
        
        return iou
    
    def reset(self):
        """Reset all trackers"""
        self.trackers = []
        self.frame_count = 0
        self.movement_tracker = MovementTracker()
        KalmanBoxTracker.count = 0




# import numpy as np
# import yaml
# import cv2
# from filterpy.kalman import KalmanFilter
# from scipy.optimize import linear_sum_assignment
# from typing import List, Dict, Any
# import time

# class MovementTracker:
#     """Tracks object movement patterns for intelligent guidance"""
    
#     def __init__(self):
#         self.object_movements = {}
#         self.movement_history = {}
        
#     def update_movement(self, track_id, bbox, frame_width, frame_height, timestamp):
#         """Update movement tracking for an object"""
#         if track_id not in self.movement_history:
#             self.movement_history[track_id] = {
#                 'positions': [],
#                 'timestamps': [],
#                 'sizes': [],
#                 'last_update': timestamp
#             }
        
#         history = self.movement_history[track_id]
        
#         # Calculate center position
#         center_x = (bbox[0] + bbox[2]) / 2
#         center_y = (bbox[1] + bbox[3]) / 2
#         bbox_size = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
#         # Add current data
#         history['positions'].append((center_x, center_y))
#         history['sizes'].append(bbox_size)
#         history['timestamps'].append(timestamp)
#         history['last_update'] = timestamp
        
#         # Keep only recent history (last 3 seconds)
#         cutoff_time = timestamp - 3.0
#         valid_indices = [i for i, ts in enumerate(history['timestamps']) if ts >= cutoff_time]
        
#         history['positions'] = [history['positions'][i] for i in valid_indices]
#         history['timestamps'] = [history['timestamps'][i] for i in valid_indices]
#         history['sizes'] = [history['sizes'][i] for i in valid_indices]
        
#         # Calculate movement state
#         movement_state = self._calculate_movement_state(history, frame_width, frame_height)
#         self.object_movements[track_id] = movement_state
        
#         return movement_state
    
#     def _calculate_movement_state(self, history, frame_width, frame_height):
#         """Calculate movement state based on position and size changes"""
#         if len(history['positions']) < 2:
#             return 'stationary'
        
#         # Calculate position movement
#         recent_positions = history['positions'][-min(5, len(history['positions'])):]
#         x_movements = [recent_positions[i][0] - recent_positions[i-1][0] for i in range(1, len(recent_positions))]
#         y_movements = [recent_positions[i][1] - recent_positions[i-1][1] for i in range(1, len(recent_positions))]
        
#         # Normalize movements by frame size
#         avg_x_movement = np.mean(np.abs(x_movements)) / frame_width if x_movements else 0
#         avg_y_movement = np.mean(np.abs(y_movements)) / frame_height if y_movements else 0
#         total_movement = avg_x_movement + avg_y_movement
        
#         # Calculate size change (indicates approaching/moving away)
#         if len(history['sizes']) >= 2:
#             size_change = history['sizes'][-1] / history['sizes'][0] if history['sizes'][0] > 0 else 1.0
#         else:
#             size_change = 1.0
        
#         # Determine movement state
#         if total_movement > 0.05 or abs(size_change - 1.0) > 0.3:
#             return 'moving'
#         elif total_movement > 0.01 or abs(size_change - 1.0) > 0.1:
#             return 'slightly_moving'
#         else:
#             return 'stationary'
    
#     def get_movement_state(self, track_id):
#         """Get current movement state for a track"""
#         return self.object_movements.get(track_id, 'unknown')
    
#     def cleanup_old_tracks(self, current_time, max_age=5.0):
#         """Remove old tracks from movement history"""
#         to_remove = []
#         for track_id, history in self.movement_history.items():
#             if current_time - history['last_update'] > max_age:
#                 to_remove.append(track_id)
        
#         for track_id in to_remove:
#             del self.movement_history[track_id]
#             if track_id in self.object_movements:
#                 del self.object_movements[track_id]
                
#     def _calculate_movement_state(self, history, frame_width, frame_height):
#         if len(history['positions']) < 2:
#             return 'stationary'
    
#     # Always return 'moving' for testing - REMOVE THIS LATER
#         return 'moving'
    
#     # Original code below (commented for testing)
#     # recent_positions = history['positions'][-min(5, len(history['positions'])):]
#     # x_movements = [recent_positions[i][0] - recent_positions[i-1][0] for i in range(1, len(recent_positions))]
#     # y_movements = [recent_positions[i][1] - recent_positions[i-1][1] for i in range(1, len(recent_positions))]
    
#     # # Simple movement detection
#     # total_movement = sum(abs(x) for x in x_movements) + sum(abs(y) for y in y_movements)
#     # total_movement /= (frame_width + frame_height)  # Normalize
    
#     # if total_movement > 0.02:
#     #     return 'moving'
#     # else:
#     #     return 'stationary'

# class KalmanBoxTracker:
#     """This class represents the internal state of individual tracked objects"""
#     count = 0  # Static counter for track IDs
    
#     def __init__(self, bbox, class_id, class_name, config):
#         # Initialize Kalman filter
#         self.kf = KalmanFilter(dim_x=7, dim_z=4)
        
#         # State transition matrix
#         self.kf.F = np.array([
#             [1,0,0,0,1,0,0],
#             [0,1,0,0,0,1,0],
#             [0,0,1,0,0,0,1],
#             [0,0,0,1,0,0,0],
#             [0,0,0,0,1,0,0],
#             [0,0,0,0,0,1,0],
#             [0,0,0,0,0,0,1]
#         ])
        
#         # Measurement function
#         self.kf.H = np.array([
#             [1,0,0,0,0,0,0],
#             [0,1,0,0,0,0,0],
#             [0,0,1,0,0,0,0],
#             [0,0,0,1,0,0,0]
#         ])
        
#         # Initialize covariance matrices properly
#         self.kf.R = np.eye(4) * config['measurement_noise']  # Measurement noise
#         self.kf.P = np.eye(7) * 10  # Covariance matrix
#         self.kf.P[4:,4:] *= 1000  # Give high uncertainty to the unobservable initial velocities
#         self.kf.Q = np.eye(7) * config['process_noise']  # Process noise
#         self.kf.Q[4:,4:] *= config['process_noise']
        
#         # Initialize state
#         self.kf.x[:4] = self.convert_bbox_to_z(bbox)
        
#         self.time_since_update = 0
#         self.id = KalmanBoxTracker.count
#         KalmanBoxTracker.count += 1
#         self.history = []
#         self.hits = 1
#         self.hit_streak = 1
#         self.age = 1
#         self.class_id = class_id
#         self.class_name = class_name
    
#     def update(self, bbox):
#         """Update the state vector with observed bbox"""
#         self.time_since_update = 0
#         self.history = []
#         self.hits += 1
#         self.hit_streak += 1
        
#         # Convert bbox to measurement format and update
#         z = self.convert_bbox_to_z(bbox)
#         self.kf.update(z)
    
#     def predict(self):
#         """Advance the state vector and return the predicted bounding box"""
#         if (self.kf.x[6] + self.kf.x[2]) <= 0:
#             self.kf.x[6] *= 0.0
            
#         self.kf.predict()
#         self.age += 1
        
#         if self.time_since_update > 0:
#             self.hit_streak = 0
            
#         self.time_since_update += 1
        
#         # Store and return current state
#         current_state = self.convert_x_to_bbox(self.kf.x)
#         self.history.append(current_state)
        
#         return current_state
    
#     def get_state(self):
#         """Return the current bounding box estimate"""
#         return self.convert_x_to_bbox(self.kf.x)
    
#     @staticmethod
#     def convert_bbox_to_z(bbox):
#         """Convert bounding box to format [x, y, w, h]"""
#         x1, y1, x2, y2 = bbox
#         w = x2 - x1
#         h = y2 - y1
#         x = x1 + w/2.0
#         y = y1 + h/2.0
#         return np.array([x, y, w, h]).reshape((4, 1))
    
#     @staticmethod
#     def convert_x_to_bbox(x, score=None):
#         """Convert state vector to bounding box format [x1, y1, x2, y2]"""
#         if len(x.shape) == 2:
#             w = x[2][0]
#             h = x[3][0]
#             x_center = x[0][0]
#             y_center = x[1][0]
#         else:
#             w = x[2]
#             h = x[3]
#             x_center = x[0]
#             y_center = x[1]
            
#         x1 = x_center - w/2.0
#         y1 = y_center - h/2.0
#         x2 = x_center + w/2.0
#         y2 = y_center + h/2.0
        
#         if score is None:
#             return np.array([x1, y1, x2, y2])
#         else:
#             return np.array([x1, y1, x2, y2, score])

# class ObjectTracker:
#     def __init__(self, config_path: str = "config.yaml"):
#         with open(config_path, 'r') as f:
#             self.config = yaml.safe_load(f)
        
#         self.trackers = []
#         self.frame_count = 0
#         self.max_age = self.config['tracking']['max_age']
#         self.min_hits = self.config['tracking']['min_hits']
#         self.iou_threshold = self.config['tracking']['iou_threshold']
        
#         # Enhanced movement tracking
#         self.movement_tracker = MovementTracker()
#         self.frame_size = None
    
#     def update(self, detections, frame):
#         """Update trackers with new detections"""
#         self.frame_count += 1
        
#         if self.frame_size is None:
#             self.frame_size = (frame.shape[1], frame.shape[0])
        
#         # Get predicted locations from existing trackers
#         trk_boxes = []
#         to_del = []
#         ret = []
        
#         for t, trk in enumerate(self.trackers):
#             pos = trk.predict()
            
#             # Check for invalid predictions
#             if np.any(np.isnan(pos)) or np.any(np.isinf(pos)):
#                 to_del.append(t)
#             else:
#                 trk_boxes.append(pos)
                
#         # Remove invalid trackers
#         for t in reversed(to_del):
#             if t < len(self.trackers):
#                 self.trackers.pop(t)
            
#         # Associate detections to trackers
#         if len(trk_boxes) > 0:
#             trk_boxes_array = np.array(trk_boxes)
#             matched, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(
#                 detections, trk_boxes_array
#             )
#         else:
#             matched = np.empty((0, 2), dtype=int)
#             unmatched_dets = np.arange(len(detections))
#             unmatched_trks = np.empty((0,), dtype=int)
        
#         # Update matched trackers with assigned detections
#         for match in matched:
#             if match[0] < len(detections) and match[1] < len(self.trackers):
#                 self.trackers[match[1]].update(detections[match[0]]['bbox'])
                
#         # Create and initialize new trackers for unmatched detections
#         for i in unmatched_dets:
#             if i < len(detections):
#                 trk = KalmanBoxTracker(
#                     detections[i]['bbox'], 
#                     detections[i]['class_id'],
#                     detections[i]['class_name'],
#                     self.config['kalman']
#                 )
#                 self.trackers.append(trk)
            
#         # Return confirmed tracks with movement information
#         current_time = time.time()
#         for trk in self.trackers:
#             d = trk.get_state()
            
#             # Check for valid state
#             if (np.any(np.isnan(d)) or np.any(np.isinf(d)) or
#                 d[2] <= d[0] or d[3] <= d[1]):
#                 continue
                
#             if (trk.time_since_update < 1) and (
#                 trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits
#             ):
#                 # Update movement tracking
#                 movement_state = self.movement_tracker.update_movement(
#                     trk.id, d, self.frame_size[0], self.frame_size[1], current_time
#                 )
                
#                 ret.append({
#                     'bbox': d,
#                     'track_id': trk.id,
#                     'class_id': trk.class_id,
#                     'class_name': trk.class_name,
#                     'age': trk.age,
#                     'hits': trk.hits,
#                     'movement_relative': movement_state  # Add movement information
#                 })
                
#         # Remove dead trackers and clean up movement history
#         i = len(self.trackers)
#         for trk in reversed(self.trackers):
#             i -= 1
#             if trk.time_since_update > self.max_age:
#                 self.trackers.pop(i)
        
#         # Clean up old movement tracks
#         self.movement_tracker.cleanup_old_tracks(current_time)
            
#         return ret
    
#     def associate_detections_to_trackers(self, detections, trk_boxes):
#         """Assign detections to tracked objects"""
#         if len(trk_boxes) == 0 or len(detections) == 0:
#             return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0,), dtype=int)
            
#         iou_matrix = np.zeros((len(detections), len(trk_boxes)), dtype=np.float32)
        
#         for d, det in enumerate(detections):
#             for t, trk in enumerate(trk_boxes):
#                 iou_matrix[d, t] = self.iou(det['bbox'], trk)
                
#         # Solve the assignment problem
#         matched_indices = linear_sum_assignment(-iou_matrix)
#         matched_indices = np.asarray(matched_indices).T
        
#         unmatched_detections = []
#         for d in range(len(detections)):
#             if d not in matched_indices[:, 0]:
#                 unmatched_detections.append(d)
                
#         unmatched_trackers = []
#         for t in range(len(trk_boxes)):
#             if t not in matched_indices[:, 1]:
#                 unmatched_trackers.append(t)
                
#         # Filter out matches with low IOU
#         matches = []
#         for m in matched_indices:
#             if iou_matrix[m[0], m[1]] < self.iou_threshold:
#                 unmatched_detections.append(m[0])
#                 unmatched_trackers.append(m[1])
#             else:
#                 matches.append(m.reshape(1, 2))
                
#         if len(matches) == 0:
#             matches = np.empty((0, 2), dtype=int)
#         else:
#             matches = np.concatenate(matches, axis=0)
            
#         return matches, np.array(unmatched_detections), np.array(unmatched_trackers)
    
#     def iou(self, box1, box2):
#         """Calculate Intersection over Union between two boxes"""
#         # Ensure boxes are valid
#         if (len(box1) < 4 or len(box2) < 4 or 
#             box1[2] <= box1[0] or box1[3] <= box1[1] or
#             box2[2] <= box2[0] or box2[3] <= box2[1]):
#             return 0.0
            
#         # Determine coordinates of intersection rectangle
#         x1 = max(box1[0], box2[0])
#         y1 = max(box1[1], box2[1])
#         x2 = min(box1[2], box2[2])
#         y2 = min(box1[3], box2[3])
        
#         # Calculate area of intersection
#         if x2 < x1 or y2 < y1:
#             return 0.0
            
#         intersection = (x2 - x1) * (y2 - y1)
        
#         # Calculate area of both boxes
#         area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
#         area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
#         # Avoid division by zero
#         union = area1 + area2 - intersection
#         if union <= 0:
#             return 0.0
        
#         # Calculate IoU
#         iou = intersection / float(union)
        
#         return iou
    
#     def reset(self):
#         """Reset all trackers"""
#         self.trackers = []
#         self.frame_count = 0
#         self.movement_tracker = MovementTracker()
#         KalmanBoxTracker.count = 0





# import numpy as np
# import yaml
# import cv2
# from filterpy.kalman import KalmanFilter
# from scipy.optimize import linear_sum_assignment
# from typing import List, Dict, Any

# class KalmanBoxTracker:
#     """This class represents the internal state of individual tracked objects"""
#     count = 0  # Static counter for track IDs
    
#     def __init__(self, bbox, class_id, class_name, config):
#         # Initialize Kalman filter
#         self.kf = KalmanFilter(dim_x=7, dim_z=4)
        
#         # State transition matrix
#         self.kf.F = np.array([
#             [1,0,0,0,1,0,0],
#             [0,1,0,0,0,1,0],
#             [0,0,1,0,0,0,1],
#             [0,0,0,1,0,0,0],
#             [0,0,0,0,1,0,0],
#             [0,0,0,0,0,1,0],
#             [0,0,0,0,0,0,1]
#         ])
        
#         # Measurement function
#         self.kf.H = np.array([
#             [1,0,0,0,0,0,0],
#             [0,1,0,0,0,0,0],
#             [0,0,1,0,0,0,0],
#             [0,0,0,1,0,0,0]
#         ])
        
#         # Initialize covariance matrices properly
#         self.kf.R = np.eye(4) * config['measurement_noise']  # Measurement noise
#         self.kf.P = np.eye(7) * 10  # Covariance matrix
#         self.kf.P[4:,4:] *= 1000  # Give high uncertainty to the unobservable initial velocities
#         self.kf.Q = np.eye(7) * config['process_noise']  # Process noise
#         self.kf.Q[4:,4:] *= config['process_noise']
        
#         # Initialize state
#         self.kf.x[:4] = self.convert_bbox_to_z(bbox)
        
#         self.time_since_update = 0
#         self.id = KalmanBoxTracker.count
#         KalmanBoxTracker.count += 1
#         self.history = []
#         self.hits = 1
#         self.hit_streak = 1
#         self.age = 1
#         self.class_id = class_id
#         self.class_name = class_name
    
#     def update(self, bbox):
#         """Update the state vector with observed bbox"""
#         self.time_since_update = 0
#         self.history = []
#         self.hits += 1
#         self.hit_streak += 1
        
#         # Convert bbox to measurement format and update
#         z = self.convert_bbox_to_z(bbox)
#         self.kf.update(z)
    
#     def predict(self):
#         """Advance the state vector and return the predicted bounding box"""
#         if (self.kf.x[6] + self.kf.x[2]) <= 0:
#             self.kf.x[6] *= 0.0
            
#         self.kf.predict()
#         self.age += 1
        
#         if self.time_since_update > 0:
#             self.hit_streak = 0
            
#         self.time_since_update += 1
        
#         # Store and return current state
#         current_state = self.convert_x_to_bbox(self.kf.x)
#         self.history.append(current_state)
        
#         return current_state
    
#     def get_state(self):
#         """Return the current bounding box estimate"""
#         return self.convert_x_to_bbox(self.kf.x)
    
#     @staticmethod
#     def convert_bbox_to_z(bbox):
#         """Convert bounding box to format [x, y, w, h]"""
#         x1, y1, x2, y2 = bbox
#         w = x2 - x1
#         h = y2 - y1
#         x = x1 + w/2.0
#         y = y1 + h/2.0
#         return np.array([x, y, w, h]).reshape((4, 1))
    
#     @staticmethod
#     def convert_x_to_bbox(x, score=None):
#         """Convert state vector to bounding box format [x1, y1, x2, y2]"""
#         if len(x.shape) == 2:
#             w = x[2][0]
#             h = x[3][0]
#             x_center = x[0][0]
#             y_center = x[1][0]
#         else:
#             w = x[2]
#             h = x[3]
#             x_center = x[0]
#             y_center = x[1]
            
#         x1 = x_center - w/2.0
#         y1 = y_center - h/2.0
#         x2 = x_center + w/2.0
#         y2 = y_center + h/2.0
        
#         if score is None:
#             return np.array([x1, y1, x2, y2])
#         else:
#             return np.array([x1, y1, x2, y2, score])

# class ObjectTracker:
#     def __init__(self, config_path: str = "config.yaml"):
#         with open(config_path, 'r') as f:
#             self.config = yaml.safe_load(f)
        
#         self.trackers = []
#         self.frame_count = 0
#         self.max_age = self.config['tracking']['max_age']
#         self.min_hits = self.config['tracking']['min_hits']
#         self.iou_threshold = self.config['tracking']['iou_threshold']
    
#     def update(self, detections, frame):
#         """Update trackers with new detections"""
#         self.frame_count += 1
        
#         # Get predicted locations from existing trackers
#         trk_boxes = []
#         to_del = []
#         ret = []
        
#         for t, trk in enumerate(self.trackers):
#             pos = trk.predict()
            
#             # Check for invalid predictions
#             if np.any(np.isnan(pos)) or np.any(np.isinf(pos)):
#                 to_del.append(t)
#             else:
#                 trk_boxes.append(pos)
                
#         # Remove invalid trackers
#         for t in reversed(to_del):
#             if t < len(self.trackers):
#                 self.trackers.pop(t)
            
#         # Associate detections to trackers
#         if len(trk_boxes) > 0:
#             trk_boxes_array = np.array(trk_boxes)
#             matched, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(
#                 detections, trk_boxes_array
#             )
#         else:
#             matched = np.empty((0, 2), dtype=int)
#             unmatched_dets = np.arange(len(detections))
#             unmatched_trks = np.empty((0,), dtype=int)
        
#         # Update matched trackers with assigned detections
#         for match in matched:
#             if match[0] < len(detections) and match[1] < len(self.trackers):
#                 self.trackers[match[1]].update(detections[match[0]]['bbox'])
                
#         # Create and initialize new trackers for unmatched detections
#         for i in unmatched_dets:
#             if i < len(detections):
#                 trk = KalmanBoxTracker(
#                     detections[i]['bbox'], 
#                     detections[i]['class_id'],
#                     detections[i]['class_name'],
#                     self.config['kalman']
#                 )
#                 self.trackers.append(trk)
            
#         # Return confirmed tracks
#         for trk in self.trackers:
#             d = trk.get_state()
            
#             # Check for valid state
#             if (np.any(np.isnan(d)) or np.any(np.isinf(d)) or
#                 d[2] <= d[0] or d[3] <= d[1]):
#                 continue
                
#             if (trk.time_since_update < 1) and (
#                 trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits
#             ):
#                 ret.append({
#                     'bbox': d,
#                     'track_id': trk.id,
#                     'class_id': trk.class_id,
#                     'class_name': trk.class_name,
#                     'age': trk.age,
#                     'hits': trk.hits
#                 })
                
#         # Remove dead trackers
#         i = len(self.trackers)
#         for trk in reversed(self.trackers):
#             i -= 1
#             if trk.time_since_update > self.max_age:
#                 self.trackers.pop(i)
            
#         return ret
    
#     def associate_detections_to_trackers(self, detections, trk_boxes):
#         """Assign detections to tracked objects"""
#         if len(trk_boxes) == 0 or len(detections) == 0:
#             return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0,), dtype=int)
            
#         iou_matrix = np.zeros((len(detections), len(trk_boxes)), dtype=np.float32)
        
#         for d, det in enumerate(detections):
#             for t, trk in enumerate(trk_boxes):
#                 iou_matrix[d, t] = self.iou(det['bbox'], trk)
                
#         # Solve the assignment problem
#         matched_indices = linear_sum_assignment(-iou_matrix)
#         matched_indices = np.asarray(matched_indices).T
        
#         unmatched_detections = []
#         for d in range(len(detections)):
#             if d not in matched_indices[:, 0]:
#                 unmatched_detections.append(d)
                
#         unmatched_trackers = []
#         for t in range(len(trk_boxes)):
#             if t not in matched_indices[:, 1]:
#                 unmatched_trackers.append(t)
                
#         # Filter out matches with low IOU
#         matches = []
#         for m in matched_indices:
#             if iou_matrix[m[0], m[1]] < self.iou_threshold:
#                 unmatched_detections.append(m[0])
#                 unmatched_trackers.append(m[1])
#             else:
#                 matches.append(m.reshape(1, 2))
                
#         if len(matches) == 0:
#             matches = np.empty((0, 2), dtype=int)
#         else:
#             matches = np.concatenate(matches, axis=0)
            
#         return matches, np.array(unmatched_detections), np.array(unmatched_trackers)
    
#     def iou(self, box1, box2):
#         """Calculate Intersection over Union between two boxes"""
#         # Ensure boxes are valid
#         if (len(box1) < 4 or len(box2) < 4 or 
#             box1[2] <= box1[0] or box1[3] <= box1[1] or
#             box2[2] <= box2[0] or box2[3] <= box2[1]):
#             return 0.0
            
#         # Determine coordinates of intersection rectangle
#         x1 = max(box1[0], box2[0])
#         y1 = max(box1[1], box2[1])
#         x2 = min(box1[2], box2[2])
#         y2 = min(box1[3], box2[3])
        
#         # Calculate area of intersection
#         if x2 < x1 or y2 < y1:
#             return 0.0
            
#         intersection = (x2 - x1) * (y2 - y1)
        
#         # Calculate area of both boxes
#         area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
#         area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
#         # Avoid division by zero
#         union = area1 + area2 - intersection
#         if union <= 0:
#             return 0.0
        
#         # Calculate IoU
#         iou = intersection / float(union)
        
#         return iou
    
#     def reset(self):
#         """Reset all trackers"""
#         self.trackers = []
#         self.frame_count = 0
#         KalmanBoxTracker.count = 0