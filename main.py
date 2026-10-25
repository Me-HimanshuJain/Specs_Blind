# #!/usr/bin/env python3
# """
# Smart Goggle System for Visually Impaired - Complete Enhanced Version
# With intelligent audio guidance and static object detection
# """

# import cv2
# import time
# import yaml
# import numpy as np
# import os
# import sys
# from pathlib import Path
# from typing import List, Dict, Any

# # Add src directory to path
# # This is necessary when running the script from the root directory
# sys.path.append(str(Path(__file__).parent / 'src'))

# # The imports from src are assumed to be available
# try:
#     from src.camera import Camera
#     from src.detector import EnhancedObjectDetector
#     from src.tracker import ObjectTracker
#     from src.audio_feedback import AudioFeedback
#     from src.utils import draw_tracking_info
# except ImportError as e:
#     print(f"Error importing modules from src/: {e}")
#     print("Please ensure you have the 'src' directory with camera.py, detector.py, tracker.py, audio_feedback.py, and utils.py files.")
#     sys.exit(1)


# class SmartGoggleSystem:
#     def __init__(self, config_path="config.yaml"):
#         # Load configuration
#         self.config_path = config_path
#         try:
#             with open(config_path, 'r') as f:
#                 self.config = yaml.safe_load(f)
#         except Exception as e:
#             print(f"Error loading config file: {e}")
#             print("Using default configuration")
#             self.config = self._get_default_config()
        
#         # Auto-detect device profile if set to 'auto'
#         self._detect_and_optimize_device()
        
#         # Initialize components
#         try:
#             # Assuming Camera, Detector, Tracker, AudioFeedback constructors handle the config correctly
#             self.camera = Camera(config_path)
#             self.detector = EnhancedObjectDetector(config_path)
#             self.tracker = ObjectTracker(config_path)
#             self.audio_feedback = AudioFeedback(config_path)
#         except Exception as e:
#             print(f"Error initializing components: {e}")
#             raise
        
#         # Performance monitoring
#         self.frame_count = 0
#         self.start_time = time.time()
#         self.fps = 0
        
#         # State variables
#         self.is_running = False
#         self.visualization = True
#         self.paused = False
        
#         print("🎯 Enhanced Smart Goggle System initialized successfully!")
#         print("📦 Comprehensive obstacle detection: ENABLED")
#         print("🧱 Wall detection: ENABLED")
#         print("🔊 Intelligent audio guidance: ENABLED")
#         print("🎯 Directional guidance: ENABLED")
        
#         # Test audio at startup
#         print("\n🔧 Testing audio system...")
#         self.audio_feedback.test_tts()  # Direct TTS test first
#         time.sleep(1)
#         self.audio_feedback.speak("Smart goggle system activated. I will guide you with distance information for obstacles ahead.")
#         time.sleep(2)
    
#     def _detect_and_optimize_device(self):
#         """Device detection - all features enabled for all devices"""
#         device_profile = self.config.get('device_profile', 'full')
#         print(f"🎯 Device profile: {device_profile} - ALL FEATURES ENABLED")
#         self.config['device_profile'] = 'full'
    
#     def _get_default_config(self):
#         """Get default configuration - all features enabled on all devices"""
#         return {
#             'device_profile': 'full',
#             'camera': {'device_id': 0, 'width': 640, 'height': 480, 'fps': 60},
#             'yolo': {'model_path': 'yolov8n.pt', 'confidence_threshold': 0.3, 'iou_threshold': 0.45, 'detection_frequency': 1, 'inference_size': 416, 'half_precision': False},
#             'kalman': {'state_dim': 7, 'measurement_dim': 4, 'process_noise': 0.01, 'measurement_noise': 0.1},
#             'tracking': {'max_age': 10, 'min_hits': 1, 'iou_threshold': 0.3},
#             'audio': {
#                 'min_distance': 0.3, 
#                 'max_distance': 15.0, 
#                 'update_interval': 0.5,
#                 'language': 'en', 
#                 'volume': 0.9, 
#                 'rate': 160,
#                 'announcement_intervals': {
#                     'person_moving': 1.0,
#                     'person_stationary': 3.0,
#                     'vehicle_moving': 0.8,
#                     'vehicle_stationary': 2.0,
#                     'obstacle_moving': 1.2,
#                     'obstacle_stationary': 4.0,
#                     'static_object': 6.0
#                 }
#             },
#             'regions': {'center_threshold': 0.3, 'positions': ['far left', 'left', 'center', 'right', 'far right']},
#             'guidance': {'safe_distance': 2.0, 'warning_distance': 1.0, 'critical_distance': 0.5},
#             'static_objects': {
#                 'enabled': True,
#                 'important_objects': ["chair", "dining table", "bed", "couch", "person", "car", "bottle", "cup"],
#                 'min_confidence': 0.25
#             }
#         }
    
#     def run(self):
#         """Main loop of the smart goggle system"""
#         self.is_running = True
#         print("🚀 Starting Enhanced Smart Goggle System...")
#         print("🔧 Controls: 'q'=quit, 'p'=pause, 'v'=visualization")
#         print("🎵 'a'=audio test, 'c'=clear history, 's'=status")
#         print("⚙️ Mode: All features enabled - Optimized async processing")
        
#         try:
#             while self.is_running:
#                 if self.paused:
#                     key = cv2.waitKey(1) & 0xFF
#                     if key == ord('p'):
#                         self.paused = False
#                         print("▶️ Resumed")
#                     elif key == ord('q'):
#                         break
#                     continue
                
#                 # Capture frame from camera
#                 try:
#                     result = self.camera.get_frame()
#                     if result is None:
#                         time.sleep(0.001)
#                         continue
                        
