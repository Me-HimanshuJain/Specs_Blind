import time
import threading
import yaml
from queue import Queue
import subprocess
import os
from .sensors import Sensors
from .haptic_feedback import HapticFeedback


class AudioGuidance:
    """
    Industry-grade audio guidance system.
    Fully backward compatible with legacy main.py
    """

    def __init__(self, config_path: str = "config.yaml"):
        # ===============================
        # Load configuration
        # ===============================
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except Exception:
            config = {
                "audio": {
                    "rate": 160,
                    "volume": 0.9,
                    "confidence_threshold": 0.6
                },
                "guidance": {
                    "stop_distance": 0.6,
                    "critical_distance": 1.0,
                    "warning_distance": 2.0,
                    "safe_distance": 3.0
                }
            }

        audio_cfg = config["audio"]
        guide_cfg = config["guidance"]

        # -------------------------
        # Distance thresholds
        # -------------------------
        self.STOP_DIST = guide_cfg["stop_distance"]  # 0.6m
        self.CRITICAL_DIST = guide_cfg["critical_distance"]  # 1.0m
        self.WARNING_DIST = guide_cfg["warning_distance"]  # 2.0m
        self.SAFE_DIST = guide_cfg["safe_distance"]  # 3.0m

        # -------------------------
        # Confidence threshold
        # -------------------------
        self.min_confidence = audio_cfg.get('confidence_threshold', 0.6)

        # -------------------------
        # State
        # -------------------------
        self.state = "CLEAR"
        self.state_since = time.time()
        self.last_decision_time = 0
        self.decision_interval = 0.5

        # Critical repeater control
        self._critical_repeater_thread = None
        self._critical_repeater_stop = threading.Event()
        self._critical_obstacle_id = None  # track which object triggered critical
        self._critical_is_approaching = False  # track if it's actively approaching

        # -------------------------
        # Debug counters
        # -------------------------
        self.false_stop_count = 0
        self.last_false_stop_time = 0

        # -------------------------
        # Per-object announcement memory
        # -------------------------
        self.object_announce_state = {}
        self.object_announce_cooldown = audio_cfg.get('announcement_intervals', {}).get('static_object', 6.0)
        
        # Velocity tracking
        self.object_positions = {}

        # -------------------------
        # Audio system: priority queues
        # -------------------------
        self.queues = {
            'EMERGENCY': [],
            'OBSTACLE': [],
            'NAVIGATION': [],
            'INFO': []
        }
        self.q_lock = threading.Lock()
        self.q_cond = threading.Condition(self.q_lock)
        self.is_speaking = False
        self.last_speech_time = 0
        
        # Sensors for indoor/outdoor and step detection
        try:
            self.sensors = Sensors()
            self.step_count = 0
            self.last_step_check = time.time()
        except Exception:
            self.sensors = None
            self.step_count = 0

        # Environment detection
        self.is_indoor = True
        self.last_environment_check = time.time()

        # Movement tracking
        self.user_moving = False
        self.last_movement_check = time.time()

        threading.Thread(target=self._audio_worker, daemon=True).start()

        # Haptic feedback controller
        try:
            self.haptic = HapticFeedback()
        except Exception:
            self.haptic = None

        print("🔊 Audio Guidance System READY")
        print(f"🎯 Distance thresholds: STOP={self.STOP_DIST}m, CRITICAL={self.CRITICAL_DIST}m, WARNING={self.WARNING_DIST}m")

    # =====================================================
    # 🔹 LEGACY ENTRY (USED BY main.py)
    # =====================================================
    def provide_intelligent_guidance(self, tracks, frame_w, frame_h):
        """
        Legacy API expected by main.py.
        Returns True if any audio was queued this call, False otherwise.
        """
        audio_triggered = False

        # Update step count if sensors available
        self._update_step_count()
        
        # Check if user is moving
        self._update_movement_status()

        # Filter tracks by confidence threshold
        valid_tracks = []
        if tracks:
            for t in tracks:
                conf = t.get('confidence', 1.0)
                if conf >= self.min_confidence:
                    valid_tracks.append(t)
        
        tracks = valid_tracks

        # Debug: Print track info
        if tracks and len(tracks) > 0:
            print(f"📊 Audio: Processing {len(tracks)} valid tracks")
            for i, track in enumerate(tracks[:3]):  # Show first 3
                bbox = track.get('bbox', [0,0,0,0])
                dist = self.estimate_distance(bbox, frame_w, frame_h)
                print(f"  Track {i}: {track.get('class_name', 'unknown')} at {dist:.2f}m")

        # If no valid tracks, announce clear path if user is moving
        if not tracks:
            if self.user_moving:
                now = time.time()
                if now - getattr(self, 'last_clear_announce', 0) > 10.0:
                    self._enqueue("Path clear.", priority='INFO')
                    self.last_clear_announce = now
                    return True
            # Reset state if no tracks
            if self.state != "CLEAR":
                self._transition("CLEAR")
            return False

        # Build obstacle list with priority scoring
        obstacles = []
        for t in tracks:
            bbox = t.get("bbox", [0, 0, 1, 1])  # Default bbox
            dist = self.estimate_distance(bbox, frame_w, frame_h)
            
            # DEBUG: Check if distance is realistic
            if dist < 0.1:  # Unrealistically close
                print(f"⚠️ WARNING: Unrealistic distance {dist:.2f}m for {t.get('class_name')}")
                print(f"  BBOX: {bbox}, Frame: {frame_w}x{frame_h}")
                # Skip this track if distance is clearly wrong
                continue
                
            direction = self._estimate_direction(bbox, frame_w)
            
            # Get approach data from tracker
            approach_score = t.get('approach_score', 0)
            velocity = t.get('velocity_magnitude', 0)
            approach_rate = t.get('approach_rate', 0)
            
            obstacles.append(
                {
                    "class": t["class_name"],
                    "distance": dist,
                    "direction": direction,
                    "track_id": t.get('track_id'),
                    "approach_score": approach_score,
                    "velocity": velocity,
                    "is_approaching": approach_rate < -10,
                    "confidence": t.get('confidence', 1.0),
                    "bbox": bbox  # Store for debugging
                }
            )

        # If no valid obstacles after filtering, transition to clear
        if not obstacles:
            if self.state != "CLEAR":
                self._transition("CLEAR")
            return False

        # Sort obstacles by SMART PRIORITY SCORE
        scored = []
        for ob in obstacles:
            # Distance weight: closer = higher priority (0-40 points)
            dist_score = max(0, int((5.0 - ob["distance"]) * 8))
            
            # Approach weight: fast approaching = critical (0-50 points)
            approach_weight = min(50, ob['approach_score'])
            
            # Direction weight: center/ahead = more critical (0-20 points)
            direction_weight = 20 if (ob["direction"] == "center" or ob["direction"] == "ahead") else 10
            
            # Total priority score
            total_score = dist_score + approach_weight + direction_weight
            
            scored.append((total_score, ob))

        # Sort by score descending (highest priority first)
        scored.sort(key=lambda x: x[0], reverse=True)
        obstacles = [item[1] for item in scored]
        
        # Log priority for debugging
        if obstacles:
            top_ob = obstacles[0]
            print(f"🎯 Top priority: {top_ob['class']} at {top_ob['distance']:.2f}m, direction: {top_ob['direction']}")

        # Process only the highest priority obstacle
        if obstacles:
            closest = obstacles[0]
            
            # DEBUG: Check distance before processing
            print(f"🔍 Processing obstacle: {closest['class']} at {closest['distance']:.2f}m")
            
            audio_triggered = self.process_obstacle(closest)
            
            # Obstacle-aware navigation
            center_blockers = [o for o in obstacles if o['direction'] in ('center','ahead') 
                              and o['distance'] <= self.SAFE_DIST]
            if center_blockers and audio_triggered:
                left_count = sum(1 for o in obstacles if o['direction'] == 'left' 
                                and o['distance'] <= self.SAFE_DIST)
                right_count = sum(1 for o in obstacles if o['direction'] == 'right' 
                                 and o['distance'] <= self.SAFE_DIST)
                
                if left_count == 0 or right_count == 0:
                    suggest = 'left' if left_count == 0 else 'right'
                    nav_msg = f"Move {suggest}."
                    self._enqueue(nav_msg, priority='NAVIGATION')

        return audio_triggered

    def announce_tracks(self, tracks, frame_w, frame_h):
        """
        Announce all obstacles that are coming in the way.
        Returns True if any audio was queued.
        """
        if not tracks:
            return False

        now = time.time()
        any_queued = False

        for t in tracks:
            # Identify object uniquely
            track_id = t.get('track_id')
            key = track_id if track_id is not None else f"{t.get('class_name','obj')}_{int(t.get('bbox',[0,0,0,0])[0])}"

            # Distance and direction
            dist = t.get('distance') if 'distance' in t else self.estimate_distance(t.get('bbox', [0,0,0,0]), frame_w, frame_h)
            direction = t.get('direction') if 'direction' in t else self._estimate_direction(t.get('bbox', [0,0,0,0]), frame_w)

            # Determine if object is 'in the way'
            in_way = (direction in ('center', 'ahead')) and (dist <= self.SAFE_DIST)
            approaching = t.get('is_approaching', False) or t.get('approach_score', 0) > 20

            # If it's approaching or in the way or within warning distance, consider announcing
            should_announce = in_way or approaching or dist <= self.WARNING_DIST

            if not should_announce:
                continue

            # Anti-spam: per-object cooldown
            last = self.object_announce_state.get(key, 0)
            # If approaching give shorter cooldown, else use configured cooldown
            cooldown = 1.0 if approaching else self.object_announce_cooldown
            if now - last < cooldown:
                continue

            # Build announcement text
            name = t.get('class_name', 'object')
            # distance phrasing
            if dist <= 0.5:
                dist_phrase = 'very close'
            else:
                dist_phrase = f"{dist:.1f} meters"

            dir_phrase = 'ahead of you' if direction in ('center','ahead') else f"to your {direction}"

            # Use shorter urgent phrasing for approaching
            if approaching and dist <= self.CRITICAL_DIST:
                msg = f"{name} very close {dir_phrase}. Stop."
                prio = 'EMERGENCY'
            elif approaching:
                msg = f"{name} approaching {dir_phrase}, {dist_phrase}."
                prio = 'OBSTACLE'
            else:
                msg = f"{name} {dir_phrase}, {dist_phrase}."
                prio = 'OBSTACLE'

            queued = self._enqueue(msg, priority=prio)
            if queued:
                any_queued = True
                self.object_announce_state[key] = now
                # Trigger a light haptic hint for awareness
                try:
                    if self.haptic and prio != 'EMERGENCY':
                        self.haptic.obstacle_warning()
                except Exception:
                    pass

        return any_queued

    # =====================================================
    # 🔹 IMPROVED DISTANCE ESTIMATION
    # =====================================================
    def estimate_distance(self, bbox, frame_w, frame_h):
        """
        Improved distance estimation based on bounding box area.
        More realistic for real-world scenarios.
        """
        if len(bbox) != 4:
            return 5.0  # Default far distance
        
        x1, y1, x2, y2 = bbox
        
        # Calculate bounding box area
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        bbox_area = bbox_width * bbox_height
        
        # Calculate frame area
        frame_area = frame_w * frame_h
        
        # Calculate area ratio
        if frame_area == 0:
            return 5.0
        
        area_ratio = bbox_area / frame_area
        
        # Debug info
        if area_ratio > 0.5:  # Very large object
            print(f"⚠️ Large object detected: area_ratio={area_ratio:.4f}")
        
        # Improved distance estimation based on real-world testing
        # Objects typically appear smaller when farther away
        if area_ratio > 0.3:    # Huge - very close (0.5m)
            distance = 0.5
        elif area_ratio > 0.15: # Large - close (1.0m)
            distance = 1.0
        elif area_ratio > 0.08: # Medium - warning distance (1.5m)
            distance = 1.5
        elif area_ratio > 0.04: # Small - safe distance (2.5m)
            distance = 2.5
        elif area_ratio > 0.02: # Very small - far (4.0m)
            distance = 4.0
        else:                   # Tiny - very far (6.0m+)
            distance = 6.0
        
        # Apply smoothing based on object type
        # People and cars have different size profiles
        # This would need object class info, but we don't have it here
        
        # Ensure distance is never unrealistically small
        if distance < 0.3:  # Minimum realistic distance
            distance = 0.3
            
        return distance

    # =====================================================
    # 🔹 IMPROVED OBSTACLE PROCESSING
    # =====================================================
    def process_obstacle(self, obstacle):
        now = time.time()

        if now - self.last_decision_time < self.decision_interval:
            return False

        self.last_decision_time = now

        dist = obstacle["distance"]
        direction = obstacle["direction"]
        name = obstacle["class"]
        is_approaching = obstacle.get('is_approaching', False)
        approach_score = obstacle.get('approach_score', 0)
        track_id = obstacle.get('track_id')

        # DEBUG: Log what we're processing
        print(f"📏 Obstacle: {name} at {dist:.2f}m, direction: {direction}, approaching: {is_approaching}")

        # SAFETY CHECK: If distance is unrealistically small but bbox is small, ignore
        bbox = obstacle.get('bbox', [0, 0, 1, 1])
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if dist < 0.5 and bbox_area < 100:  # Small bbox but claiming to be very close
            print(f"⚠️ Ignoring false close detection: {name} with small bbox")
            self.false_stop_count += 1
            if self.false_stop_count > 3 and now - self.last_false_stop_time > 10:
                print("🔧 Too many false stops, resetting state to CLEAR")
                self._transition("CLEAR")
                self.false_stop_count = 0
                self.last_false_stop_time = now
            return False

        # INTELLIGENT PRIORITY LOGIC:
        # Emergency STOP only when VERY close AND actively APPROACHING
        if dist <= self.STOP_DIST:
            # Only trigger STOP if the object is actively approaching, not static-close
            if dist <= 0.6:
                # Check if this is a valid stop scenario AND actively approaching
                if self._is_valid_stop_scenario(obstacle) and (is_approaching or approach_score > 35):
                    msg = "STOP! Object very close."
                    print(f"🛑 EMERGENCY STOP: {name} at {dist:.2f}m (approaching={is_approaching}, score={approach_score})")
                    # Track which object triggered critical and if it's approaching
                    self._critical_obstacle_id = track_id
                    self._critical_is_approaching = True
                    return self._transition("CRITICAL", msg, is_emergency=True)
                elif self._is_valid_stop_scenario(obstacle):
                    # Object is close but NOT approaching - just warn, don't STOP
                    print(f"⚠️ Object {name} is very close but NOT approaching, only warning (approaching={is_approaching}, score={approach_score})")
                    msg = f"{name} is very close ahead of you. Caution."
                    return self._transition("WARNING", msg)
                else:
                    print(f"⚠️ Suppressed false stop for {name} at {dist:.2f}m")
                    return False
            else:
                # dist is 0.6-1.0m: only CRITICAL if actively approaching
                if is_approaching or approach_score > 35:
                    msg = f"Stop! {name} {self._direction_phrase(direction)}."
                    self._critical_obstacle_id = track_id
                    self._critical_is_approaching = True
                    return self._transition("CRITICAL", msg)
                else:
                    # Not approaching, just approaching distance threshold
                    return False
        
        elif dist <= self.CRITICAL_DIST:
            # CRITICAL_DIST is 1.0m - only trigger if approaching
            if is_approaching and approach_score > 40:
                msg = f"Danger! {name} approaching {self._direction_phrase(direction)}."
                self._critical_obstacle_id = track_id
                self._critical_is_approaching = True
                return self._transition("CRITICAL", msg)
            elif is_approaching:
                msg = f"{name} approaching {self._direction_phrase(direction)}."
                self._critical_obstacle_id = track_id
                self._critical_is_approaching = True
                return self._transition("CRITICAL", msg)
            else:
                # Not approaching, not an urgent critical situation
                msg = f"{name} {self._direction_phrase(direction)}."
                return self._transition("WARNING", msg)
        
        elif dist <= self.WARNING_DIST:
            # Only warn if approaching or just entered warning zone (state transition)
            if (is_approaching and approach_score > 30):
                msg = f"{name} fast approaching {self._direction_phrase(direction)}."
                return self._transition("WARNING", msg)
            elif is_approaching:
                msg = f"{name} approaching {self._direction_phrase(direction)}."
                return self._transition("WARNING", msg)
            else:
                # For non-approaching objects at warning distance, only speak on first entry
                if self.state != "WARNING":  # Only announce on state transition, not repeatedly
                    if self.user_moving:
                        msg = f"{name} {self._direction_phrase(direction)}."
                        return self._transition("WARNING", msg)
                return False
        else:
            # Object is far away - can clear critical state
            self._critical_obstacle_id = None
            self._critical_is_approaching = False
            # Only announce clear if user is moving and path was previously blocked
            if self.user_moving and self.state != "CLEAR":
                return self._transition("CLEAR")
            return False

    def _is_valid_stop_scenario(self, obstacle):
        """
        Validate if this is a legitimate stop scenario.
        Prevents false stops from noisy detections.
        """
        # Check 1: Object should be in important categories
        important_classes = ['person', 'car', 'motorcycle', 'bicycle', 'bus', 'truck', 
                           'chair', 'table', 'bed', 'couch']
        if obstacle['class'].lower() not in important_classes:
            return False
        
        # Check 2: Confidence should be high for emergency stop
        if obstacle.get('confidence', 0) < 0.7:  # Higher threshold for emergency
            return False
        
        # Check 3: Object should be reasonably sized if it's close
        bbox = obstacle.get('bbox', [0, 0, 1, 1])
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if bbox_area < 500:  # If bbox is too small for a close object
            return False
            
        # Check 4: Object should be centered (not at edge of frame)
        direction = obstacle.get('direction', '')
        if direction not in ['center', 'ahead']:
            return False  # Only stop for centered objects
            
        return True

    # =====================================================
    # STATE MACHINE
    # =====================================================
    def _transition(self, new_state, message=None, is_emergency=False):
        now = time.time()

        if new_state == self.state:
            # Only repeat critical messages at a short interval (urgent)
            if new_state == "CRITICAL" and message:
                # If already critical, ensure fast continuous alerts
                if now - self.state_since >= 0.4:
                    priority = 'EMERGENCY' if is_emergency else 'OBSTACLE'
                    success = self._enqueue(message, priority=priority)
                    if success:
                        self.state_since = now
                    return success
            return False

        # Log state transition
        print(f"🔄 State transition: {self.state} -> {new_state}")
        if message:
            print(f"   Message: {message}")
        
        self.state = new_state
        self.state_since = now

        if message:
            # Map states to queue priorities
            prio = 'INFO'
            if new_state == 'CRITICAL':
                prio = 'EMERGENCY' if is_emergency else 'OBSTACLE'
            elif new_state == 'WARNING':
                prio = 'OBSTACLE'
                # When transitioning to WARNING, stop critical repeater and clear flags
                self._critical_is_approaching = False
                try:
                    if self._critical_repeater_thread and self._critical_repeater_thread.is_alive():
                        self._critical_repeater_stop.set()
                        self._critical_repeater_thread.join(timeout=0.3)
                except Exception:
                    pass
            success = self._enqueue(message, priority=prio)

            # If entering CRITICAL, start a repeater thread for continuous urgent alerts
            if new_state == 'CRITICAL' and success:
                # Stop any existing repeater
                try:
                    if self._critical_repeater_thread and self._critical_repeater_thread.is_alive():
                        self._critical_repeater_stop.set()
                        self._critical_repeater_thread.join(timeout=0.5)
                except Exception:
                    pass

                # Reset stop event and start new repeater
                self._critical_repeater_stop.clear()
                def _critical_repeater(msg, emergency_flag):
                    # Repeat critical messages only while object is actively approaching
                    # Stop repeating if the object is no longer approaching
                    repeat_count = 0
                    max_repeats = 10  # max 10 repeats (~6 seconds at 0.6s interval)
                    while (not self._critical_repeater_stop.is_set() and 
                           self.state == 'CRITICAL' and 
                           self._critical_is_approaching and 
                           repeat_count < max_repeats):
                        # Enqueue urgent message (EMERGENCY priority)
                        self._enqueue(msg, priority='EMERGENCY')
                        # Trigger haptic emergency vibration if available
                        try:
                            if self.haptic:
                                if emergency_flag:
                                    self.haptic.emergency_stop()
                                else:
                                    self.haptic.critical_warning()
                        except Exception:
                            pass
                        # Repeat at a fast interval
                        time.sleep(0.6)
                        repeat_count += 1
                    
                    # Once repeats are done or object stopped approaching, transition to clear
                    if repeat_count >= max_repeats:
                        print("⏹️ Critical repeater: max repeats reached, transitioning to CLEAR")

                self._critical_repeater_thread = threading.Thread(target=_critical_repeater, args=(message, is_emergency), daemon=True)
                self._critical_repeater_thread.start()

            return success
        elif new_state == "CLEAR":
            # Clear critical flags when transitioning to CLEAR
            self._critical_obstacle_id = None
            self._critical_is_approaching = False
            # Only announce clear every 15 seconds while moving
            if self.user_moving and now - getattr(self, 'last_clear_announce', 0) > 15.0:
                success = self._enqueue("Path clear.", priority='INFO')
                if success:
                    self.last_clear_announce = now
                return success
            # Ensure any critical repeater is stopped when clearing
            try:
                if self._critical_repeater_thread and self._critical_repeater_thread.is_alive():
                    self._critical_repeater_stop.set()
                    self._critical_repeater_thread.join(timeout=0.5)
            except Exception:
                pass
            return False
        
        return False

    # =====================================================
    # HELPER METHODS
    # =====================================================
    def _update_step_count(self):
        """Update step count from sensors"""
        if self.sensors:
            now = time.time()
            if now - self.last_step_check > 0.5:
                steps = self.sensors.get_steps()
                if steps > self.step_count:
                    self.user_moving = True
                    self.step_count = steps
                self.last_step_check = now

    def _update_movement_status(self):
        """Update user movement status"""
        now = time.time()
        if now - self.last_movement_check > 2.0:
            # If no steps detected for 5 seconds, assume not moving
            if self.sensors and now - self.last_step_check > 5.0:
                self.user_moving = False
            self.last_movement_check = now

    def _direction_phrase(self, direction: str) -> str:
        """Convert direction to relative phrase"""
        if direction == "left":
            return "on your left"
        if direction == "right":
            return "on your right"
        return "ahead of you"

    def _avoid_dir(self, direction):
        """Suggest avoidance direction"""
        if direction == "left":
            return "to your right"
        if direction == "right":
            return "to your left"
        return "with care"

    def _estimate_direction(self, bbox, frame_w):
        cx = (bbox[0] + bbox[2]) / 2
        x = cx / frame_w
        if x < 0.33:
            return "left"
        elif x > 0.66:
            return "right"
        return "center"

    def get_position(self, bbox, frame_w):
        """Legacy visualization helper"""
        return self._estimate_direction(bbox, frame_w)

    def assess_danger_level(self, track, distance, movement=None):
        """Legacy compatibility method"""
        if distance <= self.CRITICAL_DIST:
            return "critical"
        elif distance <= self.WARNING_DIST:
            return "high"
        elif distance <= self.SAFE_DIST:
            return "medium"
        return "low"

    # =====================================================
    # AUDIO QUEUE MANAGEMENT
    # =====================================================
    def _enqueue(self, text, priority: str = 'INFO'):
        """Add message to appropriate priority queue with anti-spam checks"""
        priority = priority.upper()
        if priority not in self.queues:
            priority = 'INFO'

        # Anti-spam: Don't queue if same message recently spoken
        now = time.time()
        if hasattr(self, 'last_message') and self.last_message == text:
            if now - self.last_speech_time < 2.0:
                return False

        # Shorten message for clarity
        short_text = text.strip()

        with self.q_cond:
            # Check if message already in queue (to prevent duplicates)
            for queue in self.queues.values():
                if short_text in queue:
                    return False
            
            self.queues[priority].append(short_text)
            self.q_cond.notify()
            print(f"🔊 Queued [{priority}]: {short_text}")
        return True

    def _audio_worker(self):
        """Worker thread that processes audio queue with priority"""
        print(f"🔊 Worker thread started")
        
        # Anti-flood: Minimum time between speeches
        # For emergency we allow faster repeats to feel continuous
        min_speech_interval = 0.4
        
        while True:
            try:
                with self.q_cond:
                    # Wait until any queue has items
                    has_items = any(len(q) for q in self.queues.values())
                    if not has_items:
                        # shorter wait to reduce audio latency for new urgent messages
                        self.q_cond.wait(timeout=0.1)

                    # Pick highest priority available
                    msg = None
                    chosen_prio = None
                    for p in ('EMERGENCY', 'OBSTACLE', 'NAVIGATION', 'INFO'):
                        if self.queues[p]:
                            msg = self.queues[p].pop(0)
                            chosen_prio = p
                            break

                if msg:
                    # Anti-flood: Wait minimum interval between speeches
                    now = time.time()
                    if now - self.last_speech_time < min_speech_interval:
                        time.sleep(min_speech_interval - (now - self.last_speech_time))
                    
                    # Scale speech rate based on priority (voice urgency)
                    # EMERGENCY: Fast (rate +2, ~200 WPM)
                    # OBSTACLE: Normal (rate -2, ~160 WPM) 
                    # NAVIGATION: Slow (rate -3, ~140 WPM)
                    # INFO: Very slow (rate -4, ~120 WPM)
                    rate_map = {
                        'EMERGENCY': 4,     # URGENT: Fastest speech
                        'OBSTACLE': -2,     # WARNING: Normal speed
                        'NAVIGATION': -3,   # HINT: Slightly slow
                        'INFO': -4          # BACKGROUND: Slowest
                    }
                    speech_rate = rate_map.get(chosen_prio, -2)
                    
                    print(f"🔊 Speaking [{chosen_prio}] (rate={speech_rate}): '{msg}'")
                    self.is_speaking = True
                    try:
                        self._speak_powershell(msg, rate=speech_rate)
                        self.last_speech_time = time.time()
                        self.last_message = msg
                    except Exception as e:
                        print(f"❌ TTS error: {e}")
                    finally:
                        self.is_speaking = False

                time.sleep(0.01)
                
            except Exception as e:
                print(f"❌ Worker error: {e}")
                time.sleep(0.1)

    def _speak_powershell(self, text, rate: int = -2):
        """
        Use Windows PowerShell to speak text with adjustable rate.
        rate: -4 to +4 (slower to faster)
              Default -2 = 160 WPM (good for blind users)
              Emergency: +2 = 200 WPM (urgent/fast approaching)
        """
        text = text.replace('"', '\\"')
        
        # Clamp rate to valid range
        rate = max(-4, min(4, rate))
        
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
            print(f"❌ PowerShell TTS error: {e}")

    # =====================================================
    # PUBLIC METHODS
    # =====================================================
    def speak(self, message: str):
        """Legacy speak method"""
        self._enqueue(message, priority='INFO')

    def clear_history(self):
        """Clear object history"""
        self.state = "CLEAR"
        self.state_since = time.time()
        self.object_announce_state.clear()
        self.object_positions.clear()
        self.false_stop_count = 0
        print("🗑️ Audio history cleared")

    def test_tts(self):
        """Direct TTS test"""
        print("🔊 TEST: Direct TTS test starting...")
        try:
            msg = "Audio test complete."
            print(f"🔊 TEST: Speaking: {msg}")
            self._speak_powershell(msg)
            print("✅ TEST: TTS worked!")
            return True
        except Exception as e:
            print(f"❌ TEST: TTS failed: {e}")
            return False


