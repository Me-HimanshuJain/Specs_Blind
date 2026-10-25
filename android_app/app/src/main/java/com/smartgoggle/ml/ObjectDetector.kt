package com.smartgoggle.ml

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import kotlin.math.max
import kotlin.math.min

class ObjectDetector(private val context: Context) {
    
    private var interpreter: Interpreter? = null
    private val inputSize = 640
    private val outputSize = 25200 // YOLOv8 output size
    private val numClasses = 80
    
    // COCO class names
    private val classNames = arrayOf(
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush"
    )
    
    // Important objects for navigation
    private val importantObjects = setOf(
        "person", "chair", "dining table", "bed", "couch", "car", "bicycle",
        "motorcycle", "bus", "truck", "bottle", "cup", "backpack", "handbag"
    )
    
    fun initializeModel() {
        try {
            val modelFile = loadModelFile("yolov8n.tflite")
            val options = Interpreter.Options().apply {
                setNumThreads(4)
                setUseNNAPI(true)
            }
            interpreter = Interpreter(modelFile, options)
            Log.d("ObjectDetector", "Model loaded successfully")
        } catch (e: Exception) {
            Log.e("ObjectDetector", "Failed to load model", e)
            throw e
        }
    }
    
    private fun loadModelFile(filename: String): MappedByteBuffer {
        val assetFileDescriptor = context.assets.openFd(filename)
        val inputStream = FileInputStream(assetFileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        val startOffset = assetFileDescriptor.startOffset
        val declaredLength = assetFileDescriptor.declaredLength
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }
    
    fun detectObjects(bitmap: Bitmap): List<Detection> {
        val interpreter = this.interpreter ?: return emptyList()
        
        try {
            // Preprocess image
            val inputBuffer = preprocessImage(bitmap)
            
            // Run inference
            val outputBuffer = Array(1) { Array(outputSize) { FloatArray(85) } }
            interpreter.run(inputBuffer, outputBuffer)
            
            // Postprocess results
            return postprocessOutput(outputBuffer[0], bitmap.width, bitmap.height)
            
        } catch (e: Exception) {
            Log.e("ObjectDetector", "Detection error", e)
            return emptyList()
        }
    }
    
    private fun preprocessImage(bitmap: Bitmap): ByteBuffer {
        val resizedBitmap = Bitmap.createScaledBitmap(bitmap, inputSize, inputSize, true)
        val byteBuffer = ByteBuffer.allocateDirect(4 * inputSize * inputSize * 3)
        byteBuffer.order(ByteOrder.nativeOrder())
        
        val intValues = IntArray(inputSize * inputSize)
        resizedBitmap.getPixels(intValues, 0, inputSize, 0, 0, inputSize, inputSize)
        
        for (pixel in intValues) {
            // Normalize to [0, 1] and convert to RGB
            byteBuffer.putFloat(((pixel shr 16) and 0xFF) / 255.0f) // R
            byteBuffer.putFloat(((pixel shr 8) and 0xFF) / 255.0f)  // G
            byteBuffer.putFloat((pixel and 0xFF) / 255.0f)          // B
        }
        
        return byteBuffer
    }
    
    private fun postprocessOutput(
        output: Array<FloatArray>,
        imageWidth: Int,
        imageHeight: Int
    ): List<Detection> {
        val detections = mutableListOf<Detection>()
        val confidenceThreshold = 0.3f
        val nmsThreshold = 0.45f
        
        for (i in output.indices) {
            val confidence = output[i][4]
            
            if (confidence > confidenceThreshold) {
                // Find class with highest probability
                var maxClassScore = 0f
                var classId = 0
                
                for (j in 5 until 85) {
                    if (output[i][j] > maxClassScore) {
                        maxClassScore = output[i][j]
                        classId = j - 5
                    }
                }
                
                val finalConfidence = confidence * maxClassScore
                
                if (finalConfidence > confidenceThreshold && classId < classNames.size) {
                    val className = classNames[classId]
                    
                    // Only process important objects
                    if (className in importantObjects) {
                        val bbox = extractBoundingBox(output[i], imageWidth, imageHeight)
                        detections.add(
                            Detection(
                                bbox = bbox,
                                confidence = finalConfidence,
                                classId = classId,
                                className = className
                            )
                        )
                    }
                }
            }
        }
        
        // Apply Non-Maximum Suppression
        return applyNMS(detections, nmsThreshold)
    }
    
    private fun extractBoundingBox(
        output: FloatArray,
        imageWidth: Int,
        imageHeight: Int
    ): FloatArray {
        val centerX = output[0]
        val centerY = output[1]
        val width = output[2]
        val height = output[3]
        
        val x1 = (centerX - width / 2) * imageWidth / inputSize
        val y1 = (centerY - height / 2) * imageHeight / inputSize
        val x2 = (centerX + width / 2) * imageWidth / inputSize
        val y2 = (centerY + height / 2) * imageHeight / inputSize
        
        return floatArrayOf(
            max(0f, x1),
            max(0f, y1),
            min(imageWidth.toFloat(), x2),
            min(imageHeight.toFloat(), y2)
        )
    }
    
    private fun applyNMS(detections: List<Detection>, threshold: Float): List<Detection> {
        val sortedDetections = detections.sortedByDescending { it.confidence }
        val selected = mutableListOf<Detection>()
        
        for (detection in sortedDetections) {
            var shouldAdd = true
            
            for (selectedDetection in selected) {
                if (calculateIoU(detection.bbox, selectedDetection.bbox) > threshold) {
                    shouldAdd = false
                    break
                }
            }
            
            if (shouldAdd) {
                selected.add(detection)
            }
        }
        
        return selected
    }
    
    private fun calculateIoU(bbox1: FloatArray, bbox2: FloatArray): Float {
        val x1 = max(bbox1[0], bbox2[0])
        val y1 = max(bbox1[1], bbox2[1])
        val x2 = min(bbox1[2], bbox2[2])
        val y2 = min(bbox1[3], bbox2[3])
        
        if (x2 <= x1 || y2 <= y1) return 0f
        
        val intersection = (x2 - x1) * (y2 - y1)
        val area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        val area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        val union = area1 + area2 - intersection
        
        return if (union > 0) intersection / union else 0f
    }
    
    fun release() {
        interpreter?.close()
        interpreter = null
    }
}

data class Detection(
    val bbox: FloatArray,
    val confidence: Float,
    val classId: Int,
    val className: String
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as Detection

        if (!bbox.contentEquals(other.bbox)) return false
        if (confidence != other.confidence) return false
        if (classId != other.classId) return false
        if (className != other.className) return false

        return true
    }

    override fun hashCode(): Int {
        var result = bbox.contentHashCode()
        result = 31 * result + confidence.hashCode()
        result = 31 * result + classId
        result = 31 * result + className.hashCode()
        return result
    }
}