#                     ret, frame = result
#                     if not ret:
#                         time.sleep(0.001)
#                         continue
#                 except Exception as e:
#                     print(f"❌ Error capturing frame: {e}")
#                     time.sleep(0.01)
#                     continue
                
#                 # Calculate FPS
#                 self.frame_count += 1
#                 if self.frame_count % 30 == 0:
#                     elapsed = time.time() - self.start_time
#                     self.fps = 30 / elapsed if elapsed > 0 else 0
#                     self.start_time = time.time()
                
#                 # Run COMPREHENSIVE object detection (including walls)
#                 detections = []
#                 try:
#                     detections = self.detector.detect_enhanced(frame)
#                     if detections:
#                         # Log up to first 8 detected class names for debugging
#                         classes = [d.get('class_name', 'unknown') for d in detections][:8]
#                         print(f"📹 Detections ({len(detections)}): {', '.join(classes)}")
#                 except Exception as e:
#                     print(f"❌ Detection error: {e}")
#                     detections = []
                
#                 # --- START: Updated Tracker Block with Debugging ---
#                 tracks: List[Dict[str, Any]] = []
#                 try:
#                     tracks = self.tracker.update(detections, frame)
                    
#                     # DEBUG: Check what's happening in tracker
#                     if detections and not tracks:
#                         print(f"❌ TRACKER ISSUE: {len(detections)} detections but 0 tracks created!")
#                         for det in detections[:3]: # Show first 3 detections
#                             print(f"  - Detection: {det['class_name']} at {det['bbox']}")
#                     # The original simplified update prints detailed logs, so let's only log when tracks are found.
#                     elif tracks and self.frame_count % 30 == 0:
#                         print(f"✅ TRACKER: Maintaining {len(tracks)} tracks. New detections: {len(detections)}")
                        
#                 except Exception as e:
#                     print(f"❌ Tracking error: {e}")
#                     tracks = []
#                 # --- END: Updated Tracker Block with Debugging ---

                
#                 # Provide ENHANCED intelligent audio guidance with distance info
#                 audio_triggered = False
#                 try:
#                     frame_width = self.config['camera']['width']
#                     frame_height = self.config['camera']['height']
    
#                     # DEBUG: Print tracks before sending to audio
#                     # if tracks and self.frame_count % 30 == 0:
#                     #     print(f"🎯 MAIN: Sending {len(tracks)} tracks to audio system")
#                     #     for track in tracks[:3]: # Log first 3 tracks
#                     #         print(f"   - Track: {track['class_name']} (ID:{track['track_id']}) - {track.get('movement_relative', '??')}")
    
#                     # Primary intelligent guidance (per-object/state)
#                     audio_triggered = self.audio_feedback.provide_intelligent_guidance(tracks, frame_width, frame_height)
#                     # Fallback global announcer to ensure audible feedback (throttled)
#                     if not audio_triggered:
#                         audio_triggered = self.audio_feedback.announce_tracks(tracks, frame_width, frame_height)
    
#                 except Exception as e:
#                     print(f"❌ Audio feedback error: {e}")
                
                
#                 if self.visualization:
#                     try:
#                         display_frame = self._create_visualization(frame, tracks, detections, audio_triggered)
#                         cv2.imshow('Enhanced Smart Goggles', display_frame)
#                     except Exception as e:
#                         print(f"❌ Visualization error: {e}")
#                         cv2.imshow('Enhanced Smart Goggles', frame)
                    
#                     # Check for key press
#                     key = cv2.waitKey(1) & 0xFF
#                     if key == ord('q'):
#                         break
#                     elif key == ord('p'):
#                         self.paused = True
#                         print("⏸️ Paused")
#                     elif key == ord('v'):
#                         self.visualization = not self.visualization
#                         print(f"👁️ Visualization: {'ON' if self.visualization else 'OFF'}")
#                     elif key == ord('a'):
#                         self.audio_feedback.speak("Audio test: Table 3 meters ahead, Person 2 meters left, Bottle 1 meter right")
#                     elif key == ord('c'):
#                         self.audio_feedback.clear_history()
#                         self.tracker.reset() # Also reset tracker when clearing history
#                         print("🗑️ Object history and tracker cleared")
#                     elif key == ord('s'):
#                         self._show_system_status(tracks)
#                 else:
#                     # If no visualization, still check for key presses
#                     key = cv2.waitKey(1) & 0xFF
#                     if key == ord('q'):
#                         break
#                     elif key == ord('p'):
#                         self.paused = True
#                         print("⏸️ Paused")
#                     elif key == ord('v'):
#                         self.visualization = True
#                         print("👁️ Visualization: ON")
#                     elif key == ord('a'):
#                         self.audio_feedback.speak("Audio test confirmed")
#                     elif key == ord('c'):
#                         self.audio_feedback.clear_history()
#                         self.tracker.reset()
#                     elif key == ord('s'):
#                         self._show_system_status(tracks)
        
#         except KeyboardInterrupt:
#             print("\n🛑 Shutting down...")
#         except Exception as e:
#             print(f"💥 Unexpected error: {e}")
#         finally:
#             self.cleanup()
    
#     def _create_visualization(self, frame, tracks, detections, audio_triggered):
#         """Create enhanced visualization with smart audio info"""
#         display_frame = draw_tracking_info(frame.copy(), tracks)
        
#         # Add enhanced status information
#         wall_count = len([t for t in tracks if t.get('class_name') == 'wall'])
#         critical_count = len([t for t in tracks if t.get('danger_level') == 'critical'])
        
#         status_text = f"FPS: {self.fps:.1f} | Objects: {len(tracks)} | Walls: {wall_count} | Critical: {critical_count}"
#         cv2.putText(
#             display_frame, 
#             status_text, 
#             (10, 30), 
#             cv2.FONT_HERSHEY_SIMPLEX, 
#             0.6, 
#             (0, 255, 0) if audio_triggered else (255, 255, 255), 
#             2
#         )
        