# =====================================================
# PUBLIC ALIASES
# =====================================================
AudioFeedback = AudioGuidance
IntelligentAudioFeedback = AudioGuidance


# import pyttsx3
# import threading
# import time
# import yaml
# from queue import Queue

# print("🔥 LOADED audio_feedback.py FROM:", __file__)
# print("✅ audio_feedback.py LOADED")


# class SmartAudioGuidance:
#     def __init__(self, config_path: str = "config.yaml"):
#         # ===============================
#         # Load configuration
#         # ===============================
#         try:
#             with open(config_path, 'r') as f:
#                 self.config = yaml.safe_load(f)
#         except FileNotFoundError:
#             print(f"❌ Config not found at {config_path}, using defaults")
#             self.config = {
#                 'audio': {
#                     'rate': 160,
#                     'volume': 0.9,
#                     'guidance_mode': 'discrete',
#                     'announcement_intervals': {
#                         'critical': 3.0,
#                         'warning': 4.0,
#                         'normal': 8.0,
#                         'clear': 15.0
#                     }
#                 },
#                 'guidance': {
#                     'safe_distance': 3.0,
#                     'warning_distance': 1.5,
#                     'critical_distance': 0.8,
#                     'stop_distance': 0.5
#                 }
#             }

#         audio = self.config['audio']
#         guidance = self.config['guidance']

