import cv2
import yaml
import numpy as np
from typing import Optional, Tuple
import threading
from queue import Queue
import time
import os
import logging

# Suppress OpenCV verbose logging
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'
logging.getLogger('opencv').setLevel(logging.ERROR)

class Camera:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        camera_config = config['camera']
        self.device_id = camera_config['device_id']
        self.width = camera_config['width']
        self.height = camera_config['height']
        self.fps = camera_config['fps']
        
        # Frame buffering for smooth async capture
        self.frame_queue = Queue(maxsize=1)  # Keep only 1 frame (latest) for minimum latency
        self.latest_frame = None
        self.latest_ret = False
        self.is_running = True
        
        self.cap = None
        self.capture_thread = None
        self.initialize_camera()
    
    def initialize_camera(self):
        """Initialize the camera with specified settings"""
        # Suppress OpenCV logs during initialization
        try:
            cv2.setLogLevel(0)  # OFF
        except AttributeError:
            pass  # Older OpenCV versions don't have this
        
        self.cap = cv2.VideoCapture(self.device_id)
        
        if not self.cap.isOpened():
            # Try different camera indices
            for i in range(5):
                self.cap = cv2.VideoCapture(i)
                if self.cap.isOpened():
                    self.device_id = i
                    break
            
            if not self.cap.isOpened():
                raise RuntimeError("Cannot open camera with any device ID")
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        # Minimize buffer to reduce latency - 1 frame only
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Disable autofocus to speed up capture
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        # Reduce exposure calculation time
        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        
        print(f"📹 Camera initialized: {self.width}x{self.height} at {self.fps} FPS")
        
        # Start background capture thread
        self.capture_thread = threading.Thread(target=self._capture_frames, daemon=True)
        self.capture_thread.start()
    
    def _capture_frames(self):
        """Background thread for continuous frame capture"""
        consecutive_failures = 0
        max_consecutive_failures = 30
        
        while self.is_running:
            ret, frame = self.cap.read()
            if ret:
                # Store only the latest frame
                if not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()  # Remove old frame
                    except:
                        pass
                self.latest_frame = frame
                self.latest_ret = ret
                consecutive_failures = 0  # Reset failure counter on success
            else:
                # Camera read failed
                consecutive_failures += 1
                
                # If too many consecutive failures, attempt reconnect
                if consecutive_failures >= max_consecutive_failures:
                    print("⚠️  Camera read failures detected. Attempting reconnect...")
                    try:
                        self.cap.release()
                        time.sleep(0.5)
                        self.cap = cv2.VideoCapture(self.device_id)
                        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        consecutive_failures = 0
                        print("✅ Camera reconnected")
                    except Exception as e:
                        print(f"❌ Failed to reconnect camera: {e}")
                        time.sleep(1)
                else:
                    time.sleep(0.01)  # Brief sleep to avoid busy wait
    
    def get_frame(self, skip_check=False) -> Optional[Tuple[bool, np.ndarray]]:
        """Get the latest captured frame (non-blocking)"""
        if self.latest_frame is None:
            return None
        return self.latest_ret, self.latest_frame.copy()  # Return copy to avoid data race
    
    def get_frame_size(self) -> Tuple[int, int]:
        """Get the frame dimensions"""
        return self.width, self.height
    
    def release(self):
        """Release the camera resource"""
        self.is_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1)
        if self.cap is not None:
            self.cap.release()
    
    def __del__(self):
        self.release()