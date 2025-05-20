# processing/brush_engine.py (Basic Brush with Delayed Local Blur)

import numpy as np
import cv2
from PyQt5.QtCore import QPoint, QRect # Used for geometry, convenient even in processing layer
import math
import random
import os
# import time # Optional: for seeding realism

# Import Lienzo class
from processing.lienzo import Lienzo

# --- Global brush shapes dictionary ---
# Loaded brush shapes (opacity, float [0, 1]). 1.0 is opaque, 0.0 is transparent.
_brush_shapes = {}
# Determine the path to the resources folder relative to this script
_brush_shape_folder = os.path.join(os.path.dirname(__file__), '..', 'resources')

def load_brush_shapes():
    """Loads brush shape images from the resources folder into the global dictionary."""
    global _brush_shapes # Declare as global to modify the module-level variable
    global _brush_shape_folder # Declare as global

    shape_files = {
        'round': 'brush_round.png',
        # Add more shapes here by adding entries like 'flat': 'brush_flat.png',
        # Make sure the actual PNG files exist in the resources folder.
    }
    # print(f"Looking for brush shapes in: {_brush_shape_folder}") # Debug path

    # Check if resources folder exists
    if not os.path.exists(_brush_shape_folder):
         print(f"Warning: Resources folder not found at {_brush_shape_folder}. Cannot load brush shapes.")
         _brush_shapes['round'] = None # Ensure 'round' entry exists even if associated with None, so fallback can be triggered
    else:
        for name, filename in shape_files.items():
            filepath = os.path.join(_brush_shape_folder, filename)
            # print(f"Attempting to load: {filepath}") # Debug loading attempts
            if os.path.exists(filepath):
                # Read the image as grayscale
                # Add error handling for cv2.imread
                try:
                    shape_img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                    if shape_img is not None:
                        # Convert shape image to float [0, 1].
                        # Original uint8: 0 (black ink) -> 255, 255 (white paper) -> 0
                        # We need opacity: 0 (black ink) -> 1.0, 255 (white paper) -> 0.0
                        # So, invert and normalize uint8 to float.
                        shape_opacity = 1.0 - shape_img.astype(np.float32) / 255.0
                        _brush_shapes[name] = shape_opacity # Store the opacity map (float [0, 1])
                        # print(f"Loaded brush shape: '{name}' from '{filename}' (size {shape_img.shape[1]}x{shape_img.shape[0]})")
                    else:
                        print(f"Warning: cv2.imread returned None for brush shape: {filepath}. File might be corrupted or not an image.")
                        _brush_shapes[name] = None # Store None if loading failed for this specific shape
                except Exception as e:
                    print(f"Error reading brush shape file {filepath}: {e}. Skipping this shape.")
                    _brush_shapes[name] = None # Store None on error
            else:
                # print(f"Warning: Brush shape file not found: {filepath}")
                _brush_shapes[name] = None # Store None if file missing

    # Fallback if 'round' shape is not successfully loaded
    if 'round' not in _brush_shapes or _brush_shapes['round'] is None:
        print("Warning: Default brush shape 'round' not successfully loaded. Creating synthetic fallback.")
        size = 128 # Synthesis size
        # Create a blurry gray circle on a white background, then invert for opacity
        temp_img = np.full((size, size), 255, dtype=np.uint8) # White background
        cv2.circle(temp_img, (size//2, size//2), int(size * 0.4), 50, -1) # Draw a gray circle (value 50)

        # Apply a bit more blur and contrast
        temp_img = cv2.GaussianBlur(temp_img, (9,9), 0)
        # Invert to black shape on white: 255 -> 0, 50 -> 205, 0 -> 255
        temp_img_inverted = 255 - temp_img
        # Convert to opacity: 0 (white) -> 0.0, 255 (black) -> 1.0
        fallback_opacity = temp_img_inverted.astype(np.float32) / 255.0

        # Add some minor random noise for texture (only to non-zero opacity areas?)
        noise = np.random.rand(size, size).astype(np.float32) * 0.05 # [0, 0.05] low amplitude noise
        fallback_opacity = np.clip(fallback_opacity + noise, 0.0, 1.0) # Add noise, slightly increasing opacity

        _brush_shapes['round'] = fallback_opacity # Store the synthetic fallback shape

# Load shapes when the module is imported
load_brush_shapes()

def get_scaled_rotated_brush_shape(brush_type: str, target_size: int, angle_degrees: float = 0.0) -> np.ndarray:
    """
    Retrieves a brush shape mask (opacity, float [0, 1]), scales and rotates it to the target_size.
    Returns a square mask of size (target_size, target_size). Uses fallback if type not found.

    Args:
        brush_type: The name of the brush type ('round', 'flat', etc.).
        target_size: The desired brush size (diameter in pixels) in canvas coordinates.
        angle_degrees: Rotation angle in degrees (e.g., direction of stroke).

    Returns:
        np.ndarray: The transformed brush shape mask (float [0, 1]), size (target_size, target_size).
                    1.0 is opaque (apply ink), 0.0 is transparent.
                    Returns the synthetic fallback shape if the specified type is not found or loading failed.
    """
    global _brush_shapes
    # Get the base shape mask (opacity float [0, 1]) - use .get with default fallback
    base_shape_opacity = _brush_shapes.get(brush_type, _brush_shapes.get('round')) # Fallback to 'round' synthetic is handled in load_shapes

    if base_shape_opacity is None or base_shape_opacity.size == 0:
         # This should be covered by the fallback in load_brush_shapes, but defensive check
         print("FATAL ERROR: Brush shape 'round' fallback is also invalid. Returning minimal array.")
         return np.zeros((max(1, int(target_size)), max(1, int(target_size))), dtype=np.float32) + 0.5 # Return a semi-transparent square as absolute last resort

    # Ensure target_size is a positive integer
    scale_target_size = max(1, int(target_size))
    current_size = base_shape_opacity.shape[0] # Assuming base shape is square

    # Resize the base shape to the desired target_size
    if current_size != scale_target_size:
        # Use INTER_AREA for shrinking, INTER_LINEAR for zooming
        interpolation = cv2.INTER_AREA if current_size > scale_target_size else cv2.INTER_LINEAR
        try:
            # Check if scaling is possible (size > 0)
            if scale_target_size > 0 and current_size > 0:
                resized_shape_opacity = cv2.resize(base_shape_opacity, (scale_target_size, scale_target_size), interpolation=interpolation)
            else:
                # Handle zero or negative size case explicitly
                print(f"Warning: Cannot resize brush shape, target or current size is zero/negative. Target: {scale_target_size}, Current: {current_size}.")
                resized_shape_opacity = np.zeros((1, 1), dtype=np.float32) # Return a minimal transparent shape
        except cv2.error as e:
            print(f"Error resizing brush shape from {current_size} to {scale_target_size}. Error: {e}. Returning base shape.")
            return base_shape_opacity # Return original base shape if resize fails

    else:
        rotated_shape_opacity = base_shape_opacity.copy() # Make a copy before potential rotation

    # Apply rotation using warpAffine
    # Angle 0 in Qt/OpenCV is horizontal right. Angle increases anti-clockwise.
    # math.degrees(atan2(dy, dx)) gives angle in degrees [-180, 180].
    # cv2.getRotationMatrix2D angle is positive for anti-clockwise rotation. Match the range directly.
    # Only rotate if size is meaningful
    if angle_degrees != 0.0 and resized_shape_opacity.shape[0] > 1 and resized_shape_opacity.shape[1] > 1:
        # Rotation center is the middle of the image (float coordinates for cv2)
        center = ((resized_shape_opacity.shape[1] - 1) / 2.0, (resized_shape_opacity.shape[0] - 1) / 2.0)
        # Angle for cv2.getRotationMatrix2D is positive for anti-clockwise rotation. Should match math.degrees logic.
        M = cv2.getRotationMatrix2D(center, angle_degrees, 1.0) # Rotation matrix
        # Warp the image, keeping the same size. Use borderValue=0.0 to fill outside with transparent (0 opacity).
        try:
            rotated_shape_opacity = cv2.warpAffine(resized_shape_opacity, M, (resized_shape_opacity.shape[1], resized_shape_opacity.shape[0]), borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
        except Exception as e: # Catch general exceptions from warpAffine
            print(f"Error rotating brush shape. Error: {e}. Returning resized shape.")
            return resized_shape_opacity # Return resized shape if rotation fails
    else:
         rotated_shape_opacity = resized_shape_opacity

    return rotated_shape_opacity # Return the opacity mask [0, 1] float

# --- apply_basic_brush_stroke_segment (Main entry point for EACH stroke segment) ---
# Applies basic ink effects immediately to the Lienzo for a single segment.
# This is the function that InkCanvasWidget imports and calls during mouseMove/mousePress.
# Note: This function currently encapsulates the core logic, previously possibly within a function named differently.
# It modifies the Lienzo directly and returns the affected canvas area (QRect).

def apply_basic_brush_stroke_segment( # <--- Renamed the function here
    lienzo: Lienzo, # The Lienzo instance to draw on (MODIFIABLE)
    p1_canvas: QPoint, # Start point of the segment (full canvas coordinates)
    p2_canvas: QPoint, # End point of the segment (full canvas coordinates)
    brush_params: dict
) -> QRect: # Returns the canvas rectangle that was directly inked (before blur)
    """
    Applies basic ink effects for a line segment (p1_canvas to p2_canvas) onto the Lienzo.
    This function crops a local area, applies ink effects using apply_basic_ink_application,
    and pastes the result back to the Lienzo.

    Args:
        lienzo: The Lienzo instance. MODIFIED IN-PLACE.
        p1_canvas: Start point of the segment (canvas coordinates).
        p2_canvas: End point of the segment (canvas coordinates).
        brush_params: Dictionary with 'size', 'density', 'feibai', 'type'.

    Returns:
        QRect: The rectangle on the canvas that was directly inked during this segment.
               Returns empty QRect if nothing was applied (e.g., invalid input).
    """
    # Check for invalid input
    if lienzo is None:
        # print("Warning: Lienzo is None in apply_basic_brush_stroke_segment.")
        return QRect()

    canvas_width, canvas_height = lienzo.get_size()
    if canvas_width <= 0 or canvas_height <= 0:
         return QRect()

    # --- Determine the local area to process ---
    # Calculate a bounding box around the segment endpoints, expanded by brush size/2 for safety.
    # This local area is where we'll crop the canvas, apply ink using the brush shape, and paste back.
    brush_size = max(1, int(brush_params.get('size', 15)))
    brush_radius = brush_size // 2

    # Include points and an buffer around them equal to the brush radius.
    process_x1 = min(p1_canvas.x(), p2_canvas.x()) - brush_radius
    process_y1 = min(p1_canvas.y(), p2_canvas.y()) - brush_radius
    process_x2 = max(p1_canvas.x(), p2_canvas.x()) + brush_radius + 1 # +1 for exclusive end
    process_y2 = max(p1_canvas.y(), p2_canvas.y()) + brush_radius + 1 # +1 for exclusive end

    # Clamp the processing rectangle coordinates to the canvas boundaries
    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2 = min(canvas_width, process_x2)
    process_y2 = min(canvas_height, process_y2)

    # Calculate width and height and create the QRect for the processing area
    process_w = max(0, process_x2 - process_x1)
    process_h = max(0, process_y2 - process_y1)

    process_rect_canvas = QRect(process_x1, process_y1, process_w, process_h)

    # Check if the local processing rectangle is valid (has positive width and height)
    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        # print("Calculated processing area for segment is too small after clipping.")
        return QRect() # Invalid processing area, cannot apply ink

    # --- Extract the local area from the Lienzo ---
    # Get the uint8 canvas data for the local area. This array will be modified.
    try:
        local_canvas_area_uint8 = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height()))
        # Check if cropping was successful
        if local_canvas_area_uint8 is None or local_canvas_area_uint8.size == 0:
             print("Warning: Cropping area from Lienzo for segment failed or returned empty.")
             return QRect()
    except Exception as e:
        print(f"Error cropping Lienzo for segment: {e}. Skipping ink application.")
        return QRect()

    # --- Apply Basic Ink Effects to the Local Area ---
    # Call the helper function that does the actual pixel modification within the local area.
    # This function operates in-place on local_canvas_area_uint8.
    try:
        # This is where apply_basic_ink_application was previously defined.
        # Moving its logic here or calling it (if kept as internal helper)
        # Let's integrate its logic directly here for this version, as it's only used here.
        # Retaining apply_basic_ink_application as an internal helper function is also an option.
        # For clarity and fixing the immediate import error, let's redefine the logic under the correct name.

        # --- Integrated Logic from apply_basic_ink_application ---
        # Ensure parameters are valid numbers for calculation
        density = np.clip(float(brush_params.get('density', 60)), 0.0, 100.0)
        feibai = np.clip(float(brush_params.get('feibai', 20)), 0.0, 100.0)
        brush_type = brush_params.get('type', 'round') # Ensure this matches lookup key

        area_height, area_width = local_canvas_area_uint8.shape[:2] # Dimensions of the local area
        brush_radius = brush_size // 2

        # Calculate segment direction for brush rotation (using canvas points)
        dx_canvas = p2_canvas.x() - p1_canvas.x()
        dy_canvas = p2_canvas.y() - p1_canvas.y()
        angle_degrees = 0.0
        if dx_canvas != 0 or dy_canvas != 0:
            angle_rad = math.atan2(dy_canvas, dx_canvas) # Angle from x-axis to (dx, dy), in radians [-pi, pi]
            angle_degrees = math.degrees(angle_rad) # Convert to degrees [-180, 180]

        # Generate a base noise texture for Feibai effect over the WHOLE LOCAL area
        try:
            noise_texture_area = np.random.rand(area_height, area_width).astype(np.float32) # [0, 1]
        except Exception as e:
             print(f"Error generating noise texture within apply_basic_brush_stroke_segment: {e}. Skipping ink application.")
             # Return the original cropped area unchanged for pasting (better than crashing?)
             lienzo.paste_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                process_rect_canvas.width(), process_rect_canvas.height()), local_canvas_area_uint8)
             return QRect() # Indicate no new ink applied

        # Calculate number of interpolation steps between points to draw continuous line
        # Calculate based on canvas distance, not relative distance now
        dist_canvas = math.sqrt(dx_canvas**2 + dy_canvas**2) if dx_canvas != 0 or dy_canvas != 0 else 0
        num_steps = max(int(dist_canvas), 1) # Always process at least one point

        # Iterate through interpolated points along the segment trajectory (canvas coordinates)
        for i in range(num_steps + 1):
            t = float(i) / num_steps # Interpolation parameter [0, 1]

            # Current point in full canvas coordinates
            px_canvas = int(p1_canvas.x() + t * dx_canvas)
            py_canvas = int(p1_canvas.y() + t * dy_canvas)

            # Convert canvas point to coordinates relative to the local cropped area's origin
            px_rel = px_canvas - process_rect_canvas.x()
            py_rel = py_canvas - process_rect_canvas.y()

            # Check if the relative point is within the bounds of the local area (should be, due to expansion)
            if not (0 <= px_rel < area_width and 0 <= py_rel < area_height):
                # This shouldn't happen with sufficient margin, but defensive check
                # print(f"Warning: Interpolated point ({px_canvas},{py_canvas}) is outside the local processing area ({process_rect_canvas.x()},{process_rect_canvas.y()})-({process_rect_canvas.right()},{process_rect_canvas.bottom()}). Skipping point.")
                continue

            # --- Get and Transform Brush Shape for the current point ---
            # Get the scaled and rotated brush shape mask (opacity, float [0, 1])
            # This mask will be (brush_size, brush_size)
            brush_mask_size = brush_size
            current_point_brush_shape_mask = get_scaled_rotated_brush_shape(brush_type, brush_mask_size, angle_degrees)

            # Check if brush shape mask is minimal
            if current_point_brush_shape_mask is None or current_point_brush_shape_mask.size == 0:
                 # print("Warning: Brush shape mask is invalid or empty. Skipping point ink application.")
                 continue # Skip applying ink for this point

            # --- Calculate overlap region between the brush mask and the local area (using relative coords) ---
            # Top-left corner of the brush_size x brush_size mask centered at (px_rel, py_rel) relative to local area origin
            brush_apply_x_start_rel = px_rel - brush_radius
            brush_apply_y_start_rel = py_rel - brush_radius
            brush_apply_x_end_rel = brush_apply_x_start_rel + brush_size # End coordinate is exclusive
            brush_apply_y_end_rel = brush_apply_y_start_rel + brush_size # End coordinate is exclusive

            # Calculate the overlap coordinates WITHIN local_canvas_area_uint8 (which is relative 0,0)
            slice_overlap_x1 = max(0, brush_apply_x_start_rel)
            slice_overlap_y1 = max(0, brush_apply_y_start_rel)
            slice_overlap_x2 = min(area_width, brush_apply_x_end_rel) # area_width is local_canvas_area_uint8.shape[1]
            slice_overlap_y2 = min(area_height, brush_apply_y_end_rel) # area_height is local_canvas_area_uint8.shape[0]

            # Check if the overlap region is valid (has positive width and height)
            if slice_overlap_x2 <= slice_overlap_x1 or slice_overlap_y2 <= slice_overlap_y1:
                 continue # Skip if overlap is empty

            # Calculate the corresponding slice coordinates within the brush mask itself (relative 0,0)
            # brush_mask_relative_* are coordinates within current_point_brush_shape_mask (which is relative 0,0)
            brush_mask_slice_x1 = slice_overlap_x1 - brush_apply_x_start_rel
            brush_mask_slice_y1 = slice_overlap_y1 - brush_apply_y_start_rel
            brush_mask_slice_x2 = brush_mask_slice_x1 + (slice_overlap_x2 - slice_overlap_x1) # Width must match overlap width
            brush_mask_slice_y2 = brush_mask_slice_y1 + (slice_overlap_y2 - slice_overlap_y1) # Height must match overlap height

            # --- Extract the actual slices from the local canvas area and the brush mask ---
            # Get the slice from the local canvas area that overlaps with the brush
            current_local_canvas_overlap_slice = local_canvas_area_uint8[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2]
            # Get the corresponding slice from the brush shape opacity mask
            brush_slice_opacity = current_point_brush_shape_mask[brush_mask_slice_y1:brush_mask_slice_y2, brush_mask_slice_x1:brush_mask_slice_x2]
            # Get the corresponding noise slice for the overlap area
            noise_slice = noise_texture_area[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2]

            # Ensure all slices derived from the same overlap region have identical shapes before element-wise operations
            if current_local_canvas_overlap_slice.shape != brush_slice_opacity.shape or current_local_canvas_overlap_slice.shape != noise_slice.shape:
                 print(f"Critical Slicing Error during segment ink application: Shape mismatch! Local:{current_local_canvas_overlap_slice.shape}, Brush:{brush_slice_opacity.shape}, Noise:{noise_slice.shape}. Skipping point ({px_canvas},{py_canvas})")
                 continue # Skip this point

            # --- Calculate Effective Opacity for this pixel application ---
            # Base ink opacity determined by density slider [0, 1]
            base_density_opacity = density / 100.0

            # Feibai effect: reduce opacity where noise is high.
            feibai_modifier = 1.0 - (feibai / 100.0) * (1.0 - noise_slice)

            # Effective pixel opacity combines base density, brush shape opacity, and feibai modifier
            effective_pixel_opacity = base_density_opacity * brush_slice_opacity * feibai_modifier

            # --- Blend new ink onto the current local canvas overlap slice (uint8) ---
            # Blend formula based on np.minimum.
            # Target shade value based on effective opacity: 255 (transparent) * (1.0 - opacity). Range [0, 255] float.
            target_shade_float = 255.0 * (1.0 - effective_pixel_opacity) # float [0, 255]

            # Apply blending using np.minimum
            current_local_canvas_overlap_slice[:] = np.minimum(current_local_canvas_overlap_slice.astype(np.float32), target_shade_float).astype(np.uint8)
            # This modifies the slice in-place, which modifies local_canvas_area_uint8.

        # --- End Integrated Logic ---

    except Exception as e:
         print(f"Error applying basic ink effects to local area: {e}. Skipping paste.")
         # Return the original cropped area unchanged for pasting (better than crashing?)
         lienzo.paste_area((process_rect_canvas.x(), process_rect_canvas.y(),
                            process_rect_canvas.width(), process_rect_canvas.height()), local_canvas_area_uint8)
         return QRect() # Indicate no new ink applied

    # --- Paste the modified local area back onto the Lienzo ---
    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    # Ensure the modified local area has the correct shape for pasting before attempting to paste.
    if local_canvas_area_uint8.shape == (process_rect_canvas.height(), process_rect_canvas.width()):
         try:
             lienzo.paste_area(paste_rect_tuple, local_canvas_area_uint8)
             # print(f"Applied ink for segment to {process_rect_canvas} (canvas coords).")
             # Return the area that was modified on the Lienzo
             return process_rect_canvas
         except Exception as e:
             print(f"Error pasting modified local area onto Lienzo: {e}. Skipping paste.")
             return QRect() # Return empty rect on failure
    else:
        print(f"Warning: Modified local area shape mismatch {local_canvas_area_uint8.shape} vs paste rect shape {(process_rect_canvas.height(), process_rect_canvas.width())}. Skipping paste.")
        return QRect() # Return empty rect on failure