#         # Add audio status
#         audio_status = "SPEAKING" if audio_triggered else "monitoring"
#         cv2.putText(
#             display_frame, 
#             f"Audio: {audio_status}", 
#             (10, 55), 
#             cv2.FONT_HERSHEY_SIMPLEX, 
#             0.5, 
#             (0, 255, 0) if audio_triggered else (200, 200, 200), 
#             2
#         )
        
#         # List tracked objects with enhanced information
#         y_offset = 60
#         for i, track in enumerate(tracks[:8]): # Show first 8 objects
#             frame_width = self.config['camera']['width']
#             # frame_height is unused in this block, but kept for consistency
#             frame_height = self.config['camera']['height'] 
            
#             # Use enhanced detection information if available
#             if 'distance' in track:
#                 distance = track['distance']
#                 danger_level = track.get('danger_level', 'low')
#                 position = track.get('position', 'unknown')
#             else:
#                 # Fallback to audio feedback calculation
#                 distance = self.audio_feedback.estimate_distance(track['bbox'], frame_width, frame_height)
#                 movement_state = track.get('movement_relative', 'unknown')
#                 danger_level = self.audio_feedback.assess_danger_level(track, distance, movement_state)
#                 position = self.audio_feedback.get_position(track['bbox'], frame_width)
            
#             movement_state = track.get('movement_relative', 'unknown')
            
#             # Color code based on danger level
#             color_map = {'critical': (0, 0, 255), 'high': (0, 165, 255), 'medium': (0, 255, 255), 'low': (0, 255, 0)}
#             color = color_map.get(danger_level, (255, 255, 255))
            
#             # Enhanced object text with guidance
#             guidance = track.get('guidance', '')
#             if guidance:
#                 obj_text = f"ID:{track['track_id']} {track['class_name']}: {distance:.1f}m {position} ({danger_level})"
#             else:
#                 obj_text = f"ID:{track['track_id']} {track['class_name']}: {distance:.1f}m {position} - {movement_state}"
#             cv2.putText(
#                 display_frame,
#                 obj_text,
#                 (10, y_offset),
#                 cv2.FONT_HERSHEY_SIMPLEX,
#                 0.5,
#                 color,
#                 1
#             )
#             y_offset += 25
        
#         # Add controls help
#         help_text = "q=quit, p=pause, v=toggle vis, a=audio test, c=clear, s=status"
#         cv2.putText(
#             display_frame,
#             help_text,
#             (10, frame.shape[0] - 10),
#             cv2.FONT_HERSHEY_SIMPLEX,
#             0.4,
#             (200, 200, 200),
#             1
#         )
        
#         return display_frame
    
#     def _show_system_status(self, tracks):
#         """Show system status in console"""
#         print(f"\n{'='*50}")
#         print("🎯 ENHANCED SYSTEM STATUS")
#         print(f"{'='*50}")
#         print(f"📊 FPS: {self.fps:.1f}")
#         print(f"🎯 Tracked objects: {len(tracks)}")
#         print(f"📦 Static detection: ACTIVE")
#         print(f"🔊 Audio guidance: INTELLIGENT MODE")
        
#         if tracks:
#             print(f"| {'Object':12} | {'Dist':4} | {'Position':12} | {'Movement':8} | {'Danger':8} |")
#             print(f"|{'-'*13}|{'-'*6}|{'-'*14}|{'-'*10}|{'-'*10}|")
#             for track in tracks:
#                 frame_width = self.config['camera']['width']
#                 frame_height = self.config['camera']['height']
#                 distance = self.audio_feedback.estimate_intelligent_distance(
#                     track['bbox'], frame_width, frame_height
#                 )
#                 movement = track.get('movement_relative', 'unknown')
#                 danger = self.audio_feedback.assess_danger_level(track, distance, movement)
#                 position = self.audio_feedback.get_intelligent_position(track['bbox'], frame_width)
                
#                 print(f"| {track['class_name']:12} | {distance:4.1f} | {position:12} | {movement:8} | {danger:8} |")
#         else:
#             print("  🌉 No objects currently tracked - Path is clear")
#         print(f"{'='*50}\n")
    
#     def cleanup(self):
#         """Clean up resources"""
#         self.is_running = False
#         self.audio_feedback.speak("System shutting down. Stay safe.")
#         time.sleep(1)
#         self.camera.release()
#         cv2.destroyAllWindows()
#         print("✅ Enhanced system shut down cleanly")

# def main():
#     """Main function"""
#     print("🎯" + "="*50)
#     print("        SMART GOGGLE SYSTEM - ENHANCED VERSION")
#     print("      Intelligent Audio Guidance + Static Object Detection")
#     print("🎯" + "="*50)
    
#     try:
#         # Check if config.yaml exists before starting
#         if not os.path.exists("config.yaml"):
#             print("WARNING: 'config.yaml' not found. Creating a default config file.")
#             default_config = SmartGoggleSystem(config_path=None)._get_default_config()
#             with open("config.yaml", 'w') as f:
#                 yaml.dump(default_config, f)
#             print("Please adjust 'config.yaml' for your system and restart.")
#             # Do not exit, continue with default settings.

#         system = SmartGoggleSystem()
#         system.run()
#     except Exception as e:
#         print(f"❌ Failed to start system: {e}")
#         print("💡 Please check: Camera connection | Dependencies | YOLO model | config.yaml settings")

# if __name__ == "__main__":
#     main()




# # #!/usr/bin/env python3
# # """
# # Smart Goggle System for Visually Impaired - Complete Enhanced Version
# # With intelligent audio guidance and static object detection
# # """

