# processing/lienzo.py

import numpy as np
import cv2

class Lienzo:
    """Manages the underlying image data for the canvas using a NumPy array (grayscale uint8)."""
    def __init__(self, width: int, height: int, color: int = 255):
        """Initializes the canvas with a solid background color."""
        if width <= 0 or height <= 0:
             print(f"Warning: Initializing Lienzo with invalid size: {width}x{height}. Using default 1x1.")
             width, height = 1, 1
             color = 255

        self._width = width
        self._height = height
        self._canvas_data = np.full((height, width), color, dtype=np.uint8)
        print(f"Canvas initialized with size {width}x{height} and color {color}")

    def get_canvas_data(self) -> np.ndarray:
        """Returns a copy of the current canvas NumPy array data."""
        if self._canvas_data is not None:
            return self._canvas_data.copy()
        return np.array([], dtype=np.uint8)

    def set_canvas_data(self, data: np.ndarray):
        """Replaces canvas data, converts to grayscale, resizes if dimensions mismatch."""
        if data is None or data.size == 0:
             print("Warning: Attempted to set empty or None data.")
             return

        target_height, target_width = self._height, self._width
        input_height, input_width = data.shape[:2]

        if len(data.shape) == 3:
             if data.shape[2] == 3:
                 data = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
             elif data.shape[2] == 4:
                  data = cv2.cvtColor(data, cv2.COLOR_BGRA2GRAY)
             else:
                  print(f"Warning: Unsupported channel count: {data.shape[2]}. Cannot set canvas data.")
                  return
        elif len(data.shape) != 2:
             print(f"Warning: Unsupported input data shape: {data.shape}. Cannot set canvas data.")
             return

        if (input_height, input_width) != (target_height, target_width):
             print(f"Warning: Input data size {input_width}x{input_height} mismatches lienzo size {target_width}x{target_height}. Resizing.")
             if target_width <= 0 or target_height <= 0 or input_width <= 0 or input_height <= 0:
                  print("Error: Cannot resize due to invalid dimensions.")
                  return

             interpolation_method = cv2.INTER_AREA if input_width > target_width else cv2.INTER_LINEAR
             try:
                 data = cv2.resize(data, (target_width, target_height), interpolation=interpolation_method)
             except Exception as e:
                  print(f"Error resizing input image data: {e}. Cannot set canvas data.")
                  return

        if data.dtype != np.uint8:
              data = data.astype(np.uint8)

        self._canvas_data = np.ascontiguousarray(data)

    def get_size(self) -> tuple[int, int]:
        """Returns the canvas dimensions (width, height)."""
        return self._width, self._height

    def crop_area(self, rect: tuple[int, int, int, int]) -> np.ndarray:
        """Crops a rectangular region from the canvas, returns a copy."""
        x, y, w, h = rect
        # These are exclusive upper bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self._width, x + w)
        y2 = min(self._height, y + h)

        if x2 <= x1 or y2 <= y1:
            return np.empty((0,0), dtype=np.uint8)

        if self._canvas_data is not None:
            # Numpy slice [y1:y2, x1:x2] gives shape (y2-y1, x2-x1)
            return self._canvas_data[y1:y2, x1:x2].copy()
        else:
             print("Warning: Cannot crop area, canvas_data is None.")
             return np.empty((0,0), dtype=np.uint8)

    def paste_area(self, rect: tuple[int, int, int, int], data: np.ndarray):
        """Pastes data onto a rectangular region of the canvas."""
        if data is None or data.size == 0:
             return
        if self._canvas_data is None:
             print("Warning: Cannot paste area, canvas_data is None.")
             return

        x, y, w, h = rect
        # These are exclusive upper bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self._width, x + w)
        y2 = min(self._height, y + h)

        target_h = y2 - y1
        target_w = x2 - x1

        # --- FIX: Corrected shape comparison ---
        # Expected shape is (height, width), i.e., (target_h, target_w)
        if target_h <= 0 or target_w <= 0 or data.shape[:2] != (target_h, target_w):
             print(f"Warning: Paste data shape {data.shape[:2]} mismatch with target region size ({target_w}x{target_h}). Skipping paste.")
             return

        if data.dtype != np.uint8:
             print(f"Warning: Pasting data with non-uint8 dtype ({data.dtype}). Attempting conversion.")
             try:
                data = np.clip(data, 0, 255).astype(np.uint8)
             except Exception as e:
                print(f"Error converting paste data dtype: {e}. Skipping paste.")
                return

        self._canvas_data[y1:y2, x1:x2] = np.ascontiguousarray(data)

    def fill(self, color: int = 255):
        """Fills the entire canvas with the specified color (grayscale 0-255)."""
        if self._canvas_data is not None:
             clipped_color = np.clip(color, 0, 255).astype(np.uint8)
             self._canvas_data.fill(clipped_color)
        else:
             print("Warning: Cannot fill canvas, lienzo data is None.")