# --- apply_basic_ink_application - Original helper function, now integrated or can be removed/kept as internal helper ---
# Keeping it here but renamed as an internal helper is possible, then have apply_basic_brush_stroke_segment call it.
# But the import error is fixed by renaming the *exported* function.
# For this fix, I've integrated the logic directly, assuming the original `apply_basic_ink_application`
# was just a helper for the main segment application logic.
# If you intended apply_basic_ink_application to be called from somewhere else, you might need to reconsider the structure.
# As per the comment saying `apply_basic_brush_stroke_segment` is the main entry point,
# restructuring is necessary to make the main entry point have that name and return the inked QRect.

# Removing the now unused `apply_basic_ink_application` definition if its logic is fully integrated above.
# If you want to keep it as a helper, you'd rename the top function, and inside that function,
# you'd calculate the crop rect, crop the lienzo, calls the helper, and then paste back.
# The current structure in your brush_engine.py suggests apply_basic_ink_application operated on the
# local crop, and something else was supposed to calculate the crop, call it, and paste back.
# Let's assume the function you want to import has the signature needed by InkCanvasWidget
# and should do the crop/paste logic. So, renaming and restructuring slightly.
# Yes, InkCanvasWidget expects (Lienzo, p1, p2, params) and gets inked_rect.
# The `apply_basic_ink_application` you had took `local_canvas_area_uint8`, `local_area_rect_canvas`
# and point/params relative to that area. This is NOT the signature InkCanvasWidget expects.
# So, the function that *should* be named `apply_basic_brush_stroke_segment` must be the one
# that handles cropping the Lienzo, calling the internal logic, and pasting back.