#         # ===============================
#         # Distance thresholds
#         # ===============================
#         self.stop_distance = guidance['stop_distance']
#         self.critical_distance = guidance['critical_distance']
#         self.warning_distance = guidance['warning_distance']
#         self.safe_distance = guidance['safe_distance']

#         # ===============================
#         # State
#         # ===============================
#         self.guidance_mode = audio.get('guidance_mode', 'discrete')
#         self.intervals = audio.get('announcement_intervals', {})
#         self.last_spoken_message = ""
#         self.last_audio_time = 0
#         self.last_guidance_type = ""
#         self.is_speaking = False

#         # Vision stability
#         self.last_detected_time = 0
#         self.distance_buffer = []

#         # ===============================
#         # Audio system
#         # ===============================
#         self.message_queue = Queue(maxsize=1)

#         try:
#             self.tts_engine = pyttsx3.init()
#             voices = self.tts_engine.getProperty('voices')
#             if voices:
#                 self.tts_engine.setProperty('voice', voices[0].id)

#             self.tts_engine.setProperty('rate', audio['rate'])
#             self.tts_engine.setProperty('volume', audio['volume'])
#             print("🔊 Audio system initialized")

#         except Exception as e:
#             print(f"❌ TTS error: {e}")
#             self.tts_engine = None

