"""
User input handler for blind-person glasses.
Implements hands-free button controls for voice navigation, feedback adjustment, and safety.
"""

import time
import threading
from queue import Queue


class UserInput:
    """
    Hands-free input handler for blind glasses.
    Supports: long-press (hold 1s) and tap (quick press) on button(s).
    Can be extended to support multi-button combinations.
    """

    def __init__(self):
        self.button_queue = Queue(maxsize=50)  # Store button events
        self._button_press_time = 0  # Track press start time
        self._last_event = None

    def button_pressed(self):
        """Call this when physical button is pressed (e.g., from GPIO/touch)."""
        self._button_press_time = time.time()

    def button_released(self):
        """Call this when physical button is released."""
        if self._button_press_time == 0:
            return

        duration = time.time() - self._button_press_time
        self._button_press_time = 0

        # Classify as tap or long-press
        if duration < 0.5:
            event = "TAP"  # Quick press: toggle features, ask for status
        else:
            event = "LONG_PRESS"  # Hold: enable repeat, get detailed info

        try:
            self.button_queue.put_nowait({
                "event": event,
                "duration": duration,
                "timestamp": time.time()
            })
        except Exception:
            pass  # Queue full, skip event

    def get_next_input(self, timeout: float = 0.1) -> dict:
        """Get next user input event (non-blocking with timeout)."""
        try:
            return self.button_queue.get(timeout=timeout)
        except:
            return None

    def clear_queue(self):
        """Clear pending input events."""
        while not self.button_queue.empty():
            try:
                self.button_queue.get_nowait()
            except:
                break

    def handle_tap(self, audio_feedback, current_state: str) -> str:
        """TAP: Toggle or request status."""
        if current_state == "LISTENING":
            # Stop listening, return to guidance
            audio_feedback.speak("Guidance resumed.")
            return "GUIDING"
        elif current_state == "GUIDING":
            # Enter listening mode (user can ask questions)
            audio_feedback.speak("Listening mode. Say command.")
            return "LISTENING"
        return current_state

    def handle_long_press(self, audio_feedback, current_state: str) -> str:
        """LONG_PRESS: Get detailed status or enable emergency mode."""
        # Give comprehensive status update
        audio_feedback.speak("Status: Sending detailed obstacle report.")
        return current_state
