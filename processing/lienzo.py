# processing/lienzo.py

import numpy as np
import cv2 # Import cv2 to easily create default image if needed and potentially for color conversion checks

class Lienzo:
    """
    Manages the underlying image data for the canvas using a NumPy array.
    Assumes grayscale uint8 data for simplicity in brush engine.
    """
    def __init__(self, width: int, height: int, color: int = 255):
        """
        Initializes the canvas with a solid background color.

        Args:
            width: Canvas width in pixels.
            height: Canvas height in pixels.
            color: Background color (grayscale 0-255). Defaults to white (255).
        """
        if width <= 0 or height <= 0:
             print(f"Warning: Initializing Lienzo with invalid size: {width}x{height}. Using default 1x1.")
             width, height = 1, 1
             color = 255 # Ensure valid color for minimal array

        self._width = width
        self._height = height
        # Use grayscale (single channel) uint8 array for canvas data. Shape is (height, width).
        self._canvas_data = np.full((height, width), color, dtype=np.uint8)
        print(f"Canvas initialized with size {width}x{height} and color {color}")

    def get_canvas_data(self) -> np.ndarray:
        """
        Returns the current canvas NumPy array data.
        """
        return self._canvas_data

    def set_canvas_data(self, data: np.ndarray):
        """
        Replaces the current canvas data with a new NumPy array.
        Automatically converts to grayscale if input is color.
        Resizes input data if dimensions don't match the current lienzo size.

        Args:
            data: The new NumPy array data for the canvas. Expected shape (H, W) uint8 or (H, W, C) uint8 convertable to gray.
        """
        if data is None or data.size == 0:
             print("Warning: Attempted to set canvas data with empty or None data.")
             return

        target_height, target_width = self._height, self._width

        # Convert data to grayscale if it's color
        if len(data.shape) == 3:
             if data.shape[2] == 3:
                 data = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
             elif data.shape[2] == 4: # Handle alpha channel
                  # Drop alpha channel when converting to gray
                  data = cv2.cvtColor(data, cv2.COLOR_BGRA2GRAY)
             else:
                  print(f"Warning: Unsupported channel count for input data: {data.shape[2]}. Cannot set canvas data.")
                  return # Cannot process data with unknown channels
        elif len(data.shape) != 2: # Not grayscale and not 3 or 4 channels
             print(f"Warning: Unsupported input data shape for setting canvas: {data.shape}. Cannot set canvas data.")
             return

        # Resize data if its dimensions do not match the current lienzo size
        if data.shape[:2] != (target_height, target_width):
             print(f"Warning: Input data size {data.shape[1]}x{data.shape[0]} mismatches lienzo size {target_width}x{target_height}. Resizing input data.")
             # Use INTER_AREA for shrinking, INTER_LINEAR for zooming
             interpolation_method = cv2.INTER_AREA if data.shape[1] > target_width else cv2.INTER_LINEAR
             data = cv2.resize(data, (target_width, target_height), interpolation=interpolation_method)
             # Ensure data is uint8 after resize
             if data.dtype != np.uint8:
                  data = data.astype(np.uint8)

        # Finally, set the canvas data
        self._canvas_data = data
        # print("Canvas data updated.")

    def get_size(self) -> tuple[int, int]:
        """
        Returns the canvas dimensions.

        Returns:
            tuple[int, int]: (width, height).
        """
        return self._width, self._height

    # Optional: Method to resize the lienzo instance, potentially losing content unless handled carefully
    # def resize(self, new_width: int, new_height: int):
    #     if new_width <= 0 or new_height <= 0:
    #         print("Warning: Attempted to resize Lienzo to invalid size.")
    #         return
    #     if new_width == self._width and new_height == self._height:
    #         return # Already the requested size
    #
    #     # Simple resize: just create a new blank canvas
    #     self._width = new_width
    #     self._height = new_height
    #     self._canvas_data = np.full((new_height, new_width), 255, dtype=np.uint8) # Fill with white
    #     print(f"Canvas resized to {new_width}x{new_height}. Content reset.")

    # NOTE: crop_area and paste_area are used directly by brush_engine and potentially image_processing
    def crop_area(self, rect: tuple[int, int, int, int]) -> np.ndarray:
        """
        Crops a specified rectangular region from the canvas.

        Args:
            rect: Tuple (x, y, width, height) defining the region in canvas coordinates.

        Returns:
            np.ndarray: A copy of the cropped region's NumPy array. Returns empty array if region is invalid.
        """
        x, y, w, h = rect
        # Clip coordinates to be within canvas bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self._width, x + w)
        y2 = min(self._height, y + h)

        # Check if the resulting region is valid
        if x2 <= x1 or y2 <= y1:
            return np.empty((0,0), dtype=np.uint8) # Return empty array for invalid region

        # NumPy array indexing is [row_start:row_end, col_start:col_end] -> [y1:y2, x1:x2]
        return self._canvas_data[y1:y2, x1:x2].copy() # .copy() is crucial to avoid modifying lienzo data directly

    def paste_area(self, rect: tuple[int, int, int, int], data: np.ndarray):
        """
        Pastes the provided NumPy array data onto a specified rectangular region of the canvas.

        Args:
            rect: Tuple (x, y, width, height) defining the target region in canvas coordinates.
            data: The NumPy array data to paste. Its dimensions (height, width) must match
                  the effective target region dimensions defined by rect clipped to canvas bounds.
                  Expected dtype np.uint8.
        """
        if data is None or data.size == 0:
             # print("Warning: Attempted to paste empty or None data.")
             return

        x, y, w, h = rect
        # Clip target coordinates to canvas bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self._width, x + w)
        y2 = min(self._height, y + h)

        target_h = y2 - y1
        target_w = x2 - x1

        # Check if the target region is valid AND the data dimensions match the target region dimensions
        # Corrected 'Or' to 'or'
        if target_h <= 0 or target_w <= 0 or data.shape[:2] != (target_h, target_w):
             # print(f"Warning: Paste area mismatch or invalid. Target: ({target_w}x{target_h}), Data: {data.shape[:2]}")
             return # Invalid target region or data shape mismatch

        # Check if data dtype is uint8 (required for consistency)
        if data.dtype != np.uint8:
             print(f"Warning: Pasting data with non-uint8 dtype ({data.dtype}). Attempting conversion.")
             # Attempt conversion, clipping values if necessary
             data = np.clip(data, 0, 255).astype(np.uint8)

        # Paste the data into the calculated area of the main canvas data
        self._canvas_data[y1:y2, x1:x2] = data
        # print(f"Pasted data at ({x1},{y1}) with size ({target_w}x{target_h}).")

    def fill(self, color: int = 255):
        """
        Fills the entire canvas with the specified color.

        Args:
            color: Fill color (grayscale 0-255). Defaults to white (255).
        """
        if self._canvas_data is not None:
             self._canvas_data.fill(color)
             # print(f"Canvas filled with color {color}.")
        else:
             print("Warning: Cannot fill canvas, lienzo data is None.")