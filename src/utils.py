import numpy as np
import cv2
from typing import Tuple, Optional, List, Dict, Any

def calculate_distance(depth_frame, bbox):
    """Calculate distance to an object using depth data"""
    if depth_frame is None:
        return None
        
    x1, y1, x2, y2 = [int(coord) for coord in bbox]
    
    # Ensure coordinates are within frame bounds
    x1 = max(0, min(x1, depth_frame.shape[1] - 1))
    x2 = max(0, min(x2, depth_frame.shape[1] - 1))
    y1 = max(0, min(y1, depth_frame.shape[0] - 1))
    y2 = max(0, min(y2, depth_frame.shape[0] - 1))
    
    if x2 <= x1 or y2 <= y1:
        return None
        
    # Extract region of interest
    roi = depth_frame[y1:y2, x1:x2]
    
    if roi.size == 0:
        return None
        
    # Calculate median distance (more robust than mean)
    distance = np.median(roi)
    
    return distance

def draw_tracking_info(frame, tracks, depth_data=None):
    """Draw tracking information on the frame for visualization"""
    for track in tracks:
        bbox = track['bbox']
        track_id = track['track_id']
        class_name = track['class_name']
        
        # Convert coordinates to integers
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        # Draw bounding box
        color = (0, 255, 0)  # Green
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label background
        label = f"{track_id}: {class_name}"
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        
        cv2.rectangle(
            frame, 
            (x1, y1 - text_height - baseline - 5), 
            (x1 + text_width, y1), 
            color, 
            -1
        )
        
        # Draw label text
        cv2.putText(
            frame, 
            label, 
            (x1, y1 - baseline - 5), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (0, 0, 0),
            1
        )
        
        # Add distance information if available
        if depth_data is not None:
            distance = calculate_distance(depth_data, bbox)
            if distance is not None:
                distance_text = f"{distance:.2f}m"
                cv2.putText(
                    frame, 
                    distance_text, 
                    (x1, y2 + 15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    (0, 255, 0), 
                    1
                )
    
    return frame

def estimate_distance(bbox, frame_w, frame_h):
    x1, y1, x2, y2 = bbox
    area = (x2 - x1) * (y2 - y1)
    frame_area = frame_w * frame_h
    ratio = area / frame_area

    if ratio < 0.002:
        return 4.0
    elif ratio < 0.01:
        return 2.5
    elif ratio < 0.03:
        return 1.5
    elif ratio < 0.08:
        return 1.0
    return 0.5

def estimate_direction(bbox, frame_w):
    cx = (bbox[0] + bbox[2]) / 2
    norm = cx / frame_w

    if norm < 0.33:
        return "left"
    elif norm > 0.66:
        return "right"
    return "center"