# Let's structure it this way:
# 1. Keep apply_basic_ink_application as an internal helper (maybe rename it like _apply_ink_to_local_area).
# 2. Create a new function named apply_basic_brush_stroke_segment that takes Lienzo, p1, p2, params.
# 3. This new function calculates the processing area rect.
# 4. It crops the Lienzo using that rect.
# 5. It calls the internal helper function (_apply_ink_to_local_area) with the cropped data and correct relative points.
# 6. It pastes the modified cropped data back to the Lienzo.
# 7. It returns the processing area/inked rect.

# Reworking based on this structure to match InkCanvasWidget's expectation:

# internal helper function (renamed and simplified params)
def _apply_ink_to_local_area(
    local_area_uint8: np.ndarray, # The local uint8 numpy array to draw on (MODIFIABLE)
    p1_local: QPoint, # Start point of segment relative to local_area_uint8 top-left
    p2_local: QPoint, # End point of segment relative to local_area_uint8 top-left
    brush_params: dict,
    area_noise_texture: np.ndarray # Pre-generated noise texture slice for this area
): # Returns nothing, modifies local_area_uint8 in-place.
     """Applies basic ink effects (density, feibai, brush shape) to a small cropped uint8 canvas area."""
     # Check for invalid input array
     if local_area_uint8 is None or local_area_uint8.size == 0:
         return # Nothing to draw on

     area_height, area_width = local_area_uint8.shape[:2]
     if area_width <= 0 or area_height <= 0:
         return # Nothing to draw on
     if area_noise_texture is None or area_noise_texture.shape != local_area_uint8.shape:
         print("Error: Noise texture slice for local area has wrong shape or is None. Cannot apply feibai.")
         area_noise_texture = np.ones_like(local_area_uint8, dtype=np.float32) * 0.5 # Use a neutral noise

     # --- Get Brush Parameters ---
     brush_size = max(1, int(brush_params.get('size', 15)))
     density = np.clip(float(brush_params.get('density', 60)), 0.0, 100.0)
     feibai = np.clip(float(brush_params.get('feibai', 20)), 0.0, 100.0)
     brush_type = brush_params.get('type', 'round')

     brush_radius = brush_size // 2 # Integer radius

     # Calculate number of interpolation steps
     num_steps_rel = max(abs(p2_local.x() - p1_local.x()), abs(p2_local.y() - p1_local.y()))
     if num_steps_rel < 1: num_steps_rel = 1 # Always process at least one point

     # Calculate segment direction for brush rotation (using local points)
     dx_local = p2_local.x() - p1_local.x()
     dy_local = p2_local.y() - p1_local.y()
     angle_degrees = 0.0
     if dx_local != 0 or dy_local != 0:
          angle_rad = math.atan2(dy_local, dx_local)
          angle_degrees = math.degrees(angle_rad)

     # Iterate through interpolated points along the segment trajectory (relative to local area origin)
     for i in range(num_steps_rel + 1):
         t = float(i) / num_steps_rel # Interpolation parameter [0, 1]

         # Current point relative to the local area origin
         px_rel = int(p1_local.x() + t * dx_local)
         py_rel = int(p1_local.y() + t * dy_local)

         # Check if the relative point is roughly within bounds (should be centered near it)
         # A more robust check would be needed if the processing area calculation was less generous
         # if not (0 <= px_rel < area_width and 0 <= py_rel < area_height): continue

         # --- Get and Transform Brush Shape ---
         brush_mask_size = brush_size
         current_point_brush_shape_mask = get_scaled_rotated_brush_shape(brush_type, brush_mask_size, angle_degrees)

         if current_point_brush_shape_mask is None or current_point_brush_shape_mask.size == 0 or current_point_brush_shape_mask.shape != (brush_mask_size, brush_mask_size):
              # print("Warning: Brush shape mask is invalid or empty. Skipping point ink application.")
              continue

         # --- Calculate overlap region ---
         # Top-left corner of the brush centered at (px_rel, py_rel) relative to local area origin
         brush_apply_x_start_rel = px_rel - brush_radius
         brush_apply_y_start_rel = py_rel - brush_radius

         # Calculate the overlap coordinates within local_area_uint8 (relative 0,0)
         slice_overlap_x1 = max(0, brush_apply_x_start_rel)
         slice_overlap_y1 = max(0, brush_apply_y_start_rel)
         slice_overlap_x2 = min(area_width, brush_apply_x_start_rel + brush_size)
         slice_overlap_y2 = min(area_height, brush_apply_y_start_rel + brush_size)

         if slice_overlap_x2 <= slice_overlap_x1 or slice_overlap_y2 <= slice_overlap_y1:
              continue # Skip if overlap is empty

         # Calculate the corresponding slice coordinates within the brush mask (relative 0,0)
         brush_mask_slice_x1 = slice_overlap_x1 - brush_apply_x_start_rel
         brush_mask_slice_y1 = slice_overlap_y1 - brush_apply_y_start_rel
         brush_mask_slice_x2 = brush_mask_slice_x1 + (slice_overlap_x2 - slice_overlap_x1)
         brush_mask_slice_y2 = brush_mask_slice_y1 + (slice_overlap_y2 - slice_overlap_y1)

         # Extract slices
         current_local_area_overlap_slice = local_area_uint8[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2]
         brush_slice_opacity = current_point_brush_shape_mask[brush_mask_slice_y1:brush_mask_slice_y2, brush_mask_slice_x1:brush_mask_slice_x2]
         noise_slice = area_noise_texture[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2] # Use correct slice of pre-generated noise

         # Ensure slicing worked as expected
         if current_local_area_overlap_slice.shape != brush_slice_opacity.shape or current_local_area_overlap_slice.shape != noise_slice.shape:
              print(f"Critical Slicing Error in _apply_ink_to_local_area: Shape mismatch! Local:{current_local_area_overlap_slice.shape}, Brush:{brush_slice_opacity.shape}, Noise:{noise_slice.shape}. Skipping point.")
              continue

         # --- Calculate Effective Opacity ---
         base_density_opacity = density / 100.0
         feibai_modifier = 1.0 - (feibai / 100.0) * (1.0 - noise_slice)
         effective_pixel_opacity = base_density_opacity * brush_slice_opacity * feibai_modifier

         # --- Blend new ink ---
         target_shade_float = 255.0 * (1.0 - effective_pixel_opacity)
         current_local_area_overlap_slice[:] = np.minimum(current_local_area_overlap_slice.astype(np.float32), target_shade_float).astype(np.uint8)