# # import cv2
# # import time
# # import yaml
# # import numpy as np
# # import os
# # import sys
# # from pathlib import Path

# # # Add src directory to path
# # sys.path.append(str(Path(__file__).parent / 'src'))

# # from src.camera import Camera
# # from src.detector import EnhancedObjectDetector
# # from src.tracker import ObjectTracker
# # from src.audio_feedback import AudioFeedback
# # from src.utils import draw_tracking_info

# # class SmartGoggleSystem:
# #     def __init__(self, config_path="config.yaml"):
# #         # Load configuration
# #         self.config_path = config_path
# #         try:
# #             with open(config_path, 'r') as f:
# #                 self.config = yaml.safe_load(f)
# #         except Exception as e:
# #             print(f"Error loading config file: {e}")
# #             print("Using default configuration")
# #             self.config = self._get_default_config()
        
# #         # Initialize components
# #         try:
# #             self.camera = Camera(config_path)
# #             self.detector = EnhancedObjectDetector(config_path)
# #             self.tracker = ObjectTracker(config_path)
# #             self.audio_feedback = AudioFeedback(config_path)
# #         except Exception as e:
# #             print(f"Error initializing components: {e}")
# #             raise
        
# #         # Performance monitoring
# #         self.frame_count = 0
# #         self.start_time = time.time()
# #         self.fps = 0
        
# #         # State variables
# #         self.is_running = False
# #         self.visualization = True
# #         self.paused = False
        
# #         print("🎯 Enhanced Smart Goggle System initialized successfully!")
# #         print("📦 Static object detection: ENABLED")
# #         print("🔊 Intelligent audio guidance: ENABLED")
        
# #         # Test audio at startup
# #         print("Testing audio system...")
# #         self.audio_feedback.speak("Smart goggle system activated. I will guide you with distance information for obstacles ahead.")
# #         time.sleep(2)
    
# #     def _get_default_config(self):
# #         """Get default configuration with enhanced audio settings"""
# #         return {
# #             'camera': {'device_id': 0, 'width': 640, 'height': 480, 'fps': 30},
# #             'yolo': {'model_path': 'yolov8n.pt', 'confidence_threshold': 0.3, 'iou_threshold': 0.45, 'detection_frequency': 5},
# #             'kalman': {'state_dim': 7, 'measurement_dim': 4, 'process_noise': 0.01, 'measurement_noise': 0.1},
# #             'tracking': {'max_age': 20, 'min_hits': 3, 'iou_threshold': 0.3},
# #             'audio': {
# #                 'min_distance': 0.5, 
# #                 'max_distance': 10.0, 
# #                 'update_interval': 1.5, 
# #                 'language': 'en', 
# #                 'volume': 0.9, 
# #                 'rate': 150,
# #                 'announcement_intervals': {
# #                     'person_moving': 2.0,
# #                     'person_stationary': 6.0,
# #                     'vehicle_moving': 1.5,
# #                     'vehicle_stationary': 4.0,
# #                     'obstacle_moving': 3.0,
# #                     'obstacle_stationary': 8.0,
# #                     'static_object': 12.0
# #                 }
# #             },
# #             'regions': {'center_threshold': 0.3, 'positions': ['far left', 'left', 'center', 'right', 'far right']},
# #             'guidance': {'safe_distance': 2.0, 'warning_distance': 1.0, 'critical_distance': 0.5},
# #             'static_objects': {
# #                 'enabled': True,
# #                 'important_objects': ["chair", "dining table", "bed", "couch", "person", "car", "bottle", "cup"],
# #                 'min_confidence': 0.25
# #             }
# #         }
    
# #     def run(self):
# #         """Main loop of the smart goggle system"""
# #         self.is_running = True
# #         print("🚀 Starting Enhanced Smart Goggle System...")
# #         print("🔧 Controls: 'q'=quit, 'p'=pause, 'v'=visualization")
# #         print("🎵 'a'=audio test, 'c'=clear history, 's'=status")
        
# #         try:
# #             while self.is_running:
# #                 if self.paused:
# #                     key = cv2.waitKey(1) & 0xFF
# #                     if key == ord('p'):
# #                         self.paused = False
# #                         print("▶️ Resumed")
# #                     elif key == ord('q'):
# #                         break
# #                     continue
                
# #                 # Capture frame from camera
# #                 try:
# #                     result = self.camera.get_frame()
# #                     if result is None:
# #                         time.sleep(0.1)
# #                         continue
                        
# #                     ret, frame = result
# #                     if not ret:
# #                         time.sleep(0.1)
# #                         continue
# #                 except Exception as e:
# #                     print(f"❌ Error capturing frame: {e}")
# #                     time.sleep(0.1)
# #                     continue
                
# #                 # Calculate FPS
# #                 self.frame_count += 1
# #                 if self.frame_count % 30 == 0:
# #                     elapsed = time.time() - self.start_time
# #                     self.fps = 30 / elapsed if elapsed > 0 else 0
# #                     self.start_time = time.time()
                
# #                 # Run ENHANCED object detection
# #                 detections = []
# #                 try:
# #                     if self.frame_count % self.config['yolo']['detection_frequency'] == 0:
# #                         detections = self.detector.detect_enhanced(frame)
# #                         if detections:
# #                             # Log important detections only
# #                             important_dets = [d for d in detections if d['class_name'] in self.detector.important_objects]
# #                             if important_dets:
# #                                 for det in important_dets[:3]:  # Log first 3 important objects
# #                                     print(f"📹 Detected: {det['class_name']} (conf: {det['confidence']:.2f})")
# #                 except Exception as e:
# #                     print(f"❌ Detection error: {e}")
# #                     detections = []
                
