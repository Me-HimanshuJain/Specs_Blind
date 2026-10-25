#!/usr/bin/env python3
"""
Smart Goggle System for Blind Users - Complete Implementation
Includes: Threat tracking, power management, voice confirmation, hand-free controls, haptic feedback
"""

import cv2
import time
import yaml
import numpy as np
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

try:
    from src.camera import Camera
    from src.detector import EnhancedObjectDetector
    from src.tracker import ObjectTracker
    from src.audio_feedback import AudioGuidance
    from src.threat_tracker import ThreatTracker
    from src.power_manager import PowerManager, BatterySimulator
    from src.user_input import UserInput
    from src.voice_confirmation import VoiceConfirmation, SafeActionExecutor
    from src.haptic_feedback import HapticFeedback
    from src.utils import draw_tracking_info
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    sys.exit(1)


class SmartGoggleSystemV2:
    """
    Smart Goggle System for Blind Users - Enhanced Version
    Features: Priority audio, threat tracking, power management, haptic feedback
    """

    def __init__(self, config_path: str = "config.yaml"):
        print("🔧 Initializing Smart Goggle System (v2.0)...")
        
        # Load configuration
        self.config_path = config_path
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            self.config = self._get_default_config()
        
        # Initialize core components
        print("📷 Initializing camera...")
        self.camera = Camera(config_path)
        
        print("🔍 Initializing detector...")
        self.detector = EnhancedObjectDetector(config_path)
        
        print("📍 Initializing tracker...")
        self.tracker = ObjectTracker(config_path)
        
        print("🔊 Initializing audio system...")
        self.audio = AudioGuidance(config_path)
        
        print("🚨 Initializing threat tracker...")
        self.threat_tracker = ThreatTracker(memory_duration=10.0, escalation_threshold=2)
        
        print("⚡ Initializing power manager...")
        self.power_manager = PowerManager(battery_percent=100.0, threat_tracker=self.threat_tracker)
        self.battery_sim = BatterySimulator(initial_percent=100.0, drain_rate_per_sec=0.05)
        
        print("🎮 Initializing user input...")
        self.user_input = UserInput()
        
        print("✅ Initializing voice confirmation...")
        self.voice_confirm = VoiceConfirmation()
        self.safe_executor = SafeActionExecutor(self.voice_confirm)
        
        print("📳 Initializing haptic feedback...")
        self.haptic = HapticFeedback()
        
        # System state
        self.is_running = False
        self.is_paused = False
        self.show_visualization = False
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0
        self.frame_times = []
        self.last_threat_announced = {}
        
        print("✅ System ready!")

    def _get_default_config(self) -> dict:
        """Return default configuration"""
        return {
            'camera': {'width': 640, 'height': 480, 'fps': 60, 'frame_skip': 0},
            'yolo': {'detection_frequency': 1, 'inference_size': 416, 'confidence_threshold': 0.3},
            'tracking': {'min_hits': 1, 'max_age': 10},
            'audio': {'confidence_threshold': 0.6, 'update_interval': 0.5},
            'guidance': {'stop_distance': 0.6, 'critical_distance': 1.0, 'warning_distance': 2.0, 'safe_distance': 3.0}
        }

    def run(self):
        """Main system loop"""
        print("🚀 Starting main processing loop...")
        self.is_running = True
        self.start_time = time.time()
        
        try:
            while self.is_running:
                # Read frame
                frame = self.camera.read()
                if frame is None:
                    continue
                
                self.frame_count += 1
                
                # Update battery (simulated)
                battery = self.battery_sim.get_battery()
                self.power_manager.update_battery(battery)
                
                # Check threats and adjust power mode
                self.power_manager.check_threat_level()
                
                # Run detection
                detections = self.detector.detect(frame)
                
                # Update tracking
                tracks = self.tracker.update(detections, frame.shape)
                
                # Update threat tracker
                frame_w, frame_h = frame.shape[1], frame.shape[0]
                for track in tracks:
                    dist = self.audio.estimate_distance(track['bbox'], frame_w, frame_h)
                    direction = self.audio._estimate_direction(track['bbox'], frame_w)
                    if dist < 5.0:  # Only track nearby threats
                        self.threat_tracker.add_threat(
                            track_id=track['track_id'],
                            class_name=track['class_name'],
                            distance=dist,
                            direction=direction
                        )
                
                # Provide audio guidance
                self.audio.provide_intelligent_guidance(tracks, frame_w, frame_h)
                
                # Trigger haptic feedback for threats
                self._update_haptic_feedback(tracks)
                
                # Process user input
                self._process_user_input()
                
                # Handle visualization
                if self.show_visualization:
                    display_frame = self._draw_visualization(frame, tracks)
                    cv2.imshow("Smart Goggle System", display_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.is_running = False
                elif key == ord('p'):
                    self.is_paused = not self.is_paused
                elif key == ord('v'):
                    self.show_visualization = not self.show_visualization
                elif key == ord('a'):
                    self.audio.test_tts()
                elif key == ord('c'):
                    self.audio.clear_history()
                    self.threat_tracker.reset()
                elif key == ord('s'):
                    self._show_status()
                
                # FPS calculation
                self._update_fps()
                
        except KeyboardInterrupt:
            print("\n⚙️ Keyboard interrupt received")
        finally:
            self.cleanup()

    def _update_haptic_feedback(self, tracks):
        """Update haptic feedback based on threats"""
        if not tracks:
            return
        
        frame_w = self.config['camera']['width']
        frame_h = self.config['camera']['height']
        
        # Find closest track
        closest = min(tracks, key=lambda t: self.audio.estimate_distance(t['bbox'], frame_w, frame_h), default=None)
        if not closest:
            return
        
        dist = self.audio.estimate_distance(closest['bbox'], frame_w, frame_h)
        
        # Haptic feedback based on distance
        if dist < 0.6:
            # Emergency - SOS pattern
            self.haptic.emergency_stop()
        elif dist < 1.0:
            # Critical warning - double pulse
            direction = self.audio._estimate_direction(closest['bbox'], frame_w)
            self.haptic.critical_warning()
        elif dist < 2.0:
            # Obstacle warning - single pulse with direction
            direction = self.audio._estimate_direction(closest['bbox'], frame_w)
            self.haptic.obstacle_warning()
        elif dist < 3.0:
            # Navigation hint - directional
            direction = self.audio._estimate_direction(closest['bbox'], frame_w)
            self.haptic.navigation_hint(direction)

    def _process_user_input(self):
        """Process user input events"""
        event = self.user_input.get_next_input()
        if not event:
            return
        
        print(f"🎮 User input: {event['event']}")
        
        if event['event'] == 'TAP':
            if self.is_paused:
                self.audio.speak("Resumed.")
                self.is_paused = False
            else:
                self.audio.speak("Paused. Tap again to resume.")
                self.is_paused = True
        
        elif event['event'] == 'LONG_PRESS':
            status = self.power_manager.get_status()
            threat_summary = self.threat_tracker.get_summary()
            msg = f"{status}. {threat_summary}"
            self.audio.speak(msg)

    def _update_fps(self):
        """Calculate and display FPS"""
        frame_time = time.time() - self.start_time
        self.frame_times.append(frame_time)
        
        if len(self.frame_times) > 60:
            self.frame_times.pop(0)
            elapsed = self.frame_times[-1] - self.frame_times[0]
            if elapsed > 0:
                self.fps = len(self.frame_times) / elapsed

    def _draw_visualization(self, frame, tracks) -> np.ndarray:
        """Draw visualization on frame"""
        display = frame.copy()
        
        # Draw tracks
        for track in tracks:
            bbox = track['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Color based on confidence
            conf = track.get('confidence', 0)
            if conf >= 0.6:
                color = (0, 255, 0)  # Green
            else:
                color = (0, 165, 255)  # Orange
            
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{track['class_name']} {conf:.2f}"
            cv2.putText(display, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # Draw system status
        cv2.putText(display, f"FPS: {self.fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, f"Battery: {self.battery_sim.get_battery():.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, f"Threats: {self.threat_tracker.get_threat_count()}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display, f"Mode: {self.power_manager.current_mode.name}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return display

    def _show_status(self):
        """Show system status"""
        print("\n" + "="*60)
        print("📊 SMART GOGGLE SYSTEM STATUS")
        print("="*60)
        print(f"⏱️ Uptime: {time.time() - self.start_time:.1f}s")
        print(f"🎬 Frames: {self.frame_count}")
        print(f"📊 FPS: {self.fps:.1f}")
        print(f"🔋 {self.power_manager.get_status()}")
        print(f"🚨 {self.threat_tracker.get_summary()}")
        print("="*60 + "\n")

    def cleanup(self):
        """Cleanup resources"""
        print("\n🛑 Shutting down...")
        self.is_running = False
        self.audio.speak("System shutting down.")
        time.sleep(0.5)
        self.camera.release()
        cv2.destroyAllWindows()
        print("✅ System shutdown complete")


def main():
    """Main entry point"""
    print("🎯" + "="*60)
    print("     SMART GOGGLE SYSTEM FOR BLIND USERS - V2.0")
    print("   Priority Audio + Threat Tracking + Haptic Feedback")
    print("🎯" + "="*60)
    
    try:
        if not os.path.exists("config.yaml"):
            print("⚠️ config.yaml not found. Creating default configuration...")
            default_config = SmartGoggleSystemV2()._get_default_config()
            with open("config.yaml", 'w') as f:
                yaml.dump(default_config, f)
        
        system = SmartGoggleSystemV2()
        system.run()
    
    except Exception as e:
        print(f"❌ System error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