# --- apply_basic_brush_stroke_segment --- (This is the one InkCanvasWidget imports)
def apply_basic_brush_stroke_segment( # <--- This name must match the import
    lienzo: Lienzo,
    p1_canvas: QPoint,
    p2_canvas: QPoint,
    brush_params: dict
) -> QRect:
    """
    Applies basic ink effects for a line segment (p1_canvas to p2_canvas) onto the Lienzo.
    This is the main entry point for applying ink for EACH stroke segment.
    It crops a local area, applies ink effects using an internal helper, and pastes the result back.

    Args:
        lienzo: The Lienzo instance. MODIFIED IN-PLACE.
        p1_canvas: Start point of the segment (canvas coordinates).
        p2_canvas: End point of the segment (canvas coordinates).
        brush_params: Dictionary with 'size', 'density', 'feibai', 'type'.

    Returns:
        QRect: The rectangle on the canvas that was directly inked during this segment.
               Returns empty QRect if nothing was applied (e.g., invalid input).
    """
    # --- Input Validation and Local Area Calculation (Same as before) ---
    if lienzo is None: return QRect()
    canvas_width, canvas_height = lienzo.get_size()
    if canvas_width <= 0 or canvas_height <= 0: return QRect()

    brush_size = max(1, int(brush_params.get('size', 15)))
    brush_radius = brush_size // 2

    process_x1 = min(p1_canvas.x(), p2_canvas.x()) - brush_radius
    process_y1 = min(p1_canvas.y(), p2_canvas.y()) - brush_radius
    process_x2 = max(p1_canvas.x(), p2_canvas.x()) + brush_radius # End is exclusive for rects, so no +1 here for safety buffer needed with min/max points
    process_y2 = max(p1_canvas.y(), p2_canvas.y()) + brush_radius # End is exclusive

    # Need to include the points themselves, handle min/max carefully
    p1_x, p1_y = p1_canvas.x(), p1_canvas.y()
    p2_x, p2_y = p2_canvas.x(), p2_canvas.y()

    # Ensure the area covers endpoints and brush radius extent
    min_x = min(p1_x, p2_x)
    max_x = max(p1_x, p2_x)
    min_y = min(p1_y, p2_y)
    max_y = max(p1_y, p2_y)

    process_x1 = min_x - brush_radius
    process_y1 = min_y - brush_radius
    process_x2 = max_x + brush_radius # The max coordinate fully included in the kernel.
    process_y2 = max_y + brush_radius # The max coordinate fully included in the kernel.

    # Clamp coordinates to canvas boundaries
    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2 = min(canvas_width - 1, process_x2) # Clamp to max *index*
    process_y2 = min(canvas_height - 1, process_y2) # Clamp to max *index*

    # Convert clamped min/max indices back to (x,y,w,h) format for QRect/cropping
    final_process_x = process_x1
    final_process_y = process_y1
    final_process_w = process_x2 - process_x1 + 1 # Width is inclusive range + 1
    final_process_h = process_y2 - process_y1 + 1 # Height is inclusive range + 1

    process_rect_canvas = QRect(final_process_x, final_process_y, final_process_w, final_process_h)

    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        # print("Calculated processing area for segment is too small after clipping.")
        return QRect()

    # --- Crop Lienzo ---
    try:
        local_canvas_area_uint8 = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height()))
        if local_canvas_area_uint8 is None or local_canvas_area_uint8.size == 0:
             print("Warning: Cropping area from Lienzo for segment failed or returned empty.")
             return QRect()
    except Exception as e:
        print(f"Error cropping Lienzo for segment: {e}. Skipping ink application.")
        return QRect()

    # --- Generate Noise Texture for the Local Area ---
    try:
        area_height, area_width = local_canvas_area_uint8.shape[:2]
        noise_texture_area = np.random.rand(area_height, area_width).astype(np.float32) # [0, 1]
    except Exception as e:
         print(f"Error generating noise texture within apply_basic_brush_stroke_segment: {e}. Proceeding without feibai texture.")
         noise_texture_area = np.ones_like(local_canvas_area_uint8, dtype=np.float32) * 0.5 # Neutral noise to prevent errors

    # --- Convert canvas points to relative points for the helper ---
    p1_local = QPoint(p1_canvas.x() - process_rect_canvas.x(), p1_canvas.y() - process_rect_canvas.y())
    p2_local = QPoint(p2_canvas.x() - process_rect_canvas.x(), p2_canvas.y() - process_rect_canvas.y())

    # --- Apply Ink using the internal helper ---
    try:
        _apply_ink_to_local_area(
            local_canvas_area_uint8,
            p1_local,
            p2_local,
            brush_params,
            noise_texture_area # Pass the noise texture
        )
    except Exception as e:
         print(f"Error applying basic ink effects to local area (via helper): {e}. Skipping paste.")
         # Return the original cropped area unchanged for pasting (better than crashing?)
         lienzo.paste_area((process_rect_canvas.x(), process_rect_canvas.y(),
                            process_rect_canvas.width(), process_rect_canvas.height()), local_canvas_area_uint8)
         return QRect() # Indicate no new ink applied

    # --- Paste the modified local area back onto the Lienzo (Same as before) ---
    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    if local_canvas_area_uint8.shape == (process_rect_canvas.height(), process_rect_canvas.width()):
         try:
             lienzo.paste_area(paste_rect_tuple, local_canvas_area_uint8)
             # print(f"Applied ink for segment to {process_rect_canvas} (canvas coords).")
             # Return the area that was modified on the Lienzo
             return process_rect_canvas
         except Exception as e:
             print(f"Error pasting modified local area onto Lienzo: {e}. Skipping paste.")
             return QRect() # Return empty rect on failure
    else:
        print(f"Warning: Modified local area shape mismatch {local_canvas_area_uint8.shape} vs paste rect shape {(process_rect_canvas.height(), process_rect_canvas.width())}. Skipping paste.")
        return QRect() # Return empty rect on failure