# #                 # Update tracker with detections
# #                 tracks = []
# #                 try:
# #                     tracks = self.tracker.update(detections, frame)
# #                 except Exception as e:
# #                     print(f"❌ Tracking error: {e}")
# #                     tracks = []
                
# #                 # # Provide INTELLIGENT AUDIO GUIDANCE
# #                 # audio_triggered = False
# #                 # try:
# #                 #     frame_width = self.config['camera']['width']
# #                 #     frame_height = self.config['camera']['height']
# #                 #     audio_triggered = self.audio_feedback.provide_intelligent_guidance(tracks, frame_width, frame_height)
                    
# #                 # except Exception as e:
# #                 #     print(f"❌ Audio feedback error: {e}")
                
# #                 # Visualization
# #                 # Provide ENHANCED intelligent audio guidance with distance info
# #                 audio_triggered = False
# #                 try:
# #                     frame_width = self.config['camera']['width']
# #                     frame_height = self.config['camera']['height']
    
# #                     # DEBUG: Print tracks before sending to audio
# #                     if tracks:
# #                         print(f"🎯 MAIN: Sending {len(tracks)} tracks to audio system")
# #                         for track in tracks:
# #                             print(f"   - Track: {track['class_name']} (ID:{track['track_id']})")
    
# #                     audio_triggered = self.audio_feedback.provide_intelligent_guidance(tracks, frame_width, frame_height)
    
# #                 except Exception as e:
# #                     print(f"❌ Audio feedback error: {e}")
                
                
# #                 if self.visualization:
# #                     try:
# #                         display_frame = self._create_visualization(frame, tracks, detections, audio_triggered)
# #                         cv2.imshow('Enhanced Smart Goggles', display_frame)
# #                     except Exception as e:
# #                         print(f"❌ Visualization error: {e}")
# #                         cv2.imshow('Enhanced Smart Goggles', frame)
                    
# #                     # Check for key press
# #                     key = cv2.waitKey(1) & 0xFF
# #                     if key == ord('q'):
# #                         break
# #                     elif key == ord('p'):
# #                         self.paused = True
# #                         print("⏸️ Paused")
# #                     elif key == ord('v'):
# #                         self.visualization = not self.visualization
# #                         print(f"👁️ Visualization: {'ON' if self.visualization else 'OFF'}")
# #                     elif key == ord('a'):
# #                         self.audio_feedback.speak("Audio test: Table 3 meters ahead, Person 2 meters left, Bottle 1 meter right")
# #                     elif key == ord('c'):
# #                         self.audio_feedback.clear_history()
# #                         print("🗑️ Object history cleared")
# #                     elif key == ord('s'):
# #                         self._show_system_status(tracks)
# #                 else:
# #                     # If no visualization, still check for key presses
# #                     key = cv2.waitKey(1) & 0xFF
# #                     if key == ord('q'):
# #                         break
# #                     elif key == ord('p'):
# #                         self.paused = True
# #                         print("⏸️ Paused")
# #                     elif key == ord('v'):
# #                         self.visualization = True
# #                         print("👁️ Visualization: ON")
# #                     elif key == ord('a'):
# #                         self.audio_feedback.speak("Audio test confirmed")
# #                     elif key == ord('c'):
# #                         self.audio_feedback.clear_history()
# #                     elif key == ord('s'):
# #                         self._show_system_status(tracks)
        
# #         except KeyboardInterrupt:
# #             print("\n🛑 Shutting down...")
# #         except Exception as e:
# #             print(f"💥 Unexpected error: {e}")
# #         finally:
# #             self.cleanup()
    
# #     def _create_visualization(self, frame, tracks, detections, audio_triggered):
# #         """Create enhanced visualization with smart audio info"""
# #         display_frame = draw_tracking_info(frame.copy(), tracks)
        
# #         # Add FPS counter
# #         status_text = f"FPS: {self.fps:.1f} | Objects: {len(tracks)} | Audio: {'SPEAKING' if audio_triggered else 'monitoring'}"
# #         cv2.putText(
# #             display_frame, 
# #             status_text, 
# #             (10, 30), 
# #             cv2.FONT_HERSHEY_SIMPLEX, 
# #             0.6, 
# #             (0, 255, 0) if audio_triggered else (255, 255, 255), 
# #             2
# #         )
        
# #         # List tracked objects with enhanced information
# #         y_offset = 60
# #         for i, track in enumerate(tracks[:8]):  # Show first 8 objects
# #             frame_width = self.config['camera']['width']
# #             frame_height = self.config['camera']['height']
# #             distance = self.audio_feedback.estimate_intelligent_distance(
# #                 track['bbox'], track['class_name'], frame_width, frame_height
# #             )
            
# #             movement_state = track.get('movement_relative', 'unknown')
# #             danger_level = self.audio_feedback.assess_danger_level(track, distance, movement_state)
# #             position = self.audio_feedback.get_intelligent_position(track['bbox'], frame_width)
            
# #             # Color code based on danger level
# #             color_map = {'critical': (0, 0, 255), 'high': (0, 165, 255), 'medium': (0, 255, 255), 'low': (0, 255, 0)}
# #             color = color_map.get(danger_level, (255, 255, 255))
            
# #             obj_text = f"{track['class_name']}: {distance}m {position} - {movement_state}"
# #             cv2.putText(
# #                 display_frame,
# #                 obj_text,
# #                 (10, y_offset),
# #                 cv2.FONT_HERSHEY_SIMPLEX,
# #                 0.5,
# #                 color,
# #                 1
# #             )
# #             y_offset += 25
        
# #         # Add controls help
# #         help_text = "q=quit, p=pause, v=toggle vis, a=audio test, c=clear, s=status"
# #         cv2.putText(
# #             display_frame,
# #             help_text,
# #             (10, frame.shape[0] - 10),
# #             cv2.FONT_HERSHEY_SIMPLEX,
# #             0.4,
# #             (200, 200, 200),
# #             1
# #         )
        