#         self.audio_thread = threading.Thread(
#             target=self._audio_worker,
#             daemon=True
#         )
#         self.audio_thread.start()

#         print("🎵 Smart Audio Guidance READY (INDUSTRY DISCRETE MODE)")

#     # =====================================================
#     # Distance & position helpers
#     # =====================================================
#     def estimate_distance(self, bbox, frame_w, frame_h):
#         area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
#         frame_area = frame_w * frame_h
#         ratio = area / frame_area

#         if ratio < 0.001:
#             return 8.0
#         elif ratio < 0.01:
#             return 3.0
#         elif ratio < 0.05:
#             return 2.0
#         elif ratio < 0.1:
#             return 1.5
#         elif ratio < 0.2:
#             return 1.0
#         return 0.5

#     def get_position(self, bbox, frame_w):
#         center_x = (bbox[0] + bbox[2]) / 2
#         x = center_x / frame_w

#         if x < 0.33:
#             return "left"
#         elif x < 0.66:
#             return "ahead"
#         return "right"

#     # =====================================================
#     # MAIN GUIDANCE ENTRY
#     # =====================================================
#     def provide_smart_guidance(self, tracks, frame_w, frame_h):
#         if self.guidance_mode == "silent":
#             return False

#         now = time.time()

#         if self.is_speaking:
#             return False

