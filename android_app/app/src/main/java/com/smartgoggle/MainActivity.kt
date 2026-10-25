package com.smartgoggle

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModelProvider
import com.smartgoggle.camera.USBCameraManager
import com.smartgoggle.ml.ObjectDetector
import com.smartgoggle.ml.ObjectTracker
import com.smartgoggle.audio.AudioGuidance
import kotlinx.coroutines.*

class MainActivity : AppCompatActivity() {
    
    private lateinit var viewModel: SmartGoggleViewModel
    private lateinit var cameraManager: USBCameraManager
    private lateinit var objectDetector: ObjectDetector
    private lateinit var objectTracker: ObjectTracker
    private lateinit var audioGuidance: AudioGuidance
    
    private lateinit var startButton: Button
    private lateinit var statusText: TextView
    private lateinit var fpsText: TextView
    private lateinit var objectsText: TextView
    
    private var isProcessing = false
    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    
    // Permission launcher
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (allGranted) {
            initializeComponents()
        } else {
            Toast.makeText(this, "Permissions required for camera and audio", Toast.LENGTH_LONG).show()
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        initializeViews()
        checkPermissions()
    }
    
    private fun initializeViews() {
        startButton = findViewById(R.id.startButton)
        statusText = findViewById(R.id.statusText)
        fpsText = findViewById(R.id.fpsText)
        objectsText = findViewById(R.id.objectsText)
        
        startButton.setOnClickListener {
            if (isProcessing) {
                stopProcessing()
            } else {
                startProcessing()
            }
        }
    }
    
    private fun checkPermissions() {
        val permissions = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.WAKE_LOCK
        )
        
        val missingPermissions = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        
        if (missingPermissions.isEmpty()) {
            initializeComponents()
        } else {
            requestPermissionLauncher.launch(permissions)
        }
    }
    
    private fun initializeComponents() {
        viewModel = ViewModelProvider(this)[SmartGoggleViewModel::class.java]
        
        try {
            cameraManager = USBCameraManager(this)
            objectDetector = ObjectDetector(this)
            objectTracker = ObjectTracker()
            audioGuidance = AudioGuidance(this)
            
            // Initialize components
            cameraManager.initializeCamera()
            objectDetector.initializeModel()
            audioGuidance.initialize()
            
            updateStatus("System initialized successfully")
            
        } catch (e: Exception) {
            updateStatus("Initialization failed: ${e.message}")
            Toast.makeText(this, "Failed to initialize system", Toast.LENGTH_LONG).show()
        }
    }
    
    private fun startProcessing() {
        if (!::cameraManager.isInitialized) {
            Toast.makeText(this, "System not initialized", Toast.LENGTH_SHORT).show()
            return
        }
        
        isProcessing = true
        startButton.text = "Stop"
        updateStatus("Processing started...")
        
        // Start background processing
        scope.launch {
            processFrames()
        }
    }
    
    private fun stopProcessing() {
        isProcessing = false
        startButton.text = "Start"
        updateStatus("Processing stopped")
        
        // Stop audio guidance
        if (::audioGuidance.isInitialized) {
            audioGuidance.stop()
        }
    }
    
    private suspend fun processFrames() {
        var frameCount = 0
        val startTime = System.currentTimeMillis()
        
        while (isProcessing) {
            try {
                // Capture frame from camera
                val bitmap = cameraManager.captureFrame()
                if (bitmap != null) {
                    // Run detection on background thread
                    val detections = withContext(Dispatchers.Default) {
                        objectDetector.detectObjects(bitmap)
                    }
                    
                    // Update tracker
                    val tracks = objectTracker.update(detections)
                    
                    // Provide audio guidance
                    audioGuidance.provideGuidance(tracks)
                    
                    // Update UI
                    updateUI(tracks, frameCount, startTime)
                }
                
                frameCount++
                
                // Small delay to prevent overwhelming the system
                delay(100)
                
            } catch (e: Exception) {
                updateStatus("Processing error: ${e.message}")
                break
            }
        }
    }
    
    private fun updateUI(tracks: List<Track>, frameCount: Int, startTime: Long) {
        runOnUiThread {
            // Update FPS
            val elapsed = System.currentTimeMillis() - startTime
            val fps = if (elapsed > 0) (frameCount * 1000) / elapsed else 0
            fpsText.text = "FPS: $fps"
            
            // Update object count
            objectsText.text = "Objects: ${tracks.size}"
            
            // Update status
            if (tracks.isNotEmpty()) {
                val criticalCount = tracks.count { it.dangerLevel == "critical" }
                val highCount = tracks.count { it.dangerLevel == "high" }
                
                when {
                    criticalCount > 0 -> updateStatus("CRITICAL: $criticalCount obstacles")
                    highCount > 0 -> updateStatus("WARNING: $highCount obstacles")
                    else -> updateStatus("Monitoring: ${tracks.size} objects")
                }
            } else {
                updateStatus("Path clear")
            }
        }
    }
    
    private fun updateStatus(message: String) {
        runOnUiThread {
            statusText.text = message
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        isProcessing = false
        scope.cancel()
        
        // Cleanup resources
        if (::cameraManager.isInitialized) {
            cameraManager.release()
        }
        if (::audioGuidance.isInitialized) {
            audioGuidance.release()
        }
    }
    
    override fun onPause() {
        super.onPause()
        if (isProcessing) {
            stopProcessing()
        }
    }
}

