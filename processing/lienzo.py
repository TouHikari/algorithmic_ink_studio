# processing/lienzo.py

import numpy as np
import cv2

class Lienzo:
    """Manages the underlying image data for the canvas using a NumPy array (BGR uint8)."""
    def __init__(self, width: int, height: int, color: tuple[int, int, int] = (255, 255, 255)):
        """Initializes the canvas with a solid background color (BGR)."""
        if width <= 0 or height <= 0:
             print(f"Warning: Initializing Lienzo with invalid size: {width}x{height}. Using default 1x1.")
             width, height = 1, 1

        if not isinstance(color, (tuple, list)) or len(color) != 3:
             print(f"Warning: Invalid initial color format {color}. Using white (255,255,255).")
             color = (255, 255, 255)
        color = (np.clip(color[0], 0, 255), np.clip(color[1], 0, 255), np.clip(color[2], 0, 255))

        self._width = width
        self._height = height
        self._canvas_data = np.full((height, width, 3), color, dtype=np.uint8)
        print(f"Canvas initialized with size {width}x{height} and color {color}")

    def get_canvas_data(self) -> np.ndarray:
        """Returns a copy of the current canvas NumPy array data (BGR uint8)."""
        if self._canvas_data is not None:
            return self._canvas_data.copy()
        return np.empty((0, 0, 3), dtype=np.uint8)

    def set_canvas_data(self, data: np.ndarray):
        """Replaces canvas data, converts to BGR, resizes if dimensions mismatch."""
        if data is None or data.size == 0:
             print("Warning: Attempted to set empty or None data.")
             return

        target_height, target_width = self._height, self._width
        # Check input shape before accessing data.shape[:2]
        if len(data.shape) not in [2, 3]:
             print(f"Warning: Unsupported input data shape for setting canvas: {data.shape}. Cannot set canvas data.")
             return
        input_height, input_width = data.shape[:2]

        # --- FIX: More robust color conversion to BGR ---
        if len(data.shape) == 2: # Grayscale
             if data.dtype != np.uint8: data = data.astype(np.uint8)
             data = cv2.cvtColor(data, cv2.COLOR_GRAY2BGR)
        elif data.shape[2] == 1: # Grayscale HxWx1
             if data.dtype != np.uint8: data = data.astype(np.uint8)
             data = cv2.cvtColor(data, cv2.COLOR_GRAY2BGR)
        elif data.shape[2] == 3: # Assuming BGR or RGB. Convert RGB to BGR just in case.
             if data.dtype != np.uint8: data = data.astype(np.uint8)
             # Simple check for potential RGB by looking at extreme corner pixel values? Unreliable.
             # Assume the read library (cv2) gives BGR for 3 channels. No conversion needed if it's BGR.
             # If you want to be safer and assume potential RGB:
             # data = cv2.cvtColor(data, cv2.COLOR_RGB2BGR) # Only if you know source is RGB
             pass # If already HxWx3, assume BGR by default from cv2.imread
        elif data.shape[2] == 4: # BGRA or RGBA - convert to BGR, dropping alpha
             if data.dtype != np.uint8: data = data.astype(np.uint8)
             data = cv2.cvtColor(data, cv2.COLOR_BGRA2BGR) # Assumes BGRA from cv2 read
        else:
             print(f"Warning: Unsupported channel count: {data.shape[2]}. Cannot set canvas data.")
             return

        # Check if data is now 3 channels after conversion attempt
        if len(data.shape) != 3 or data.shape[2] != 3:
             print(f"FATAL ERROR: Data shape after color conversion is not HxWx3: {data.shape}. Cannot set data.")
             return

        # Check dtype after potential conversion / ensure it's uint8
        if data.dtype != np.uint8:
             print(f"Warning: Data dtype {data.dtype} after color conversion is not uint8. Attempting cast.")
             data = np.clip(data, 0, 255).astype(np.uint8)

        # Resize data if its dimensions do not match the current lienzo size
        if data.shape[:2] != (target_height, target_width):
             print(f"Warning: Input data size {input_width}x{input_height} mismatches lienzo size {target_width}x{target_height}. Resizing.")
             if target_width <= 0 or target_height <= 0 or input_width <= 0 or input_height <= 0:
                  print("Error: Cannot resize due to invalid dimensions.")
                  return

             interpolation_method = cv2.INTER_AREA if input_width > target_width else cv2.INTER_LINEAR
             try:
                 data = cv2.resize(data, (target_width, target_height), interpolation=interpolation_method)
                 # Resize operation should preserve channels and dtype if input was uint8 HxWx3
                 if data.shape != (target_height, target_width, 3) or data.dtype != np.uint8:
                      print(f"Warning: Resize resulted in unexpected shape/dtype: {data.shape}, {data.dtype}.")
                      # Try to re-cast to uint8 BGR if shape is correct HxWx3
                      if len(data.shape) == 3 and data.shape[2] == 3:
                           data = np.clip(data, 0, 255).astype(np.uint8)
                      else:
                           print("FATAL ERROR: Resize resulted in invalid data format. Cannot set data.")
                           return

             except Exception as e:
                  print(f"Error resizing input image data: {e}. Cannot set canvas data.")
                  return

        # At this point, 'data' should be HxWx3 uint8 and match target size.
        if data.shape == (target_height, target_width, 3) and data.dtype == np.uint8:
             self._canvas_data = np.ascontiguousarray(data)
        else:
             print(f"FATAL ERROR: Data format mismatch after all processing: {data.shape}, {data.dtype}. Expected ({target_height}, {target_width}, 3), uint8. Cannot set data.")

    def get_size(self) -> tuple[int, int]:
        """Returns the canvas dimensions (width, height)."""
        return self._width, self._height

    def crop_area(self, rect: tuple[int, int, int, int]) -> np.ndarray:
        """Crops a rectangular region from the canvas, returns a copy (BGR uint8)."""
        x, y, w, h = rect
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self._width, x + w)
        y2 = min(self._height, y + h)

        if x2 <= x1 or y2 <= y1:
            return np.empty((0, 0, 3), dtype=np.uint8)

        if self._canvas_data is not None and len(self._canvas_data.shape) == 3 and self._canvas_data.shape[2] == 3:
            # Ensure canvas_data is HxWx3 before slicing
            return self._canvas_data[y1:y2, x1:x2].copy()
        else:
             print("Warning: Cannot crop area, canvas data is None or invalid shape.")
             return np.empty((0, 0, 3), dtype=np.uint8)

    def paste_area(self, rect: tuple[int, int, int, int], data: np.ndarray):
        """Pastes data onto a rectangular region of the canvas. Expects BGR uint8 data."""
        if data is None or data.size == 0:
             return
        if self._canvas_data is None or len(self._canvas_data.shape) != 3 or self._canvas_data.shape[2] != 3:
             print("Warning: Cannot paste area, canvas data is None or invalid shape.")
             return

        x, y, w, h = rect
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self._width, x + w)
        y2 = min(self._height, y + h)

        target_h = y2 - y1
        target_w = x2 - x1

        if target_h <= 0 or target_w <= 0 or data.shape != (target_h, target_w, 3):
             print(f"Warning: Paste data shape {data.shape} mismatch with target region size ({target_w}x{target_h}x3). Skipping paste.")
             return

        if data.dtype != np.uint8:
             print(f"Warning: Pasting data with non-uint8 dtype ({data.dtype}). Attempting conversion.")
             try:
                data = np.clip(data, 0, 255).astype(np.uint8)
             except Exception as e:
                print(f"Error converting paste data dtype: {e}. Skipping paste.")
                return

        # Ensure data is contiguous before assigning
        self._canvas_data[y1:y2, x1:x2] = np.ascontiguousarray(data)

    def fill(self, color: tuple[int, int, int] = (255, 255, 255)):
        """Fills the entire canvas with the specified color (BGR tuple)."""
        if self._canvas_data is not None and len(self._canvas_data.shape) == 3 and self._canvas_data.shape[2] == 3:
             if not isinstance(color, (tuple, list)) or len(color) != 3:
                  print(f"Warning: Invalid fill color format {color}. Using white (255,255,255).")
                  color = (255, 255, 255)
             clipped_color = (np.clip(color[0], 0, 255), np.clip(color[1], 0, 255), np.clip(color[2], 0, 255))

             self._canvas_data[:, :] = clipped_color
        else:
             print("Warning: Cannot fill canvas, lienzo data is None or invalid shape.")