#         # Handle YOLO flicker
#         if not tracks:
#             if now - self.last_detected_time < 2.0:
#                 return False

#             return self._attempt_speak(
#                 "Path is clear. Continue straight.",
#                 "clear",
#                 now
#             )

#         self.last_detected_time = now

#         closest = None
#         for t in tracks:
#             raw_dist = self.estimate_distance(t['bbox'], frame_w, frame_h)

#             self.distance_buffer.append(raw_dist)
#             if len(self.distance_buffer) > 5:
#                 self.distance_buffer.pop(0)

#             dist = sum(self.distance_buffer) / len(self.distance_buffer)

#             if closest is None or dist < closest['distance']:
#                 closest = {
#                     'class': t['class_name'],
#                     'distance': dist,
#                     'position': self.get_position(t['bbox'], frame_w)
#                 }

#         if closest['distance'] <= self.stop_distance:
#             return self._attempt_speak(
#                 f"Emergency stop! {closest['class']} too close.",
#                 "critical",
#                 now
#             )

#         if closest['distance'] <= self.critical_distance:
#             return self._attempt_speak(
#                 f"Stop! {closest['class']} ahead.",
#                 "critical",
#                 now
#             )

#         if closest['distance'] <= self.warning_distance:
#             return self._attempt_speak(
#                 f"{closest['class']} ahead. Slow down.",
#                 "warning",
#                 now
#             )

