package com.smartgoggle.ml

import android.util.Log
import kotlin.math.sqrt

class ObjectTracker {
    
    private val trackers = mutableListOf<KalmanTracker>()
    private var nextId = 0
    private val maxAge = 20
    private val minHits = 3
    private val iouThreshold = 0.3f
    
    fun update(detections: List<Detection>): List<Track> {
        val tracks = mutableListOf<Track>()
        
        // Predict existing tracks
        for (tracker in trackers) {
            tracker.predict()
        }
        
        // Associate detections with tracks
        val matches = associateDetectionsToTracks(detections, trackers)
        
        // Update matched tracks
        for ((detection, tracker) in matches) {
            tracker.update(detection.bbox)
            val track = createTrackFromTracker(tracker)
            tracks.add(track)
        }
        
        // Create new tracks for unmatched detections
        for (detection in detections) {
            if (!matches.containsKey(detection)) {
                val tracker = KalmanTracker(nextId++, detection.bbox, detection.className)
                trackers.add(tracker)
                val track = createTrackFromTracker(tracker)
                tracks.add(track)
            }
        }
        
        // Remove old tracks
        trackers.removeAll { it.age > maxAge }
        
        return tracks
    }
    
    private fun associateDetectionsToTracks(
        detections: List<Detection>,
        trackers: List<KalmanTracker>
    ): Map<Detection, KalmanTracker> {
        val matches = mutableMapOf<Detection, KalmanTracker>()
        
        if (detections.isEmpty() || trackers.isEmpty()) {
            return matches
        }
        
        // Calculate IoU matrix
        val iouMatrix = Array(detections.size) { FloatArray(trackers.size) }
        
        for (i in detections.indices) {
            for (j in trackers.indices) {
                iouMatrix[i][j] = calculateIoU(detections[i].bbox, trackers[j].getState())
            }
        }
        
        // Simple greedy assignment
        val usedDetections = BooleanArray(detections.size)
        val usedTrackers = BooleanArray(trackers.size)
        
        for (i in detections.indices) {
            var bestTracker = -1
            var bestIoU = 0f
            
            for (j in trackers.indices) {
                if (!usedTrackers[j] && iouMatrix[i][j] > bestIoU && iouMatrix[i][j] > iouThreshold) {
                    bestIoU = iouMatrix[i][j]
                    bestTracker = j
                }
            }
            
            if (bestTracker != -1) {
                matches[detections[i]] = trackers[bestTracker]
                usedDetections[i] = true
                usedTrackers[bestTracker] = true
            }
        }
        
        return matches
    }
    
    private fun calculateIoU(bbox1: FloatArray, bbox2: FloatArray): Float {
        val x1 = maxOf(bbox1[0], bbox2[0])
        val y1 = maxOf(bbox1[1], bbox2[1])
        val x2 = minOf(bbox1[2], bbox2[2])
        val y2 = minOf(bbox1[3], bbox2[3])
        
        if (x2 <= x1 || y2 <= y1) return 0f
        
        val intersection = (x2 - x1) * (y2 - y1)
        val area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        val area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        val union = area1 + area2 - intersection
        
        return if (union > 0) intersection / union else 0f
    }
    
    private fun createTrackFromTracker(tracker: KalmanTracker): Track {
        val bbox = tracker.getState()
        val distance = estimateDistance(bbox)
        val position = getPosition(bbox)
        val movement = tracker.getMovementState()
        val dangerLevel = assessDangerLevel(tracker.className, distance, movement)
        
        return Track(
            trackId = tracker.id,
            className = tracker.className,
            bbox = bbox,
            distance = distance,
            position = position,
            movement = movement,
            dangerLevel = dangerLevel
        )
    }
    
    private fun estimateDistance(bbox: FloatArray): Float {
        val width = bbox[2] - bbox[0]
        val height = bbox[3] - bbox[1]
        val area = width * height
        
        // Simple distance estimation based on object size
        return when {
            area > 50000 -> 0.5f  // Very close
            area > 20000 -> 1.0f  // Close
            area > 10000 -> 2.0f  // Medium
            area > 5000 -> 3.0f   // Far
            else -> 5.0f          // Very far
        }
    }
    
    private fun getPosition(bbox: FloatArray): String {
        val centerX = (bbox[0] + bbox[2]) / 2
        val normalizedX = centerX / 640f // Assuming 640px width
        
        return when {
            normalizedX < 0.25f -> "far left"
            normalizedX < 0.4f -> "left"
            normalizedX < 0.6f -> "ahead"
            normalizedX < 0.75f -> "right"
            else -> "far right"
        }
    }
    
    private fun assessDangerLevel(className: String, distance: Float, movement: String): String {
        val isHighPriority = className in setOf("person", "car", "motorcycle", "bicycle", "bus", "truck")
        val isMoving = movement == "moving"
        
        return when {
            distance < criticalDistance -> "critical"
            distance < warningDistance && (isHighPriority || isMoving) -> "high"
            distance < safeDistance -> "medium"
            else -> "low"
        }
    }
    
    companion object {
        private const val criticalDistance = 1.0f
        private const val warningDistance = 2.0f
        private const val safeDistance = 4.0f
    }
}

class KalmanTracker(
    val id: Int,
    val className: String,
    initialBbox: FloatArray
) {
    private var x: Float = (initialBbox[0] + initialBbox[2]) / 2
    private var y: Float = (initialBbox[1] + initialBbox[3]) / 2
    private var width: Float = initialBbox[2] - initialBbox[0]
    private var height: Float = initialBbox[3] - initialBbox[1]
    private var vx: Float = 0f
    private var vy: Float = 0f
    private var vw: Float = 0f
    private var vh: Float = 0f
    
    var age = 1
    var hits = 1
    var timeSinceUpdate = 0
    
    private val processNoise = 0.01f
    private val measurementNoise = 0.1f
    
    fun predict() {
        // Simple prediction model
        x += vx
        y += vy
        width += vw
        height += vh
        
        // Add process noise
        x += (Math.random() - 0.5) * processNoise
        y += (Math.random() - 0.5) * processNoise
        
        age++
        timeSinceUpdate++
    }
    
    fun update(bbox: FloatArray) {
        val newX = (bbox[0] + bbox[2]) / 2
        val newY = (bbox[1] + bbox[3]) / 2
        val newWidth = bbox[2] - bbox[0]
        val newHeight = bbox[3] - bbox[1]
        
        // Update velocities
        vx = newX - x
        vy = newY - y
        vw = newWidth - width
        vh = newHeight - height
        
        // Update state with measurement
        x = newX
        y = newY
        width = newWidth
        height = newHeight
        
        hits++
        timeSinceUpdate = 0
    }
    
    fun getState(): FloatArray {
        return floatArrayOf(
            x - width / 2,
            y - height / 2,
            x + width / 2,
            y + height / 2
        )
    }
    
    fun getMovementState(): String {
        val speed = sqrt(vx * vx + vy * vy)
        return when {
            speed > 5f -> "moving"
            speed > 1f -> "slightly_moving"
            else -> "stationary"
        }
    }
}

