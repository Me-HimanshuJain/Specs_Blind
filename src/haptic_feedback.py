"""
Haptic feedback system for blind user glasses.
Provides vibration patterns for different threat levels and directions.
"""

import time
import threading


class HapticFeedback:
    """
    Haptic pattern generator for blind navigation.
    Provides distinct vibration patterns for: EMERGENCY, WARNING, OBSTACLE, SAFE
    """

    def __init__(self):
        self.enabled = True
        self.intensity = 0.8  # 0.0 to 1.0
        self.is_vibrating = False
        self._lock = threading.Lock()

    def emergency_stop(self):
        """Rapid strong vibrations for emergency stop <0.6m."""
        if not self.enabled:
            return
        # Pattern: 200ms on, 100ms off, 200ms on, 100ms off (SOS-like)
        self._vibrate_pattern([(200, 1.0), (100, 0), (200, 1.0), (100, 0)])

    def critical_warning(self):
        """Strong double vibration for critical distance 0.6-1.0m."""
        if not self.enabled:
            return
        # Pattern: 150ms on, 100ms off, 150ms on
        self._vibrate_pattern([(150, 0.9), (100, 0), (150, 0.9)])

    def obstacle_warning(self):
        """Single medium vibration for obstacle at 1.0-2.0m."""
        if not self.enabled:
            return
        # Pattern: 100ms vibration
        self._vibrate_pattern([(100, 0.6)])

    def navigation_hint(self, direction: str):
        """Directional haptic hint: left=single pulse left side, right=pulse right side."""
        if not self.enabled:
            return
        if direction == "left":
            # Vibrate left side of device
            self._vibrate_pattern([(80, 0.5)], side="left")
        elif direction == "right":
            # Vibrate right side of device
            self._vibrate_pattern([(80, 0.5)], side="right")
        else:
            # Center: both sides
            self._vibrate_pattern([(60, 0.5)], side="center")

    def safe_path(self):
        """Light gentle vibration pattern to confirm path is clear."""
        if not self.enabled:
            return
        # Pattern: 50ms gentle vibration
        self._vibrate_pattern([(50, 0.3)])

    def _vibrate_pattern(self, pattern, side: str = "both"):
        """
        Internal method to play vibration pattern.
        pattern: list of (duration_ms, intensity_0_to_1) tuples
        side: "left", "right", "center", or "both"
        
        Note: On real hardware, this would interface with device motor(s).
        """
        with self._lock:
            self.is_vibrating = True

        def _play():
            try:
                for duration_ms, intensity in pattern:
                    if duration_ms > 0:
                        # TODO: Replace with real hardware vibration call
                        # Example for Android: context.getSystemService(Context.VIBRATOR_SERVICE).vibrate(duration_ms)
                        # Example for iOS: use CoreHaptics framework
                        time.sleep(duration_ms / 1000.0)
                    else:
                        time.sleep(0.05)  # Rest period
            finally:
                with self._lock:
                    self.is_vibrating = False

        threading.Thread(target=_play, daemon=True).start()

    def set_intensity(self, level: float):
        """Set global haptic intensity (0.0 to 1.0)."""
        self.intensity = max(0.0, min(1.0, float(level)))

    def disable(self):
        """Disable all haptic feedback."""
        self.enabled = False

    def enable(self):
        """Enable haptic feedback."""
        self.enabled = True
