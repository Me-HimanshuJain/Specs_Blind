"""
Power management for blind-person glasses.
Optimizes battery life by adjusting processing power based on environment and threat level.
"""

import time
import threading
from enum import Enum


class PowerMode(Enum):
    """Power modes with corresponding processing levels."""
    ECO = 1        # Minimal processing, low FPS, reduced detection
    BALANCED = 2   # Normal operation, good accuracy and battery
    PERFORMANCE = 3  # Maximum FPS and accuracy, high power draw


class PowerManager:
    """
    Manages power consumption by adjusting system parameters based on:
    - Battery level
    - Threat level (high threat = more power used for safety)
    - Time of day (night = lower power needs)
    - User activity (stationary = less power needed)
    """

    def __init__(self, battery_percent: float = 100.0, threat_tracker=None):
        self.battery_percent = battery_percent
        self.threat_tracker = threat_tracker
        self.current_mode = PowerMode.BALANCED
        self.mode_changed_time = time.time()
        
        # Power mode parameters
        self.mode_config = {
            PowerMode.ECO: {
                'fps': 15,
                'detection_frequency': 3,  # Every 3rd frame
                'inference_size': 320,
                'audio_update_interval': 2.0,
                'announce_interval': 8.0
            },
            PowerMode.BALANCED: {
                'fps': 30,
                'detection_frequency': 2,  # Every 2nd frame
                'inference_size': 416,
                'audio_update_interval': 0.5,
                'announce_interval': 2.0
            },
            PowerMode.PERFORMANCE: {
                'fps': 60,
                'detection_frequency': 1,  # Every frame
                'inference_size': 416,
                'audio_update_interval': 0.3,
                'announce_interval': 1.0
            }
        }
        
        # Thresholds
        self.low_battery_threshold = 20.0  # Switch to ECO below this
        self.critical_battery_threshold = 10.0  # Extreme ECO below this
        self.high_threat_duration = 30.0  # Stay in PERFORMANCE during high threat

    def update_battery(self, percent: float):
        """Update current battery level."""
        prev_battery = self.battery_percent
        self.battery_percent = max(0, min(100, percent))
        
        # Check if mode should change
        if prev_battery > self.low_battery_threshold and self.battery_percent <= self.low_battery_threshold:
            print(f"🔋 Low battery detected ({self.battery_percent:.1f}%). Switching to ECO mode.")
            self.set_mode(PowerMode.ECO)
        elif prev_battery <= self.low_battery_threshold and self.battery_percent > self.low_battery_threshold:
            print(f"🔋 Battery recovered ({self.battery_percent:.1f}%). Switching to BALANCED mode.")
            self.set_mode(PowerMode.BALANCED)

    def check_threat_level(self):
        """Boost to PERFORMANCE if threats detected."""
        if not self.threat_tracker:
            return
        
        escalated = self.threat_tracker.get_escalated_threats()
        
        if escalated and self.current_mode != PowerMode.PERFORMANCE:
            print(f"⚠️ Escalated threats detected. Boosting to PERFORMANCE mode.")
            self.set_mode(PowerMode.PERFORMANCE)
            self.threat_boost_time = time.time()
        elif not escalated and self.current_mode == PowerMode.PERFORMANCE:
            # Check if enough time has passed
            if time.time() - getattr(self, 'threat_boost_time', 0) > self.high_threat_duration:
                # Return to normal mode
                if self.battery_percent > self.low_battery_threshold:
                    self.set_mode(PowerMode.BALANCED)
                else:
                    self.set_mode(PowerMode.ECO)

    def set_mode(self, mode: PowerMode):
        """Switch to a specific power mode."""
        if self.current_mode == mode:
            return
        
        self.current_mode = mode
        self.mode_changed_time = time.time()
        print(f"⚡ Power mode: {mode.name} | Battery: {self.battery_percent:.1f}%")

    def get_config(self) -> dict:
        """Get current power mode configuration."""
        return self.mode_config[self.current_mode].copy()

    def estimate_runtime(self) -> str:
        """
        Estimate runtime in current power mode.
        Rough estimation based on power draw.
        """
        # Power draw estimates (mW): ECO=500, BALANCED=1000, PERFORMANCE=1500
        power_draws = {
            PowerMode.ECO: 500,
            PowerMode.BALANCED: 1000,
            PowerMode.PERFORMANCE: 1500
        }
        
        battery_capacity = 3000  # mAh estimate
        power_draw = power_draws[self.current_mode]
        
        # Runtime = capacity / power_draw (hours)
        runtime_hours = (battery_capacity * self.battery_percent / 100) / power_draw
        
        if runtime_hours < 1:
            return f"{int(runtime_hours * 60)} minutes"
        else:
            return f"{runtime_hours:.1f} hours"

    def get_status(self) -> str:
        """Get power status string for user."""
        mode_name = self.current_mode.name
        runtime = self.estimate_runtime()
        return f"Battery: {self.battery_percent:.1f}% | Mode: {mode_name} | Runtime: {runtime}"


class BatterySimulator:
    """Simulate battery drain for testing."""
    
    def __init__(self, initial_percent: float = 100.0, drain_rate_per_sec: float = 0.1):
        self.battery = initial_percent
        self.drain_rate = drain_rate_per_sec
        self.last_update = time.time()
        self.lock = threading.Lock()

    def get_battery(self) -> float:
        """Get current simulated battery level."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.battery -= self.drain_rate * elapsed
            self.battery = max(0, self.battery)
            self.last_update = now
            return self.battery

    def charge(self, amount: float):
        """Add battery charge."""
        with self.lock:
            self.battery = min(100, self.battery + amount)

    def reset(self, percent: float = 100.0):
        """Reset battery to specific level."""
        with self.lock:
            self.battery = percent
            self.last_update = time.time()
