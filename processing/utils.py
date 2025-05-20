# processing/utils.py

import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap # Make sure QImage and QPixmap are imported
from PyQt5.QtCore import Qt

def convert_cv_to_qt(cv_image: np.ndarray) -> QPixmap:
    """
    Converts an OpenCV image (NumPy array) to a Qt QPixmap, suitable for display in QLabels or QWidgets.

    Args:
        cv_image: OpenCV image (NumPy array). Can be grayscale or BGR color.

    Returns:
        QPixmap: The converted Qt image object. Returns an empty QPixmap if conversion fails.
    """
    if cv_image is None or cv_image.size == 0:
        print("Error: Input cv_image is empty or None.")
        return QPixmap()

    # Ensure the image data is contiguous in memory, which QImage requires
    cv_image = np.ascontiguousarray(cv_image)

    height, width = cv_image.shape[:2]

    if len(cv_image.shape) == 2: # Grayscale image (H, W)
        # QImage.Format_Grayscale8 requires bytesPerLine = width
        bytes_per_line = width
        q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    elif cv_image.shape[2] == 3: # BGR color image (H, W, 3)
        # OpenCV uses BGR order, QImage.Format_RGB888 expects RGB order. Need to convert color space.
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        # For RGB888, bytesPerLine is 3 * width
        bytes_per_line = 3 * width
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
    elif cv_image.shape[2] == 4: # BGRA image (H, W, 4)
        # OpenCV uses BGRA order, QImage.Format_ARGB32 expects ARGB order.
        # Convert BGRA to RGBA first
        rgba_image = cv2.cvtColor(cv_image, cv2.COLOR_BGRA2RGBA)
        # For ARGB32, bytesPerLine is 4 * width
        bytes_per_line = 4 * width
        q_image = QImage(rgba_image.data, width, height, bytes_per_line, QImage.Format_ARGB32)
    else:
        # Unsupported number of channels
        print(f"Error: Unsupported image format shape {cv_image.shape}. Cannot convert to QImage.")
        return QPixmap() # Return an empty QPixmap

    # Convert QImage to QPixmap for display purposes
    # QPixmap is optimized for showing images on screen widgets
    return QPixmap.fromImage(q_image)

# TODO: Optionally implement convert_qt_to_cv if needed to get data from a QImage back into OpenCV/NumPy.
# (Currently not strictly needed as we operate on Lienzo's NumPy data directly).
# def convert_qt_to_cv(q_image: QImage) -> np.ndarray:
#     """
#     Converts a Qt QImage to an OpenCV image (NumPy array).
#     Needs to handle various QImage formats (Grayscale8, RGB888, ARGB32 etc.)
#     and convert to a format compatible with OpenCV (typically uint8, HxW or HxWx3).
#     """
#     if q_image.isNull():
#         return np.array([], dtype=np.uint8)

#     width = q_image.width()
#     height = q_image.height()
#
#     if q_image.format() == QImage.Format_Grayscale8:
#         # Convert QImage data buffer directly to numpy array
#         ptr = q_image.bits()
#         ptr.setsize(height * width * q_image.bytesPerLine()) # bytesPerLine is just width for gray8
#         # Create numpy array sharing the buffer. Be careful with memory management if original QImage can be deleted.
#         # For typical use where QImage is temporary, .copy() afterwards is safer.
#         return np.array(ptr, dtype=np.uint8).reshape((height, width))
#
#     elif q_image.format() == QImage.Format_RGB888:
#         # Convert QImage data buffer to numpy array (RGB order)
#         ptr = q_image.bits()
#         ptr.setsize(height * width * 3) # 3 bytes per pixel for RGB888
#         # Reshape to (height, width, 3) and convert from RGB to BGR for OpenCV
#         return cv2.cvtColor(np.array(ptr, dtype=np.uint8).reshape((height, width, 3)), cv2.COLOR_RGB2BGR)
#
#     elif q_image.format() == QImage.Format_ARGB32:
#          # Convert QImage data buffer to numpy array (ARGB order)
#          ptr = q_image.bits()
#          ptr.setsize(height * width * 4) # 4 bytes per pixel for ARGB32
#          # Reshape to (height, width, 4) and convert from ARGB to BGRA for OpenCV
#          # Note: ARGB in QImage byte order might be tricky (little/big endian).
#          # Format_ARGB32 is typically 0xAARRGGBB, which on little-endian is BB GG RR AA in memory.
#          # OpenCV BGRA is BB GG RR AA. So direct conversion might work?
#          # Need to test byte order carefully or use cvtColor which handles it.
#          # ARGB -> RGBA -> BGRA (or ARGB -> BGRA directly if OpenCV supports)
#          # cv2.cvtColor(src, cv2.COLOR_RGBA2BGRA) expects RGBA input.
#          # Let's assume Format_ARGB32 bits are RGBA in memory (simplification, check Qt docs for real endianness)
#          rgba_array = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))
#          return cv2.cvtColor(rgba_array, cv2.COLOR_RGBA2BGRA)
#
#     else:
#         print(f"Warning: Unsupported QImage format for conversion to cv image: {q_image.format()}.")
#         return np.array([], dtype=np.uint8) # Return empty array for unsupported formats