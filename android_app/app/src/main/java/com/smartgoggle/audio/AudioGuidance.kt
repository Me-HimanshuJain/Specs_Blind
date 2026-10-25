package com.smartgoggle.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import com.smartgoggle.ml.Track
import java.util.*

class AudioGuidance(private val context: Context) {
    
    private var tts: TextToSpeech? = null
    private var lastAnnouncementTime = 0L
    private val announcementInterval = 3000L // 3 seconds
    
    private val safeDistance = 4.0f
    private val warningDistance = 2.0f
    private val criticalDistance = 1.0f
    
    fun initialize() {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.ENGLISH
                tts?.setSpeechRate(1.2f)
                tts?.setPitch(1.0f)
                Log.d("AudioGuidance", "TTS initialized successfully")
            } else {
                Log.e("AudioGuidance", "TTS initialization failed")
            }
        }
    }
    
    fun provideGuidance(tracks: List<Track>) {
        val currentTime = System.currentTimeMillis()
        
        // Rate limiting
        if (currentTime - lastAnnouncementTime < announcementInterval) {
            return
        }
        
        val guidance = generateGuidanceMessage(tracks)
        if (guidance.isNotEmpty()) {
            speak(guidance)
            lastAnnouncementTime = currentTime
        }
    }
    
    private fun generateGuidanceMessage(tracks: List<Track>): String {
        if (tracks.isEmpty()) {
            return "Path is clear ahead. Continue straight."
        }
        
        // Categorize obstacles by danger level
        val criticalObstacles = tracks.filter { it.dangerLevel == "critical" }
        val highObstacles = tracks.filter { it.dangerLevel == "high" }
        val mediumObstacles = tracks.filter { it.dangerLevel == "medium" }
        
        return when {
            criticalObstacles.isNotEmpty() -> generateCriticalGuidance(criticalObstacles)
            highObstacles.isNotEmpty() -> generateHighPriorityGuidance(highObstacles)
            mediumObstacles.isNotEmpty() -> generateMediumPriorityGuidance(mediumObstacles)
            else -> generateLowPriorityGuidance(tracks)
        }
    }
    
    private fun generateCriticalGuidance(obstacles: List<Track>): String {
        val obstacle = obstacles.first()
        return if (obstacle.distance < 0.5f) {
            "EMERGENCY STOP! ${obstacle.className} extremely close ${obstacle.position} at ${obstacle.distance}m!"
        } else {
            "STOP IMMEDIATELY! ${obstacle.className} very close ${obstacle.position} at ${obstacle.distance}m!"
        }
    }
    
    private fun generateHighPriorityGuidance(obstacles: List<Track>): String {
        val obstacle = obstacles.first()
        return if (obstacle.movement == "moving") {
            "Caution! ${obstacle.className} approaching ${obstacle.position} at ${obstacle.distance}m. Slow down."
        } else {
            "Caution! ${obstacle.className} close ${obstacle.position} at ${obstacle.distance}m. Proceed carefully."
        }
    }
    
    private fun generateMediumPriorityGuidance(obstacles: List<Track>): String {
        val obstacle = obstacles.first()
        return if (obstacle.className == "wall") {
            "Wall detected ${obstacle.position} at ${obstacle.distance}m. Continue straight."
        } else if (obstacle.movement == "moving") {
            "${obstacle.className} moving ${obstacle.position} at ${obstacle.distance}m"
        } else {
            "${obstacle.className} ${obstacle.position} at ${obstacle.distance}m"
        }
    }
    
    private fun generateLowPriorityGuidance(obstacles: List<Track>): String {
        val obstacle = obstacles.first()
        return "${obstacle.className} ${obstacle.position} at ${obstacle.distance}m"
    }
    
    private fun speak(text: String) {
        try {
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, null)
            Log.d("AudioGuidance", "Speaking: $text")
        } catch (e: Exception) {
            Log.e("AudioGuidance", "TTS error", e)
        }
    }
    
    fun stop() {
        tts?.stop()
    }
    
    fun release() {
        tts?.shutdown()
        tts = null
    }
}

