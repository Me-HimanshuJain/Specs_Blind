package com.smartgoggle.camera

import android.content.Context
import android.graphics.Bitmap
import android.graphics.ImageFormat
import android.graphics.SurfaceTexture
import android.hardware.camera2.*
import android.hardware.usb.UsbDevice
import android.hardware.usb.UsbManager
import android.media.ImageReader
import android.util.Log
import android.util.Size
import android.view.Surface
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class USBCameraManager(private val context: Context) {
    
    private val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
    private val usbManager = context.getSystemService(Context.USB_SERVICE) as UsbManager
    
    private var cameraDevice: CameraDevice? = null
    private var captureSession: CameraCaptureSession? = null
    private var imageReader: ImageReader? = null
    private var backgroundHandler: android.os.Handler? = null
    
    private val cameraId: String? by lazy {
        findUSBCamera()
    }
    
    private val previewSize = Size(640, 480)
    private val imageFormat = ImageFormat.YUV_420_888
    
    fun initializeCamera() {
        if (cameraId == null) {
            throw RuntimeException("No USB camera found")
        }
        
        try {
            openCamera()
        } catch (e: Exception) {
            Log.e("USBCameraManager", "Failed to initialize camera", e)
            throw e
        }
    }
    
    private fun findUSBCamera(): String? {
        val cameraList = cameraManager.cameraIdList
        
        for (id in cameraList) {
            val characteristics = cameraManager.getCameraCharacteristics(id)
            val facing = characteristics.get(CameraCharacteristics.LENS_FACING)
            
            // Look for external camera (USB OTG)
            if (facing == CameraCharacteristics.LENS_FACING_EXTERNAL) {
                Log.d("USBCameraManager", "Found USB camera: $id")
                return id
            }
        }
        
        // Fallback: try first available camera
        if (cameraList.isNotEmpty()) {
            Log.w("USBCameraManager", "No external camera found, using first available: ${cameraList[0]}")
            return cameraList[0]
        }
        
        return null
    }
    
    private fun openCamera() {
        val id = cameraId ?: throw RuntimeException("No camera ID available")
        
        try {
            cameraManager.openCamera(id, cameraStateCallback, backgroundHandler)
        } catch (e: SecurityException) {
            Log.e("USBCameraManager", "Camera permission denied", e)
            throw e
        }
    }
    
    private val cameraStateCallback = object : CameraDevice.StateCallback() {
        override fun onOpened(camera: CameraDevice) {
            cameraDevice = camera
            Log.d("USBCameraManager", "Camera opened successfully")
            createCaptureSession()
        }
        
        override fun onDisconnected(camera: CameraDevice) {
            camera.close()
            cameraDevice = null
            Log.w("USBCameraManager", "Camera disconnected")
        }
        
        override fun onError(camera: CameraDevice, error: Int) {
            camera.close()
            cameraDevice = null
            Log.e("USBCameraManager", "Camera error: $error")
        }
    }
    
    private fun createCaptureSession() {
        val device = cameraDevice ?: return
        
        try {
            // Create ImageReader for capturing frames
            imageReader = ImageReader.newInstance(
                previewSize.width,
                previewSize.height,
                imageFormat,
                2
            )
            
            val surface = imageReader?.surface ?: return
            
            // Create capture session
            device.createCaptureSession(
                listOf(surface),
                captureSessionCallback,
                backgroundHandler
            )
            
        } catch (e: Exception) {
            Log.e("USBCameraManager", "Failed to create capture session", e)
        }
    }
    
    private val captureSessionCallback = object : CameraCaptureSession.StateCallback() {
        override fun onConfigured(session: CameraCaptureSession) {
            captureSession = session
            startPreview()
        }
        
        override fun onConfigureFailed(session: CameraCaptureSession) {
            Log.e("USBCameraManager", "Capture session configuration failed")
        }
    }
    
    private fun startPreview() {
        val session = captureSession ?: return
        val device = cameraDevice ?: return
        
        try {
            val captureRequestBuilder = device.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW)
            val surface = imageReader?.surface ?: return
            
            captureRequestBuilder.addTarget(surface)
            captureRequestBuilder.set(CaptureRequest.CONTROL_AF_MODE, CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
            captureRequestBuilder.set(CaptureRequest.CONTROL_AE_MODE, CaptureRequest.CONTROL_AE_MODE_ON)
            
            session.setRepeatingRequest(
                captureRequestBuilder.build(),
                null,
                backgroundHandler
            )
            
            Log.d("USBCameraManager", "Preview started")
            
        } catch (e: Exception) {
            Log.e("USBCameraManager", "Failed to start preview", e)
        }
    }
    
    suspend fun captureFrame(): Bitmap? = suspendCancellableCoroutine { continuation ->
        val reader = imageReader ?: run {
            continuation.resume(null)
            return@suspendCancellableCoroutine
        }
        
        val imageListener = ImageReader.OnImageAvailableListener { reader ->
            try {
                val image = reader.acquireLatestImage()
                if (image != null) {
                    val bitmap = convertImageToBitmap(image)
                    image.close()
                    continuation.resume(bitmap)
                } else {
                    continuation.resume(null)
                }
            } catch (e: Exception) {
                Log.e("USBCameraManager", "Error processing image", e)
                continuation.resumeWithException(e)
            }
        }
        
        reader.setOnImageAvailableListener(imageListener, backgroundHandler)
        
        continuation.invokeOnCancellation {
            reader.setOnImageAvailableListener(null, null)
        }
    }
    
    private fun convertImageToBitmap(image: android.media.Image): Bitmap {
        val planes = image.planes
        val yBuffer = planes[0].buffer
        val uBuffer = planes[1].buffer
        val vBuffer = planes[2].buffer
        
        val ySize = yBuffer.remaining()
        val uSize = uBuffer.remaining()
        val vSize = vBuffer.remaining()
        
        val nv21 = ByteArray(ySize + uSize + vSize)
        
        yBuffer.get(nv21, 0, ySize)
        vBuffer.get(nv21, ySize, vSize)
        uBuffer.get(nv21, ySize + vSize, uSize)
        
        val yuvImage = android.graphics.YuvImage(
            nv21,
            imageFormat,
            image.width,
            image.height,
            null
        )
        
        val out = java.io.ByteArrayOutputStream()
        yuvImage.compressToJpeg(
            android.graphics.Rect(0, 0, image.width, image.height),
            50,
            out
        )
        
        val imageBytes = out.toByteArray()
        return android.graphics.BitmapFactory.decodeByteArray(imageBytes, 0, imageBytes.size)
    }
    
    fun release() {
        try {
            captureSession?.close()
            cameraDevice?.close()
            imageReader?.close()
        } catch (e: Exception) {
            Log.e("USBCameraManager", "Error releasing camera", e)
        }
    }
}

