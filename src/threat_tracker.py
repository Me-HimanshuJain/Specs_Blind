"""
Persistent threat tracking for blind-person glasses.
Remembers dangerous objects across frame drops and escalates threat level if they reappear.
"""

import time
from collections import defaultdict


class ThreatTracker:
    """
    Tracks threats across frames and escalates threat level if they reappear.
    Useful for blind users to remember repeated obstacles in same location.
    """

    def __init__(self, memory_duration: float = 10.0, escalation_threshold: int = 2):
        """
        Args:
            memory_duration: How long to remember a threat (seconds)
            escalation_threshold: How many times before escalating to critical
        """
        self.memory_duration = memory_duration
        self.escalation_threshold = escalation_threshold
        
        # Threats: {track_id: {time_added, class_name, distance, direction, reappear_count, threat_level}}
        self.threats = {}
        self.threat_history = []  # (timestamp, track_id, class_name, threat_level)
        
    def add_threat(self, track_id: int, class_name: str, distance: float, direction: str):
        """Record a new threat or update existing one."""
        now = time.time()
        
        if track_id not in self.threats:
            # New threat
            self.threats[track_id] = {
                'time_added': now,
                'class_name': class_name,
                'distance': distance,
                'direction': direction,
                'reappear_count': 0,
                'threat_level': 'NEW'  # NEW → PERSISTENT → ESCALATED
            }
        else:
            # Reappearing threat - escalate
            threat = self.threats[track_id]
            threat['reappear_count'] += 1
            threat['distance'] = distance
            threat['direction'] = direction
            threat['time_added'] = now  # Reset timer
            
            # Check if threat should be escalated
            if threat['reappear_count'] >= self.escalation_threshold:
                threat['threat_level'] = 'ESCALATED'
                print(f"🚨 THREAT ESCALATED: {class_name} reappeared {threat['reappear_count']}x")
            else:
                threat['threat_level'] = 'PERSISTENT'

    def remove_threat(self, track_id: int):
        """Mark threat as resolved."""
        if track_id in self.threats:
            threat = self.threats[track_id]
            self.threat_history.append((
                time.time(),
                track_id,
                threat['class_name'],
                threat['threat_level']
            ))
            del self.threats[track_id]

    def get_escalated_threats(self) -> list:
        """Get all escalated threats (reappeared multiple times)."""
        return [
            (tid, t) for tid, t in self.threats.items()
            if t.get('threat_level') == 'ESCALATED'
        ]

    def get_persistent_threats(self) -> list:
        """Get all threats, including escalated."""
        return [(tid, t) for tid, t in self.threats.items()]

    def clean_old_threats(self):
        """Remove threats older than memory_duration."""
        now = time.time()
        to_remove = [
            tid for tid, t in self.threats.items()
            if now - t['time_added'] > self.memory_duration
        ]
        for tid in to_remove:
            self.remove_threat(tid)

    def get_threat_status(self, track_id: int) -> dict:
        """Get detailed threat info."""
        if track_id not in self.threats:
            return None
        
        threat = self.threats[track_id]
        return {
            'class_name': threat['class_name'],
            'distance': threat['distance'],
            'direction': threat['direction'],
            'reappear_count': threat['reappear_count'],
            'threat_level': threat['threat_level'],
            'time_in_memory': time.time() - threat['time_added']
        }

    def get_threat_count(self) -> int:
        """Get number of active threats."""
        self.clean_old_threats()
        return len(self.threats)

    def get_summary(self) -> str:
        """Get human-readable threat summary."""
        self.clean_old_threats()
        
        if not self.threats:
            return "No active threats."
        
        escalated = self.get_escalated_threats()
        persistent = [t for t in self.threats.values() if t['threat_level'] == 'PERSISTENT']
        new = [t for t in self.threats.values() if t['threat_level'] == 'NEW']
        
        summary = f"Threats: {len(escalated)} escalated, {len(persistent)} persistent, {len(new)} new. "
        
        if escalated:
            summary += f"ESCALATED: " + ", ".join([
                f"{t[1]['class_name']} (x{t[1]['reappear_count']})"
                for t in escalated[:3]
            ]) + ". "
        
        return summary.strip()

    def reset(self):
        """Clear all threat memory."""
        self.threats.clear()
        self.threat_history.clear()
