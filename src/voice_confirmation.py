"""
Voice confirmation system for blind-person glasses.
Implements speech confirmation for safety-critical actions like emergency navigation.
"""

import subprocess
import threading
from queue import Queue


class VoiceConfirmation:
    """
    Wait for voice input confirmation before executing actions.
    Example: "Proceed right?" → User says "Yes" → Execute turn right
    """

    def __init__(self):
        self.confirmation_queue = Queue(maxsize=10)
        self.pending_action = None
        self.confirmation_timeout = 3.0  # seconds
        self.last_confirmation_time = 0

    def ask_confirmation(self, action_text: str) -> bool:
        """
        Ask user to confirm an action.
        action_text: e.g., "Move left to avoid obstacle?"
        Returns: True if confirmed, False if denied or timeout
        """
        self._speak_with_tts(f"{action_text} Say yes to confirm.")
        
        # Wait for voice response
        return self._wait_for_response(timeout=self.confirmation_timeout)

    def _speak_with_tts(self, text: str, rate: int = -2):
        """Speak text using PowerShell TTS."""
        text = text.replace('"', '\\"')
        
        ps_command = f'''
[System.Reflection.Assembly]::LoadWithPartialName("System.Speech") > $null
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Volume = 100
$speak.Rate = {rate}
$speak.Speak("{text}")
'''
        
        try:
            process = subprocess.Popen(
                ["powershell", "-Command", ps_command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            process.wait(timeout=30)
        except Exception as e:
            print(f"❌ TTS error in confirmation: {e}")

    def _wait_for_response(self, timeout: float = 3.0) -> bool:
        """
        Wait for user confirmation.
        In a real system, this would listen to microphone input.
        Currently returns True for demo purposes.
        """
        import time
        start = time.time()
        
        # Placeholder: In production, would use speech recognition API
        # (Azure Speech, Google Speech-to-Text, etc.)
        
        # For now, return True if no timeout
        while time.time() - start < timeout:
            # Check if confirmation received from queue
            try:
                response = self.confirmation_queue.get(timeout=0.1)
                if response.lower() in ['yes', 'yeah', 'ok', 'okay', 'confirmed']:
                    return True
                elif response.lower() in ['no', 'cancel', 'denied']:
                    return False
            except:
                continue
        
        # Timeout: assume no response = deny
        print("⏱️ Confirmation timeout - action cancelled")
        return False

    def provide_response(self, voice_input: str):
        """Call this when voice input is captured."""
        try:
            self.confirmation_queue.put_nowait(voice_input)
        except:
            print("❌ Confirmation queue full")

    def cancel_pending(self):
        """Cancel pending confirmation."""
        self.pending_action = None
        self.confirmation_queue.queue.clear()


class SafeActionExecutor:
    """
    Execute safety-critical actions with optional confirmation.
    Automatically confirms non-critical actions.
    """

    def __init__(self, voice_confirmation: VoiceConfirmation = None):
        self.voice_confirmation = voice_confirmation or VoiceConfirmation()
        self.actions_executed = []

    def execute_action(self, action_name: str, action_func, critical: bool = False, 
                       confirmation_text: str = None) -> bool:
        """
        Execute an action with optional voice confirmation.
        
        Args:
            action_name: Name of action (e.g., "turn_left")
            action_func: Callable to execute
            critical: If True, requires confirmation
            confirmation_text: Text to speak before confirming
        
        Returns: True if action executed, False if cancelled/denied
        """
        if critical and confirmation_text:
            # Ask for confirmation
            if not self.voice_confirmation.ask_confirmation(confirmation_text):
                print(f"❌ Action '{action_name}' cancelled by user")
                return False
            print(f"✅ Action '{action_name}' confirmed by user")
        
        # Execute the action
        try:
            action_func()
            self.actions_executed.append((action_name, True))
            print(f"✅ Action executed: {action_name}")
            return True
        except Exception as e:
            print(f"❌ Action failed: {action_name} - {e}")
            self.actions_executed.append((action_name, False))
            return False

    def undo_last_action(self, undo_func=None) -> bool:
        """Undo the last executed action."""
        if not self.actions_executed:
            print("❌ No actions to undo")
            return False
        
        last_action, success = self.actions_executed.pop()
        if success and undo_func:
            try:
                undo_func()
                print(f"↩️ Undid action: {last_action}")
                return True
            except Exception as e:
                print(f"❌ Undo failed: {e}")
                return False
        
        return False

    def get_action_history(self) -> list:
        """Get history of executed actions."""
        return self.actions_executed.copy()