#         return False

#     # =====================================================
#     # DISCRETE SPEAK CONTROL (OPTION B)
#     # =====================================================
#     def _attempt_speak(self, message, gtype, now):
#         interval = self.intervals.get(gtype, 5.0)

#         # 🔁 Critical repeats
#         if gtype == "critical":
#             if self.last_audio_time != 0 and now - self.last_audio_time < interval:
#                 return False
#         else:
#             if message == self.last_spoken_message:
#                 return False
#             if self.last_audio_time != 0 and now - self.last_audio_time < interval:
#                 return False

#         if not self.message_queue.empty():
#             return False

#         self.last_audio_time = now
#         self.last_spoken_message = message
#         self.last_guidance_type = gtype
#         self.message_queue.put(message)

#         print(f"🔊 [{gtype.upper()}] {message}")
#         return True

#     # =====================================================
#     # Audio worker
#     # =====================================================
#     def _audio_worker(self):
#         while True:
#             if not self.message_queue.empty():
#                 msg = self.message_queue.get()
#                 self._speak_now(msg)
#             time.sleep(0.05)

#     def _speak_now(self, message):
#         self.is_speaking = True
#         try:
#             if self.tts_engine:
#                 self.tts_engine.say(message)
#                 self.tts_engine.runAndWait()
#         except Exception as e:
#             print(f"❌ Audio error: {e}")
#         self.is_speaking = False

#     # =====================================================
#     # Compatibility methods
#     # =====================================================
#     def speak(self, message: str):
#         self._attempt_speak(message, "normal", time.time())

#     def test_audio(self):
#         self.speak("Smart guidance system ready. Audio is working.")

#     def provide_intelligent_guidance(self, tracks, frame_w, frame_h):
#         return self.provide_smart_guidance(tracks, frame_w, frame_h)

#     def assess_danger_level(self, track, distance, movement=None):
#         if distance <= self.critical_distance:
#             return "critical"
#         elif distance <= self.warning_distance:
#             return "high"
#         elif distance <= self.safe_distance:
#             return "medium"
#         return "low"

#     def clear_history(self):
#         self.last_spoken_message = ""
#         self.last_audio_time = 0
#         self.distance_buffer.clear()
#         print("🗑️ Audio history cleared")


# # =====================================================
# # Aliases for backward compatibility
# # =====================================================
# AudioFeedback = SmartAudioGuidance
# IntelligentAudioFeedback = SmartAudioGuidance


