#!/usr/bin/env python3
"""
Setup script for Enhanced Smart Goggle System
"""

import subprocess
import sys
import os
import time

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        sys.exit(1)

def download_yolo_models():
    """Download recommended YOLO models for different use cases"""
    print("🔍 Checking YOLO models...")
    
    models = {
        'yolov8n.pt': 'Nano - Fast, lightweight (Raspberry Pi)',
        'yolov8s.pt': 'Small - Balanced speed/accuracy (Laptop CPU)',
        'yolov8m.pt': 'Medium - High accuracy (Laptop GPU)',
        'yolov8l.pt': 'Large - Best accuracy (Desktop GPU)'
    }
    
    for model_name, description in models.items():
        if not os.path.exists(model_name):
            print(f"📥 Downloading {model_name} ({description})...")
            try:
                from ultralytics import YOLO
                model = YOLO(model_name)
                print(f"✅ {model_name} downloaded successfully")
            except Exception as e:
                print(f"❌ Failed to download {model_name}: {e}")
                print("💡 Please check your internet connection")
        else:
            print(f"✅ {model_name} already exists")
    
    # Set default model based on hardware
    if not os.path.exists("yolov8s.pt"):
        print("📝 Creating default model link...")
        try:
            import shutil
            if os.path.exists("yolov8n.pt"):
                shutil.copy("yolov8n.pt", "yolov8s.pt")
                print("✅ Default model set to YOLOv8n")
        except Exception as e:
            print(f"⚠️ Could not set default model: {e}")

def create_directory_structure():
    """Create necessary directory structure"""
    print("📁 Creating directory structure...")
    os.makedirs("src", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    print("✅ Directory structure created")

def test_system():
    """Test the enhanced system components"""
    print("🧪 Testing system components...")
    
    try:
        # Test camera
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("✅ Camera: Working")
            cap.release()
        else:
            print("❌ Camera: Not working - check connection")
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
    
    try:
        # Test TTS
        import pyttsx3
        engine = pyttsx3.init()
        print("✅ Text-to-Speech: Working")
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
    
    try:
        # Test YOLO
        from ultralytics import YOLO
        model = YOLO('yolov8n.pt')
        print("✅ YOLO model: Working")
    except Exception as e:
        print(f"❌ YOLO test failed: {e}")

def main():
    print("🎯" + "="*60)
    print("      ENHANCED SMART GOGGLE SYSTEM - SETUP")
    print("      Comprehensive Obstacle Detection & Audio Guidance")
    print("🎯" + "="*60)
    
    create_directory_structure()
    install_requirements()
    download_yolo_models()
    test_system()
    
    print("\n🎉 Enhanced setup completed successfully!")
    print("\n🚀 To start the system: python main.py")
    print("📖 Features enabled:")
    print("   🧱 Wall detection using edge detection")
    print("   🎯 Comprehensive obstacle analysis")
    print("   🔊 Intelligent audio guidance with danger levels")
    print("   📍 Directional instructions (left/right/straight)")
    print("   ⚠️ Critical obstacle warnings")
    print("\n🔊 Test the audio output with: python main.py and press 'a'")
    print("📋 Check MODEL_RECOMMENDATIONS.md for model selection guide")

if __name__ == "__main__":
    main()