# The old apply_basic_ink_application definition is now replaced/integrated into the helper _apply_ink_to_local_area
# and the main entry point apply_basic_brush_stroke_segment.
# Remove the old `def apply_basic_ink_application(...)` block entirely once you replace it with the code above.

# --- apply_localized_blur (Applies Blur and Blends result back to Lienzo) ---
# Called by finalize_stroke
def apply_localized_blur(
    lienzo: Lienzo,
    canvas_rect_to_blur: QRect, # The core area where ink was applied during a stroke (canvas coordinates)
    wetness: int, # Wetness parameter [0, 100]
    brush_size: int # Brush size is needed to influence blur radius
) -> QRect: # Return the canvas rectangle that was modified (for widget update)
    """
    Applies simulated ink diffusion (Bilateral Filter) to a specified region around ink strokes.
    Blends the blurred result with the original data using np.minimum to simulate darkening/diffusion
    without over-brightening. Pastes the result directly onto the Lienzo.

    Args:
        lienzo: The Lienzo instance to paste onto.
        canvas_rect_to_blur: The canvas area (QRect, canvas coordinates) which received ink
                             during a stroke. Blur radiation starts from here.
        wetness: Wetness parameter (0-100) controlling blur strength and extent.
        brush_size: Brush size, influencing blur radius calculation.

    Returns:
        QRect: The canvas rectangle that was updated on the Lienzo after blur and paste.
               Returns empty QRect if nothing was applied (e.g., invalid input, wetness 0).
    """
    # Only apply blur if wetness is greater than 0 and the target region is valid
    if lienzo is None or canvas_rect_to_blur.isNull() or wetness <= 0 or canvas_rect_to_blur.width() <= 0 or canvas_rect_to_blur.height() <= 0:
        # print("Skipping localized blur due to invalid input, rect size or wetness=0.")
        return QRect() # Invalid input, nothing to apply

    canvas_height, canvas_width = lienzo.get_size()
    if canvas_height <= 0 or canvas_width <= 0:
         # print("Skipping localized blur due to invalid canvas size.")
         return QRect()

    # --- Determine the actual processing area for blur ---
    # This area is an expansion of canvas_rect_to_blur to allow ink to diffuse into surrounding paper.
    # The expansion amount is based on 'wetness' and 'brush_size'.
    # Let sigmaSpace be the primary control for spatial diffusion distance in BilateralFilter.
    # Map wetness [0, 100] to sigmaSpace [0, ~20] empirically.
    base_sigma_space = wetness / 100.0 * 20.0
    base_sigma_space = max(0.5, base_sigma_space) # Minimum spatial sigma for noticeable effect

    # Estimate required expansion needed around the inked area for the filter to operate.
    # The diameter of the blur kernel (d parameter in BilateralFilter, or derived from sigmaSpace)
    # determines how far away pixels can influence the center pixel.
    # Expansion should be roughly half the maximum kernel size or related to sigmaSpace.
    # Let's make expansion correlate to sigmaSpace.
    estimated_blur_radius = int(base_sigma_space * 2.5) # Expand by roughly 2.5 * sigmaSpace
    estimated_blur_radius = max(estimated_blur_radius, brush_size // 2) # Ensure expansion is at least half brush size
    estimated_blur_radius = max(estimated_blur_radius, 5) # Minimum expansion pixels

    # Calculate the rectangle for the processing area including expansion
    process_x1 = canvas_rect_to_blur.left() - estimated_blur_radius
    process_y1 = canvas_rect_to_blur.top() - estimated_blur_radius
    process_x2 = canvas_rect_to_blur.right() + estimated_blur_radius
    process_y2 = canvas_rect_to_blur.bottom() + estimated_blur_radius

    # Clip the processing rectangle coordinates to the canvas boundaries
    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2 = min(canvas_width, process_x2) # min should be canvas_width (exclusive upper bound for pixel range)
    process_y2 = min(canvas_height, process_y2) # min should be canvas_height (exclusive upper bound)

    # Calculate the width and height and create the QRect for the processing area
    process_w = max(0, process_x2 - process_x1)
    process_h = max(0, process_y2 - process_y1)

    process_rect_canvas = QRect(process_x1, process_y1, process_w, process_h)

    # Check if the calculated processing rectangle is valid (has positive width and height)
    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        # print("Calculated processing area for blur is invalid or too small after clipping.")
        return QRect() # Invalid processing area, cannot apply blur

    # --- Extract the processing area from the Lienzo ---
    # Get the uint8 canvas data directly for processing.
    # This area already includes the ink applied by apply_basic_brush_stroke_segment.
    try:
        processing_area_uint8 = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height()))
        # Check if cropping was successful
        if processing_area_uint8 is None or processing_area_uint8.size == 0:
             print("Warning: Cropping area from Lienzo for blur failed or returned empty.")
             return QRect()
    except Exception as e:
        print(f"Error cropping Lienzo for blur: {e}. Skipping blur.")
        return QRect()

    # --- Store the original state of the processing area (before blur) ---
    # We need this copy for the intelligent blending step (using np.minimum).
    original_processing_area_uint8 = processing_area_uint8.copy()

    # --- Apply Bilateral Filter to the extracted processing area ---
    # Bilateral filter requires uint8 input and outputs uint8.
    # sigmaColor: Color distance tolerance. Higher wetness -> higher tolerance -> blur spreads more into lighter areas.
    # Map wetness [0, 100] to sigmaColor [0, ~150] empirically.
    sigma_color = wetness / 100.0 * 150.0
    sigma_color = max(1.0, sigma_color) # Ensure minimum value for effect

    # Apply bilateral filter. d=0 lets OpenCV determine diameter from sigmaSpace.
    # Ensure parameters are valid floats.
    try:
        # Apply bilateral filter
        processed_area_blurred = cv2.bilateralFilter(processing_area_uint8, 0, float(sigma_color), float(base_sigma_space))
    except Exception as e:
         print(f"Error during cv2.bilateralFilter in apply_localized_blur: {e}. Skipping blur.")
         return QRect() # Return empty rect on error

    # --- Intelligent Blending to Simulate Diffusion ---
    # Blend the blurred result with the original area (before-blur).
    # Use np.minimum: result pixel = min(original_pixel, blurred_pixel).
    # This simulates ink darkening the paper and spreading into lighter areas,
    # while preventing the blur from making already dark areas lighter or introducing bright halos.
    blended_area_uint8 = np.minimum(original_processing_area_uint8, processed_area_blurred)

    # --- Paste the blended area back onto the Lienzo ---
    # Paste the blended result back into the calculated processing rectangle on the main canvas.
    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    # Ensure the blended area has the correct shape for pasting before attempting to paste.
    if blended_area_uint8.shape == (process_rect_canvas.height(), process_rect_canvas.width()):
         try:
             lienzo.paste_area(paste_rect_tuple, blended_area_uint8)
             # print(f"Applied localized blur blending to {process_rect_canvas} (canvas coords) with wetness={wetness}, expansion={estimated_blur_radius}.")
             # Return the area that was modified on the Lienzo
             return process_rect_canvas
         except Exception as e:
             print(f"Error pasting blended area onto Lienzo: {e}. Skipping paste.")
             return QRect() # Return empty rect on failure
    else:
        print(f"Warning: Blended area shape mismatch {blended_area_uint8.shape} vs paste rect shape {(process_rect_canvas.height(), process_rect_canvas.width())}. Skipping paste.")
        return QRect() # Return empty rect on failure

