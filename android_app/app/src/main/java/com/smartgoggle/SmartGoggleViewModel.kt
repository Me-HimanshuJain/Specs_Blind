package com.smartgoggle

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class SmartGoggleViewModel : ViewModel() {
    
    private val _isProcessing = MutableStateFlow(false)
    val isProcessing: StateFlow<Boolean> = _isProcessing.asStateFlow()
    
    private val _status = MutableStateFlow("System ready")
    val status: StateFlow<String> = _status.asStateFlow()
    
    private val _fps = MutableStateFlow(0)
    val fps: StateFlow<Int> = _fps.asStateFlow()
    
    private val _objectCount = MutableStateFlow(0)
    val objectCount: StateFlow<Int> = _objectCount.asStateFlow()
    
    fun updateProcessingState(processing: Boolean) {
        viewModelScope.launch {
            _isProcessing.value = processing
        }
    }
    
    fun updateStatus(message: String) {
        viewModelScope.launch {
            _status.value = message
        }
    }
    
    fun updateFps(fps: Int) {
        viewModelScope.launch {
            _fps.value = fps
        }
    }
    
    fun updateObjectCount(count: Int) {
        viewModelScope.launch {
            _objectCount.value = count
        }
    }
}

