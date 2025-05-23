# processing/utils.py

import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt

def convert_cv_to_qt(cv_image: np.ndarray) -> QPixmap:
    """Converts an OpenCV image (NumPy array) to a Qt QPixmap."""
    if cv_image is None or cv_image.size == 0:
        print("Error: Input cv_image is empty or None.")
        return QPixmap()

    cv_image = np.ascontiguousarray(cv_image)

    height, width = cv_image.shape[:2]

    if width <= 0 or height <= 0:
        print(f"Error: Invalid image dimensions {width}x{height}.")
        return QPixmap()

    q_image = None
    if len(cv_image.shape) == 2: # Grayscale image (H, W)
        if cv_image.dtype != np.uint8:
             print(f"Warning: Grayscale image dtype is {cv_image.dtype}, attempting conversion to uint8.")
             cv_image = cv_image.astype(np.uint8)
        bytes_per_line = width
        if not cv_image.data:
             print("Error: cv_image data buffer is invalid.")
             return QPixmap()
        q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)

    elif cv_image.shape[2] == 3: # BGR color image (H, W, 3)
        if cv_image.dtype != np.uint8:
             print(f"Warning: BGR image dtype is {cv_image.dtype}, attempting conversion to uint8.")
             cv_image = cv_image.astype(np.uint8)
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * width
        if not rgb_image.data:
             print("Error: rgb_image data buffer is invalid.")
             return QPixmap()
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)

    elif cv_image.shape[2] == 4: # BGRA image (H, W, 4)
        if cv_image.dtype != np.uint8:
             print(f"Warning: BGRA image dtype is {cv_image.dtype}, attempting conversion to uint8.")
             cv_image = cv_image.astype(np.uint8)
        bytes_per_line_bgra = 4 * width
        if not cv_image.data:
             print("Error: cv_image data buffer is invalid for BGRA.")
             return QPixmap()
        q_image = QImage(cv_image.data, width, height, bytes_per_line_bgra, QImage.Format_ARGB32)

    else:
        print(f"Error: Unsupported image format shape {cv_image.shape}. Cannot convert to QImage.")
        return QPixmap()

    if q_image is None or q_image.isNull():
         print("Error: QImage creation failed.")
         return QPixmap()

    return QPixmap.fromImage(q_image)