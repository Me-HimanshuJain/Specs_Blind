# Smart Goggle System Package
__version__ = "1.0.0"
__author__ = "Smart Goggle Team"

from .camera import Camera
from .detector import ObjectDetector
from .tracker import ObjectTracker
from .audio_feedback import AudioFeedback
from .utils import draw_tracking_info, calculate_distance

__all__ = [
    'Camera',
    'ObjectDetector', 
    'ObjectTracker',
    'AudioFeedback',
    'draw_tracking_info',
    'calculate_distance'
]