# --- finalize_stroke (Main entry point for stroke finalization) ---
# Called from InkCanvasWidget on mouse release.
# This function calls apply_localized_blur to perform the blur and pasting.
def finalize_stroke(
    lienzo: Lienzo,
    stroke_inked_region_canvas: QRect, # The accumulated ink region QRect from InkCanvasWidget
    brush_params: dict
) -> QRect: # Return the canvas rectangle that needs updating after finalization (including diffusion)
    """
    Finalizes a stroke after mouse release by applying localized diffusion (blur)
    to the accumulated inked area.

    Args:
        lienzo: The Lienzo instance. MODIFIED IN-PLACE by the blur process.
        stroke_inked_region_canvas: The union of all ink application rectangles for this stroke (canvas coordinates).
                                    This defines the core area around which blur will be applied.
        brush_params: Brush parameters ('wetness', 'size').

    Returns:
        QRect: The final canvas rectangle that was updated after blur and paste.
               This rectangle includes the diffusion expansion.
               Returns empty QRect if no blur applied or invalid input.
    """
    # print("Calling finalize_stroke (basic version)...") # Debugging

    # Call apply_localized_blur with the accumulated inked region.
    # apply_localized_blur modifies the Lienzo directly by cropping, processing, and pasting.
    # It returns the canvas rectangle that was modified (including the blur expansion).
    final_updated_area_canvas = apply_localized_blur(
        lienzo,
        stroke_inked_region_canvas, # The area where ink was applied
        brush_params.get('wetness', 70), # Pass wetness param
        brush_params.get('size', 15) # Pass brush size param
    )

    # apply_localized_blur returns the process rect (canvas coords) that was modified.
    return final_updated_area_canvas # This is the area that was blurred and pasted

# --- apply_basic_brush_stroke_segment (Original name for main segment processor) ---
# Renamed from apply_basic_brush_stroke_segment to apply_stroke_segment
# This is the main entry point for processing EACH stroke segment from mousePress/MouseMove.
# It applies basic ink effects immediately to the Lienzo.
# Let's keep the original name `apply_basic_brush_stroke_segment` as that is what InkCanvasWidget imports.
# The function definition is above. It takes Lienzo, p1, p2, params and returns the inked rect.

# The function `apply_stroke_segment_advanced` from the complex version is NOT used here.