# #         return display_frame
    
# #     def _show_system_status(self, tracks):
# #         """Show system status in console"""
# #         print(f"\n{'='*50}")
# #         print("🎯 ENHANCED SYSTEM STATUS")
# #         print(f"{'='*50}")
# #         print(f"📊 FPS: {self.fps:.1f}")
# #         print(f"🎯 Tracked objects: {len(tracks)}")
# #         print(f"📦 Static detection: ACTIVE")
# #         print(f"🔊 Audio guidance: INTELLIGENT MODE")
        
# #         if tracks:
# #             for track in tracks:
# #                 frame_width = self.config['camera']['width']
# #                 frame_height = self.config['camera']['height']
# #                 distance = self.audio_feedback.estimate_intelligent_distance(
# #                     track['bbox'], track['class_name'], frame_width, frame_height
# #                 )
# #                 movement = track.get('movement_relative', 'unknown')
# #                 danger = self.audio_feedback.assess_danger_level(track, distance, movement)
# #                 position = self.audio_feedback.get_intelligent_position(track['bbox'], frame_width)
                
# #                 print(f"  📍 {track['class_name']:12} | {distance:4.1f}m | {position:12} | {movement:8} | {danger:8}")
# #         else:
# #             print("  🌉 No objects currently tracked - Path is clear")
# #         print(f"{'='*50}\n")
    
# #     def cleanup(self):
# #         """Clean up resources"""
# #         self.is_running = False
# #         self.audio_feedback.speak("System shutting down. Stay safe.")
# #         time.sleep(1)
# #         self.camera.release()
# #         cv2.destroyAllWindows()
# #         print("✅ Enhanced system shut down cleanly")

# # def main():
# #     """Main function"""
# #     print("🎯" + "="*50)
# #     print("           SMART GOGGLE SYSTEM - ENHANCED VERSION")
# #     print("      Intelligent Audio Guidance + Static Object Detection")
# #     print("🎯" + "="*50)
    
# #     try:
# #         system = SmartGoggleSystem()
# #         system.run()
# #     except Exception as e:
# #         print(f"❌ Failed to start system: {e}")
# #         print("💡 Please check: Camera connection | Dependencies | YOLO model")

# # if __name__ == "__main__":
# #     main()


#!/usr/bin/env python3
"""
Smart Goggle System for Visually Impaired - Complete Enhanced Version
With intelligent audio guidance and static object detection
"""

import cv2
import time
import yaml
import numpy as np
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

try:
    from src.camera import Camera
    from src.detector import EnhancedObjectDetector
    from src.tracker import ObjectTracker
    from src.audio_feedback import AudioFeedback
    from src.utils import draw_tracking_info
except ImportError as e:
    print(f"Error importing modules from src/: {e}")
    print("Please ensure you have the 'src' directory with camera.py, detector.py, tracker.py, audio_feedback.py, and utils.py files.")
    sys.exit(1)


