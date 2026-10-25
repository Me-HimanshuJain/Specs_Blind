import time

# Lightweight sensor stubs for indoor/outdoor and step estimation.
# Replace these with real GPS/IMU integrations on device.

class Sensors:
    def __init__(self, config_path: str = "config.yaml"):
        # placeholder state
        self._outdoor = False
        self._last_gps = None
        self._step_count = 0
        self._last_step_time = 0

    def is_outdoor(self) -> bool:
        """Return True if GPS indicates outdoor. Stub: returns last set state.
        Replace with real GPS fix & accuracy checks on device."""
        return self._outdoor

    def set_outdoor(self, val: bool):
        self._outdoor = bool(val)

    def update_gps(self, lat: float, lon: float, accuracy_m: float = 999.0):
        self._last_gps = (lat, lon, accuracy_m, time.time())
        # If accuracy is good and coordinates present, consider outdoor
        self._outdoor = accuracy_m < 50.0

    def step_detected(self):
        """Call this from an IMU step detector to increment step count."""
        t = time.time()
        # Debounce very rapid triggers
        if t - self._last_step_time > 0.3:
            self._step_count += 1
            self._last_step_time = t

    def get_steps(self) -> int:
        return self._step_count

    def get_heading(self) -> float:
        """Return heading in degrees from IMU. Stub returns 0.0.
        Implement by reading device magnetometer/gyro in production."""
        return 0.0
