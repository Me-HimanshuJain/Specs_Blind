# Smart Glasses for Blind Users - Quick Start Guide

## Before You Start

- Ensure camera is working and pointing forward
- Check that audio speakers are at comfortable volume
- Make sure haptic motor is mounted securely
- Fully charge the device (or verify battery is at least 50%)

---

## First Time Setup

### 1. System Startup
```
Press power button
Listen for: "Smart Goggle System ready"
Feel: Gentle center vibration (safe path confirmation)
```

### 2. Audio Test
```
Press 'A' button (or say "Test audio")
Listen for: "Audio test complete"
Confirm: Audio is clear and volume is good
If not clear: Adjust volume dial before continuing
```

### 3. Initial Threat Scan
```
System starts scanning surroundings
Listen for obstacles as system detects them
Get verbal descriptions of distances and directions
This takes about 5-10 seconds
```

### 4. You're Ready!
```
Listen for: "Path clear" or directional warning
System now running in full guidance mode
```

---

## How the System Talks to You

### Audio Speeds = Urgency Levels

**VERY FAST (Emergency)**
- "STOP! Object very close!"
- Means: Danger within 2 feet (0.6m)
- **Action**: Stop immediately

**FAST (Warning)**
- "Car approaching on your left 5 feet"
- Means: Threat getting closer, within 6 feet
- **Action**: Listen carefully, prepare to move

**NORMAL (Direction)**
- "Move right"
- Means: Path suggestion to avoid detected obstacle
- **Action**: Adjust course as suggested

**SLOW (Background Info)**
- "Person standing on your right 10 feet away"
- Means: Non-threatening object detected at distance
- **Action**: Just listen, continue walking

### Distance Descriptions

```
< 2 feet  (0.6m)  = "STOP! Very close!"
2-3 feet  (1.0m)  = "Critical! Object very close!"
3-6 feet  (2.0m)  = "[Object] approaching"
6+ feet   (3.0m)  = "[Object] on your [direction]"
```

### Direction References

```
Center / Ahead = Directly in front of you
Left  = 45° to your left
Right = 45° to your right
```

---

## Button Controls

### Single Tap (Quick Press)
**When Paused**:
- Hears: "Resumed"
- System: Continues normal operation

**When Running**:
- Hears: "Paused"
- System: Stops announcements, no guidance
- Haptic: No vibrations

### Long Press (Hold 1+ second)
**Effect**:
- System says current status
- Example: "Battery 85%, 2 threats nearby, 2 hours runtime"
- Useful for checking system health

---

## Haptic Feedback (Vibrations)

### Emergency SOS Pattern
```
Strong vibration: Pulse-Pulse-Pulse
Meaning: IMMEDIATE DANGER
Action: STOP and listen to audio description
```

### Critical Warning (Double Pulse)
```
Vibration: Shake-Pause-Shake
Meaning: High-speed approaching threat
Action: Move away from vibration direction
```

### Obstacle Warning (Single Pulse)
```
Vibration: Sharp vibration on one side
Meaning: Obstacle detected nearby
Action: Move away from vibration side
```

### Navigation Hint (Directional)
```
Left vibration  = Turn left
Right vibration = Turn right
Center vibration = Go straight
Meaning: Suggested safe path
Action: Follow the direction
```

### Safe Path (Gentle)
```
Soft, brief vibration
Meaning: Clear path ahead
Action: Continue walking forward
```

---

## Common Scenarios

### Scenario 1: Crossing Intersection
```
1. System says: "Intersection detected. Quiet moment."
   (Few vehicles approaching)

2. Audio: "Car on your left, 20 feet away"
   (Vibration on left side)
   Action: Wait for car to pass

3. Audio: "Path clear. You may cross."
   (Gentle center vibration)
   Action: Cross straight ahead

4. Audio: "Curb ahead, 3 feet away"
   (Slow audio, low vibration)
   Action: Prepare to stop
```

### Scenario 2: Crowded Sidewalk
```
1. Audio: "Multiple people detected"
   (System in PERFORMANCE mode, multiple vibrations)

2. System describes positions:
   - "Person on your left, 4 feet"
   - "Person on your right, 5 feet"
   - "Two people ahead, 6 feet"

3. Audio: "Move left to pass"
   (Left vibration suggests direction)
   Action: Move left carefully

4. System updates: "Clear. Continue ahead"
   Action: Resume normal walking
```

### Scenario 3: Battery Low (10% or less)
```
1. Audio: "Battery critical, 10%"
   (Fast vibration warning)

2. System enters ECO mode (lower accuracy)
   Audio: "Only warning major threats"

3. Suggest: "Find charging location soon"
   Action: Navigate to known charger

4. When charged: System returns to normal mode
```

---

## What to Do If...

### "System Says Nothing But I See (Sense) Obstacle"
```
Problem: False negative (system missed object)
Solution:
- System might have < 60% confidence
- Describe obstacle shape/color to improve future detection
- Continue cautiously, feel around with cane
```

### "System Talks Too Much"
```
Problem: Too many announcements
Solution:
- Increase update_interval in config.yaml (1.0 → 2.0)
- Or press 'P' button to pause, tap to resume
- Long press to get status, confirm you want to continue
```