class SmartGoggleSystem:
    def __init__(self, config_path="config.yaml"):
        # Load configuration
        self.config_path = config_path
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration")
            self.config = self._get_default_config()
        
        # Initialize components with proper configuration
        try:
            self.camera = Camera(config_path)
            self.detector = EnhancedObjectDetector(config_path)
            self.tracker = ObjectTracker(config_path)
            # Pass confidence threshold from config to audio system
            audio_config = self.config.get('audio', {})
            # Ensure confidence threshold is passed
            if 'confidence_threshold' not in audio_config:
                audio_config['confidence_threshold'] = 0.6
            self.audio_feedback = AudioFeedback(config_path)
        except Exception as e:
            print(f"Error initializing components: {e}")
            raise
        
        # Performance monitoring
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0
        
        # State variables
        self.is_running = False
        self.visualization = True
        self.paused = False
        
        # Audio trigger tracking
        self.last_audio_time = 0
        self.audio_cooldown = 1.0  # Minimum 1 second between audio triggers
        
        print("🎯 Enhanced Smart Goggle System initialized successfully!")
        print(f"🎯 Confidence threshold: {audio_config.get('confidence_threshold', 0.6)}")
        print("🔊 Priority-based audio: ENABLED")
        print("🛡️ Anti-spam protection: ENABLED")
        
        # Test audio at startup
        print("\n🔧 Testing audio system...")
        self.audio_feedback.test_tts()  # Direct TTS test first
        time.sleep(1)
        # Shorter startup message
        self.audio_feedback.speak("System ready. I will guide you.")
        time.sleep(1)
    
    def _get_default_config(self):
        """Get default configuration - all features enabled on all devices"""
        return {
            'device_profile': 'full',
            'camera': {'device_id': 0, 'width': 640, 'height': 480, 'fps': 60},
            'yolo': {'model_path': 'yolov8n.pt', 'confidence_threshold': 0.3, 'iou_threshold': 0.45, 'detection_frequency': 1, 'inference_size': 416, 'half_precision': False},
            'kalman': {'state_dim': 7, 'measurement_dim': 4, 'process_noise': 0.01, 'measurement_noise': 0.1},
            'tracking': {'max_age': 10, 'min_hits': 1, 'iou_threshold': 0.3},
            'audio': {
                'min_distance': 0.3, 
                'max_distance': 15.0, 
                'update_interval': 0.5,
                'language': 'en', 
                'volume': 0.9, 
                'rate': 160,
                'confidence_threshold': 0.6,  # NEW: Added confidence threshold
                'announcement_intervals': {
                    'person_moving': 1.0,
                    'person_stationary': 3.0,
                    'vehicle_moving': 0.8,
                    'vehicle_stationary': 2.0,
                    'obstacle_moving': 1.2,
                    'obstacle_stationary': 4.0,
                    'static_object': 6.0
                }
            },
            'regions': {'center_threshold': 0.3, 'positions': ['far left', 'left', 'center', 'right', 'far right']},
            'guidance': {'safe_distance': 2.0, 'warning_distance': 1.0, 'critical_distance': 0.5},
            'static_objects': {
                'enabled': True,
                'important_objects': ["chair", "dining table", "bed", "couch", "person", "car", "bottle", "cup"],
                'min_confidence': 0.25
            }
        }
    
    def run(self):
        """Main loop of the smart goggle system"""
        self.is_running = True
        print("🚀 Starting Enhanced Smart Goggle System...")
        print("🔧 Controls: 'q'=quit, 'p'=pause, 'v'=visualization")
        print("🎵 'a'=audio test, 'c'=clear history, 's'=status")
        print("⚙️ Mode: Priority-based audio with anti-spam protection")
        
        try:
            while self.is_running:
                if self.paused:
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('p'):
                        self.paused = False
                        print("▶️ Resumed")
                    elif key == ord('q'):
                        break
                    continue
                
                # Capture frame from camera
                try:
                    result = self.camera.get_frame()
                    if result is None:
                        time.sleep(0.001)
                        continue
                        
                    ret, frame = result
                    if not ret:
                        time.sleep(0.001)
                        continue
                except Exception as e:
                    print(f"❌ Error capturing frame: {e}")
                    time.sleep(0.01)
                    continue
                
                # Calculate FPS
                self.frame_count += 1
                if self.frame_count % 30 == 0:
                    elapsed = time.time() - self.start_time
                    self.fps = 30 / elapsed if elapsed > 0 else 0
                    self.start_time = time.time()
                
                # Run COMPREHENSIVE object detection (including walls)
                detections = []
                try:
                    detections = self.detector.detect_enhanced(frame)
                    if detections and self.frame_count % 60 == 0:  # Log every 2 seconds at 30fps
                        # Only log high confidence detections
                        high_conf_dets = [d for d in detections if d.get('confidence', 0) >= 0.6]
                        if high_conf_dets:
                            classes = [d.get('class_name', 'unknown') for d in high_conf_dets[:4]]
                            print(f"📹 High-confidence detections ({len(high_conf_dets)}): {', '.join(classes)}")
                except Exception as e:
                    print(f"❌ Detection error: {e}")
                    detections = []
                
                # Update tracker with detections
                tracks = []
                try:
                    tracks = self.tracker.update(detections, frame)
                    
                    # Debug: Check track confidence
                    if tracks and self.frame_count % 90 == 0:  # Log every 3 seconds
                        high_conf_tracks = [t for t in tracks if t.get('confidence', 0) >= 0.6]
                        print(f"🎯 Tracking {len(high_conf_tracks)} high-confidence objects")
                        
                except Exception as e:
                    print(f"❌ Tracking error: {e}")
                    tracks = []
                
                # Provide ENHANCED intelligent audio guidance
                audio_triggered = False
                try:
                    frame_width = self.config['camera']['width']
                    frame_height = self.config['camera']['height']
    
                    # Anti-spam: Don't trigger audio too frequently
                    now = time.time()
                    if now - self.last_audio_time >= self.audio_cooldown:
                        audio_triggered = self.audio_feedback.provide_intelligent_guidance(tracks, frame_width, frame_height)
                        if audio_triggered:
                            self.last_audio_time = now
                            # Debug log
                            if tracks:
                                closest = min(tracks, key=lambda t: self.audio_feedback.estimate_distance(
                                    t['bbox'], frame_width, frame_height
                                ))
                                dist = self.audio_feedback.estimate_distance(closest['bbox'], frame_width, frame_height)
                                print(f"🔊 Audio triggered for {closest['class_name']} at {dist:.1f}m")
    
                except Exception as e:
                    print(f"❌ Audio feedback error: {e}")
                
                if self.visualization:
                    try:
                        display_frame = self._create_visualization(frame, tracks, detections, audio_triggered)
                        cv2.imshow('Enhanced Smart Goggles', display_frame)
                    except Exception as e:
                        print(f"❌ Visualization error: {e}")
                        cv2.imshow('Enhanced Smart Goggles', frame)
                    
                    # Check for key press
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('p'):
                        self.paused = True
                        print("⏸️ Paused")
                    elif key == ord('v'):
                        self.visualization = not self.visualization
                        print(f"👁️ Visualization: {'ON' if self.visualization else 'OFF'}")
                    elif key == ord('a'):
                        # Quick audio test
                        self.audio_feedback._enqueue("Test message.", priority='INFO')
                    elif key == ord('c'):
                        self.audio_feedback.clear_history()
                        self.tracker.reset()
                        print("🗑️ Object history and tracker cleared")
                    elif key == ord('s'):
                        self._show_system_status(tracks)
                else:
                    # If no visualization, still check for key presses
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('p'):
                        self.paused = True
                        print("⏸️ Paused")
                    elif key == ord('v'):
                        self.visualization = True
                        print("👁️ Visualization: ON")
                    elif key == ord('a'):
                        self.audio_feedback._enqueue("Test message.", priority='INFO')
                    elif key == ord('c'):
                        self.audio_feedback.clear_history()
                        self.tracker.reset()
                    elif key == ord('s'):
                        self._show_system_status(tracks)
        
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
        finally:
            self.cleanup()
    
    def _create_visualization(self, frame, tracks, detections, audio_triggered):
        """Create enhanced visualization with smart audio info"""
        display_frame = draw_tracking_info(frame.copy(), tracks)
        
        # Add enhanced status information
        frame_width = self.config['camera']['width']
        frame_height = self.config['camera']['height']
        
        # Count high confidence tracks
        high_conf_tracks = [t for t in tracks if t.get('confidence', 0) >= 0.6]
        
        status_text = f"FPS: {self.fps:.1f} | High-conf objects: {len(high_conf_tracks)}"
        cv2.putText(
            display_frame, 
            status_text, 
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (0, 255, 0) if audio_triggered else (255, 255, 255), 
            2
        )
        
        # Add audio status
        audio_status = "SPEAKING" if audio_triggered else "monitoring"
        cv2.putText(
            display_frame, 
            f"Audio: {audio_status}", 
            (10, 55), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (0, 255, 0) if audio_triggered else (200, 200, 200), 
            2
        )
        
        # List only high-confidence tracked objects with enhanced information
        y_offset = 80
        for i, track in enumerate(high_conf_tracks[:6]):  # Show first 6 high-confidence objects
            distance = self.audio_feedback.estimate_distance(track['bbox'], frame_width, frame_height)
            movement_state = track.get('movement_relative', 'unknown')
            danger_level = self.audio_feedback.assess_danger_level(track, distance, movement_state)
            position = self.audio_feedback.get_position(track['bbox'], frame_width)
            
            # Color code based on danger level
            color_map = {'critical': (0, 0, 255), 'high': (0, 165, 255), 'medium': (0, 255, 255), 'low': (0, 255, 0)}
            color = color_map.get(danger_level, (255, 255, 255))
            
            # Object text with confidence
            conf = track.get('confidence', 0)
            obj_text = f"{track['class_name']}: {distance:.1f}m {position} (conf: {conf:.2f})"
            cv2.putText(
                display_frame,
                obj_text,
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1
            )
            y_offset += 25
        
        # Add confidence threshold info
        conf_thresh = self.config.get('audio', {}).get('confidence_threshold', 0.6)
        cv2.putText(
            display_frame,
            f"Min confidence: {conf_thresh}",
            (10, frame.shape[0] - 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (200, 200, 255),
            1
        )
        
        # Add controls help
        help_text = "q=quit, p=pause, v=toggle vis, a=audio test, c=clear, s=status"
        cv2.putText(
            display_frame,
            help_text,
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (200, 200, 200),
            1
        )
        
        return display_frame
    
    def _show_system_status(self, tracks):
        """Show system status in console"""
        print(f"\n{'='*50}")
        print("🎯 ENHANCED SYSTEM STATUS")
        print(f"{'='*50}")
        print(f"📊 FPS: {self.fps:.1f}")
        
        # Count by confidence
        high_conf_tracks = [t for t in tracks if t.get('confidence', 0) >= 0.6]
        medium_conf_tracks = [t for t in tracks if 0.4 <= t.get('confidence', 0) < 0.6]
        low_conf_tracks = [t for t in tracks if t.get('confidence', 0) < 0.4]
        
        print(f"🎯 Tracked objects: {len(tracks)}")
        print(f"  • High confidence (≥0.6): {len(high_conf_tracks)}")
        print(f"  • Medium confidence (0.4-0.6): {len(medium_conf_tracks)}")
        print(f"  • Low confidence (<0.4): {len(low_conf_tracks)}")
        
        conf_thresh = self.config.get('audio', {}).get('confidence_threshold', 0.6)
        print(f"🔊 Audio confidence threshold: {conf_thresh}")
        print(f"🔊 Audio system: PRIORITY QUEUE ACTIVE")
        
        if high_conf_tracks:
            print(f"\n📋 HIGH CONFIDENCE OBJECTS:")
            print(f"| {'Object':12} | {'Dist':4} | {'Position':12} | {'Conf':5} | {'Movement':8} |")
            print(f"|{'-'*13}|{'-'*6}|{'-'*14}|{'-'*7}|{'-'*10}|")
            for track in high_conf_tracks[:8]:  # Show first 8 high confidence objects
                frame_width = self.config['camera']['width']
                frame_height = self.config['camera']['height']
                distance = self.audio_feedback.estimate_distance(track['bbox'], frame_width, frame_height)
                movement = track.get('movement_relative', 'unknown')
                position = self.audio_feedback.get_position(track['bbox'], frame_width)
                conf = track.get('confidence', 0)
                
                print(f"| {track['class_name']:12} | {distance:4.1f} | {position:12} | {conf:4.2f} | {movement:8} |")
        else:
            print("  🌉 No high-confidence objects tracked")
        print(f"{'='*50}\n")
    
    def cleanup(self):
        """Clean up resources"""
        self.is_running = False
        # Short shutdown message
        self.audio_feedback._enqueue("System shutting down.", priority='INFO')
        time.sleep(0.5)
        self.camera.release()
        cv2.destroyAllWindows()
        print("✅ Enhanced system shut down cleanly")

def main():
    """Main function"""
    print("🎯" + "="*50)
    print("        SMART GOGGLE SYSTEM - ENHANCED VERSION")
    print("      Priority-based Audio + Anti-spam Protection")
    print("🎯" + "="*50)
    
    try:
        # Check if config.yaml exists before starting
        if not os.path.exists("config.yaml"):
            print("WARNING: 'config.yaml' not found. Creating a default config file.")
            default_config = SmartGoggleSystem(config_path=None)._get_default_config()
            with open("config.yaml", 'w') as f:
                yaml.dump(default_config, f)
            print("Default config created. Please adjust settings if needed.")
            print("Starting with default configuration...")

        system = SmartGoggleSystem()
        system.run()
    except Exception as e:
        print(f"❌ Failed to start system: {e}")
        print("💡 Please check: Camera connection | Dependencies | YOLO model | config.yaml settings")

if __name__ == "__main__":
    main()