### "System Talks Too Little"
```
Problem: Missing announcements
Solution:
- Decrease update_interval in config.yaml (0.5 → 0.3)
- Or reduce detection_frequency (1 → 0, every frame)
- Run system test: Press 'A' button
```

### "Audio Cuts Out / Haptic Not Vibrating"
```
Problem: Hardware failure
Solution:
- Check volume is not muted
- Verify speaker/motor connections
- Restart system: Power off 30 seconds, power on
- Try audio test: Press 'A' button
```

### "System Too Slow / Detecting Late"
```
Problem: Latency (response delay)
Solution:
- Confirm you're in PERFORMANCE mode (see battery)
- Reduce inference_size from 416 to 320 in config.yaml
- Close other apps running on device
- System may boost to PERFORMANCE mode automatically in high-threat areas
```

### "System Says I'm Going Wrong Direction"
```
Problem: Incorrect navigation guidance
Solution:
- System uses visual object detection (not compass)
- It suggests "move left/right" based on obstacles NEAR you
- For long-distance navigation, use smartphone GPS + map app
- System only provides immediate obstacle avoidance
```

---

## Battery Management Tips

### Extend Battery Life
1. Use ECO mode when in low-threat area
2. Reduce volume slightly (saves processor power)
3. Disable visualization if using connected display
4. Keep firmware updated
5. Reduce detection_frequency if in simple environment

### Check Battery
```
Long press button
Listen for: "Battery [X]%, Mode [BALANCED/ECO/PERFORMANCE], Runtime [X hours]"
```

### When Battery Critical (< 5%)
```
System automatically:
- Switches to extreme ECO mode
- Only announces emergencies (< 1.0m)
- Reduces FPS to minimum
- Recommend: Stop and charge immediately
```

---

## Customizing for Your Needs

### If You Walk Very Fast
- Increase detection_frequency to 1 (every frame)
- Reduce announcement_intervals for faster updates
- Keep in PERFORMANCE mode for max responsiveness

### If You Prefer Lots of Detail
- Increase audio update_interval (0.5 → 1.0)
- Enable background INFO announcements
- Reduce suppression of static objects

### If You Prefer Minimal Audio
- Increase announcement_intervals (reduce chatter)
- Enable step-based suppression (skip INFO while walking)
- Keep detection_frequency at 2 (every 2nd frame)

### If You Have Hearing Difficulties
- Increase volume to maximum in config.yaml
- Use haptic feedback as primary alert method
- Reduce speech rate adjustment range (-4 to +2 is default, remove variation)

### If You're in Unfamiliar Area
- Switch to PERFORMANCE mode manually
- Increase announcement_intervals to hear more details
- Use threat tracking: Long press for threat summary

---

## Emergency Procedures

### If System Goes Non-Responsive
```
1. Press power button 3 times quickly (triple-tap)
2. Hold power button 10 seconds (hard reset)
3. System restarts in ECO mode
4. Contact support if problem persists
```

### If You Need Help
```
Voice command: "Help" or "Emergency"
System will:
1. Sound alarm (3 vibrations + audio)
2. Send location to emergency contact (if GPS enabled)
3. Speak: "Emergency services contacted"
```

### If You Get Lost
```
1. Stop walking
2. Say "Status" or long-press button
3. System will:
   - Describe current location (obstacles, environment)
   - Tell you GPS coordinates (if outdoors with signal)
   - Suggest nearest safe shelter/street
```

---

## Tips for Best Results

### 1. Keep Camera Clean
- Wipe camera lens with soft cloth every hour
- Rain/fog reduces accuracy significantly
- Use protective cover when not in use

### 2. Maintain Good Posture
- Wear glasses at eye level (proper height)
- Camera should point 15° downward (not straight ahead)
- Adjust strap so device doesn't move while walking

### 3. Start in Familiar Areas
- First few times: Use in known locations
- Practice trusting the system's guidance
- Learn the voice patterns and vibration meanings

### 4. Use Both Audio and Haptic
- Audio tells you WHAT (object description)
- Haptic tells you WHERE (direction/urgency)
- Together they provide complete picture

### 5. Combine with Other Tools
- Use white cane for ground/steps
- Use smartphone GPS for long-distance navigation
- Use system for immediate obstacle avoidance
- Ask sighted person for confirmation when uncertain

---

## Regular Maintenance

### Daily
- Charge device overnight or when < 20%
- Wipe camera lens
- Test audio (press 'A' button)

### Weekly
- Clean sensors (GPS, IMU)
- Check all vibration patterns working
- Verify battery drain rate normal

### Monthly
- Update system firmware
- Recalibrate sensors if available
- Check for service bulletins
- Test in different environments

---

## Support Resources

### Getting Help
```
In-app: Say "Help" or press 'H' button
Online: Visit [support-website]
Phone: Call [support-number]
Email: support@[company].com
```

### Before Contacting Support, Provide:
1. Device type and OS version
2. What you were doing when problem occurred
3. Error message (if any)
4. Battery level and mode
5. Environmental conditions (indoor/outdoor, lighting)

---

## Remember

> **This system is designed to ASSIST, not REPLACE your judgment.**

- Always trust your cane and spatial awareness
- System has < 100% accuracy (usually 95-98% in good conditions)
- Use system alongside traditional mobility techniques
- If something feels wrong, it probably is - proceed cautiously
- You are in control - system is your tool

**You've got this! Stay safe! 🎯**

