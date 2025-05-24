# processing/brush_engine.py

import numpy as np
import cv2
from PyQt5.QtCore import QPoint, QRect # QColor not needed here
import math
import random
import os
from processing.lienzo import Lienzo # QColor not needed here

_brush_shapes = {}
_brush_shape_folder = os.path.join(os.path.dirname(__file__), '..', 'resources')

def load_brush_shapes():
    global _brush_shapes
    global _brush_shape_folder

    shape_files = {
        'round': 'brush_round.png',
        'flat': 'brush_flat.png',
        'dry': 'brush_dry.png',
        'tapered': 'brush_tapered.png',
    }

    if not os.path.exists(_brush_shape_folder):
         print(f"Warning: Resources folder not found at {_brush_shape_folder}. Cannot load brush shapes.")
         for name in shape_files.keys():
              _brush_shapes[name] = None
    else:
        for name, filename in shape_files.items():
            filepath = os.path.join(os.path.join(os.path.dirname(__file__), '..', 'resources'), filename)
            if os.path.exists(filepath):
                try:
                    shape_img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
                    if shape_img is not None:
                        if len(shape_img.shape) == 3 and shape_img.shape[2] == 4:
                            alpha_channel = shape_img[:, :, 3]
                            shape_opacity = alpha_channel.astype(np.float32) / 255.0
                        elif len(shape_img.shape) == 2:
                            shape_opacity = 1.0 - shape_img.astype(np.float32) / 255.0
                        else:
                             print(f"Warning: Loading brush '{filename}' with unsupported channels ({shape_img.shape[2]}), converting to grayscale.")
                             gray_img = cv2.cvtColor(shape_img, cv2.COLOR_BGR2GRAY)
                             shape_opacity = 1.0 - gray_img.astype(np.float32) / 255.0

                        h, w = shape_opacity.shape[:2]
                        if h != w:
                             print(f"Warning: Brush shape '{filename}' is not square ({w}x{h}). Resizing.")
                             size = min(h, w)
                             shape_opacity = cv2.resize(shape_opacity, (size, size), interpolation=cv2.INTER_AREA)
                        if shape_opacity.size > 0:
                            _brush_shapes[name] = shape_opacity.copy()
                        else:
                             print(f"Warning: Brush shape '{filename}' resulted in empty data after processing.")
                             _brush_shapes[name] = None

                    else:
                        print(f"Warning: cv2.imread returned None for brush shape: {filepath}.")
                        _brush_shapes[name] = None
                except Exception as e:
                    print(f"Error reading brush shape file {filepath}: {e}. Skipping.")
                    _brush_shapes[name] = None
            else:
                _brush_shapes[name] = None

    fallback_size = 128
    if 'round' not in _brush_shapes or _brush_shapes['round'] is None or _brush_shapes['round'].size == 0:
        print("Creating synthetic 'round' fallback.")
        temp_img = np.full((fallback_size, fallback_size), 255, dtype=np.uint8)
        cv2.circle(temp_img, (fallback_size//2, fallback_size//2), int(fallback_size * 0.4), 50, -1)
        temp_img = cv2.GaussianBlur(temp_img, (9,9), 0)
        temp_img_inverted = 255 - temp_img
        fallback_opacity = temp_img_inverted.astype(np.float32) / 255.0
        noise = np.random.rand(fallback_size, fallback_size).astype(np.float32) * 0.05
        fallback_opacity = np.clip(fallback_opacity + noise, 0.0, 1.0)
        _brush_shapes['round'] = fallback_opacity

    if 'flat' not in _brush_shapes or _brush_shapes['flat'] is None or _brush_shapes['flat'].size == 0:
        print("Creating synthetic 'flat' fallback.")
        temp_img = np.full((fallback_size, fallback_size), 255, dtype=np.uint8)
        center = (fallback_size//2, fallback_size//2)
        axesLength = (int(fallback_size * 0.45), int(fallback_size * 0.15))
        cv2.ellipse(temp_img, center, axesLength, 0, 0, 360, 50, -1)
        temp_img = cv2.GaussianBlur(temp_img, (9,9), 0)
        temp_img_inverted = 255 - temp_img
        fallback_opacity = temp_img_inverted.astype(np.float32) / 255.0
        _brush_shapes['flat'] = fallback_opacity

def get_available_brush_types() -> list[str]:
    """Returns successfully loaded brush types."""
    available_types = [name for name, shape in _brush_shapes.items() if shape is not None and shape.size > 0]
    if 'round' in _brush_shapes and _brush_shapes['round'] is not None and _brush_shapes['round'].size > 0 and 'round' not in available_types:
         available_types.insert(0, 'round')
    return available_types

def get_scaled_rotated_brush_shape(brush_type: str, target_size: int, angle_degrees: float = 0.0) -> np.ndarray:
    """Retrieves, scales, and rotates a brush shape mask."""
    scale_target_size = max(1, int(target_size))
    base_shape_opacity = _brush_shapes.get(brush_type)

    if base_shape_opacity is None or base_shape_opacity.size == 0:
         print(f"Warning: Brush shape '{brush_type}' not found or invalid. Falling back to 'round'.")
         base_shape_opacity = _brush_shapes.get('round')

    if base_shape_opacity is None or base_shape_opacity.size == 0:
         print("FATAL ERROR: Brush shape 'round' fallback is also invalid.")
         return np.zeros((max(1, scale_target_size), max(1, scale_target_size)), dtype=np.float32)

    current_size = base_shape_opacity.shape[0]

    if current_size != scale_target_size:
        interpolation = cv2.INTER_AREA if current_size > scale_target_size else cv2.INTER_LINEAR
        try:
             if scale_target_size > 0 and base_shape_opacity.shape[0] > 0 and base_shape_opacity.shape[1] > 0:
                 resized_shape_opacity = cv2.resize(base_shape_opacity, (scale_target_size, scale_target_size), interpolation=interpolation)
             else:
                 print(f"Warning: Cannot resize brush shape, target or current size invalid. Target: {scale_target_size}.")
                 resized_shape_opacity = np.zeros((max(1, scale_target_size), max(1, scale_target_size)), dtype=np.float32)
        except Exception as e:
            print(f"Error resizing brush. Error: {e}. Returning base shape.")
            resized_shape_opacity = base_shape_opacity
    else:
        resized_shape_opacity = base_shape_opacity.copy()

    if angle_degrees != 0.0 and resized_shape_opacity.shape[0] > 1 and resized_shape_opacity.shape[1] > 1:
        center = ((resized_shape_opacity.shape[1] - 1) / 2.0, (resized_shape_opacity.shape[0] - 1) / 2.0)
        M = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
        try:
             rotated_shape_opacity = cv2.warpAffine(resized_shape_opacity, M, (resized_shape_opacity.shape[1], resized_shape_opacity.shape[0]), borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
        except Exception as e:
            print(f"Error rotating brush shape. Error: {e}. Returning resized shape.")
            rotated_shape_opacity = resized_shape_opacity
    else:
         rotated_shape_opacity = resized_shape_opacity

    return rotated_shape_opacity

def _apply_single_brush_stamp(
    local_area_uint8: np.ndarray, # HxWx3 BGR uint8
    center_local: QPoint,
    brush_params: dict,
    local_area_noise_texture: np.ndarray, # HxW float32 (still grayscale noise)
    stamp_segment_angle_rad: float = None
):
     """Applies a single brush stamp (ink or eraser) to a local BGR uint8 canvas area centered at center_local."""
     if local_area_uint8 is None or local_area_uint8.size == 0 or local_area_uint8.shape[2] != 3: return # Expect BGR
     area_height, area_width = local_area_uint8.shape[:2]
     if area_width <= 0 or area_height <= 0: return

     is_eraser = brush_params.get('is_eraser', False)
     brush_color_bgr = brush_params.get('color', (0, 0, 0)) # Grab color tuple (B, G, R)

     if local_area_noise_texture is None or local_area_noise_texture.shape[:2] != local_area_uint8.shape[:2]: # Compare HxW
          print("Error: Noise texture slice has wrong shape or is None.")
          local_area_noise_texture = np.ones(local_area_uint8.shape[:2], dtype=np.float32) * 0.5 # Fallback noise HxW

     base_brush_size = max(1, int(brush_params.get('size', 15)))
     flow = np.clip(float(brush_params.get('flow', 100)), 0.0, 100.0)
     density = np.clip(float(brush_params.get('density', 60)), 0.0, 100.0)
     feibai = np.clip(float(brush_params.get('feibai', 20)), 0.0, 100.0)
     hardness = np.clip(float(brush_params.get('hardness', 50)), 0.0, 100.0)
     brush_type = brush_params.get('type', 'round')

     pos_jitter = np.clip(float(brush_params.get('pos_jitter', 0)), 0.0, 100.0)
     size_jitter = np.clip(float(brush_params.get('size_jitter', 0)), 0.0, 100.0)
     angle_jitter_degrees = np.clip(float(brush_params.get('angle_jitter', 0)), 0.0, 180.0)

     angle_mode = brush_params.get('angle_mode', 'Direction')
     fixed_angle_degrees = float(brush_params.get('fixed_angle', 0))

     # --- Apply Jitter ---
     size_variation_factor = (size_jitter / 100.0) * 0.75
     current_brush_size = base_brush_size * (1.0 + random.uniform(-size_variation_factor, size_variation_factor))
     current_brush_size = max(1, int(current_brush_size))
     current_brush_radius = current_brush_size // 2

     pos_variation_dist_max = (pos_jitter / 100.0) * base_brush_size
     if pos_variation_dist_max > 0:
         random_offset_dist = random.uniform(0, pos_variation_dist_max)
         random_offset_angle = random.uniform(0, 2 * math.pi)
         offset_x = random_offset_dist * math.cos(random_offset_angle)
         offset_y = random_offset_dist * math.sin(random_offset_angle)
     else:
         offset_x, offset_y = 0, 0

     stamp_center_local_x = int(center_local.x() + offset_x)
     stamp_center_local_y = int(center_local.y() + offset_y)
     stamp_center_local = QPoint(stamp_center_local_x, stamp_center_local_y)

     current_angle_degrees = 0.0
     if angle_mode == 'Direction':
          if stamp_segment_angle_rad is not None:
             current_angle_degrees = math.degrees(stamp_segment_angle_rad)
     elif angle_mode == 'Fixed':
          current_angle_degrees = fixed_angle_degrees
     elif angle_mode == 'Random':
          current_angle_degrees = random.uniform(0, 360)
     elif angle_mode == 'Direction+Jitter':
          if stamp_segment_angle_rad is not None:
              current_angle_degrees = math.degrees(stamp_segment_angle_rad)
          current_angle_degrees += random.uniform(-angle_jitter_degrees, angle_jitter_degrees)
     elif angle_mode == 'Fixed+Jitter':
          current_angle_degrees = fixed_angle_degrees
          current_angle_degrees += random.uniform(-angle_jitter_degrees, angle_jitter_degrees)
     current_angle_degrees = current_angle_degrees % 360.0

     # --- Get and Transform Brush Shape ---
     brush_mask_size = current_brush_size
     current_stamp_brush_shape_mask = get_scaled_rotated_brush_shape(brush_type, brush_mask_size, current_angle_degrees)

     if current_stamp_brush_shape_mask is None or current_stamp_brush_shape_mask.size == 0 or current_stamp_brush_shape_mask.shape != (brush_mask_size, brush_mask_size):
          return

     # --- Hardness Adjustment ---
     hardness_exponent = 1.0 + (hardness / 100.0) * 2.0
     adjusted_brush_opacity = np.power(current_stamp_brush_shape_mask, hardness_exponent)
     adjusted_brush_opacity = np.clip(adjusted_brush_opacity, 0.0, 1.0)

     # --- Calculate overlap region ---
     # Top-left corner of the brush centered at stamp_center_local
     brush_apply_x_start_local = stamp_center_local.x() - current_brush_radius
     brush_apply_y_start_local = stamp_center_local.y() - current_brush_radius

     slice_overlap_x1 = max(0, brush_apply_x_start_local)
     slice_overlap_y1 = max(0, brush_apply_y_start_local)
     slice_overlap_x2 = min(area_width, brush_apply_x_start_local + current_brush_size)
     slice_overlap_y2 = min(area_height, brush_apply_y_start_local + current_brush_size)

     if slice_overlap_x2 <= slice_overlap_x1 or slice_overlap_y2 <= slice_overlap_y1:
          return

     # Calculate the corresponding slice coordinates within the brush mask
     brush_mask_slice_x1 = slice_overlap_x1 - brush_apply_x_start_local
     brush_mask_slice_y1 = slice_overlap_y1 - brush_apply_y_start_local
     brush_mask_slice_x2 = brush_mask_slice_x1 + (slice_overlap_x2 - slice_overlap_x1)
     brush_mask_slice_y2 = brush_mask_slice_y1 + (slice_overlap_y2 - slice_overlap_y1)

     current_local_area_overlap_slice = local_area_uint8[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2] # HxWx3 BGR uint8
     brush_slice_opacity = adjusted_brush_opacity[brush_mask_slice_y1:brush_mask_slice_y2, brush_mask_slice_x1:brush_mask_slice_x2] # HxW float32
     noise_slice = local_area_noise_texture[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2] # HxW float32

     if brush_slice_opacity.shape != current_local_area_overlap_slice.shape[:2] or noise_slice.shape != current_local_area_overlap_slice.shape[:2]:
          print(f"Critical Slicing Error: Shape mismatch! Skipping stamp.")
          return

     # --- Calculate Effective Per-Pixel Opacity ---
     # Base opacity from Density and Flow
     base_stamp_opacity = (density / 100.0) * (flow / 100.0)
     base_stamp_opacity = np.clip(base_stamp_opacity, 0.0, 1.0)

     # Feibai effect based on noise
     feibai_modifier = 1.0
     if feibai > 0:
         feibai_effect = (feibai / 100.0) * (1.0 - noise_slice)
         feibai_modifier = 1.0 - feibai_effect
         feibai_modifier = np.clip(feibai_modifier, 0.0, 1.0)

     # Combine all opacity factors: Base * BrushShape * Feibai
     effective_pixel_opacity_hw = base_stamp_opacity * brush_slice_opacity * feibai_modifier
     effective_pixel_opacity_hw = np.clip(effective_pixel_opacity_hw, 0.0, 1.0) # HxW float32

     # Expand opacity mask to 3 channels for blending with BGR data
     effective_pixel_opacity_hwd = effective_pixel_opacity_hw[:, :, None] # HxWx1 float32

     # --- Blend new ink onto the canvas slice ---
     canvas_slice_float = current_local_area_overlap_slice.astype(np.float32) # HxWx3 float32

     if not is_eraser:
         # Ink blending: Blend brush color with paper color (white 255,255,255) based on stamp opacity.
         # Then, blend that result with the existing canvas pixel using np.minimum.
         # Paper color is (255, 255, 255)
         paper_color = np.array([255, 255, 255], dtype=np.float32)
         brush_color_bgr_float = np.array(brush_color_bgr, dtype=np.float32)

         # Calculated color applied by the stamp at this pixel (blending brush color and paper color based on opacity)
         stamp_applied_color = (1.0 - effective_pixel_opacity_hwd) * paper_color[None, None, :] + effective_pixel_opacity_hwd * brush_color_bgr_float[None, None, :] # HxWx3 float32

         # Blend the stamp_applied_color result with the existing canvas pixel using np.minimum
         # This simulates ink darkening effect and mixing without brightening
         blended_slice_float = np.minimum(canvas_slice_float, stamp_applied_color)

     else:
         # Eraser blending: Blend white (255, 255, 255) with existing canvas pixel based on stamp opacity
         white_color = np.array([255, 255, 255], dtype=np.float32)
         blended_slice_float = (1.0 - effective_pixel_opacity_hwd) * canvas_slice_float + effective_pixel_opacity_hwd * white_color[None, None, :] # HxWx3 float32

     blended_slice_float = np.clip(blended_slice_float, 0.0, 255.0)

     current_local_area_overlap_slice[:] = blended_slice_float.astype(np.uint8)

def apply_basic_brush_stroke_segment(
    lienzo: Lienzo, # Lienzo now manages HxWx3 Data
    p1_canvas: QPoint,
    p2_canvas: QPoint,
    brush_params: dict # Contains color key 'color': (B,G,R) tuple
) -> QRect:
    """Applies ink for a segment to the Lienzo, returns directly affected canvas area."""
    if lienzo is None: return QRect()
    canvas_width, canvas_height = lienzo.get_size()
    if canvas_width <= 0 or canvas_height <= 0: return QRect()

    base_brush_size = max(1, int(brush_params.get('size', 15)))
    brush_radius = base_brush_size // 2

    pos_jitter = np.clip(float(brush_params.get('pos_jitter', 0)), 0.0, 100.0)
    size_jitter = np.clip(float(brush_params.get('size_jitter', 0)), 0.0, 100.0)

    dx_canvas = p2_canvas.x() - p1_canvas.x()
    dy_canvas = p2_canvas.y() - p1_canvas.y()
    dist_canvas = math.sqrt(dx_canvas**2 + dy_canvas**2)

    # --- Calculate number of stamps/interpolation steps based on desired stamp spacing ---
    # Stamps should be spaced by a fraction of the brush size to ensure continuity.
    # A common value is spacing = brush_size / 4.
    # Use a minimum spacing of 1 pixel on the canvas.
    stamp_spacing = max(1.0, base_brush_size / 4.0)

    # Number of intervals = Total Distance / Spacing. Number of stamps = Number of intervals + 1.
    num_interpolation_steps = max(1, int(dist_canvas / stamp_spacing))

    segment_angle_rad = None
    if dx_canvas != 0 or dy_canvas != 0:
         segment_angle_rad = math.atan2(dy_canvas, dx_canvas)

    # --- Calculate required processing area covering segment endpoints and max potential stamp influence ---
    max_size_variation_factor = (size_jitter / 100.0) * 0.75
    max_possible_stamp_size = base_brush_size * (1.0 + max_size_variation_factor)
    max_possible_stamp_radius = max(max_possible_stamp_size, 1.0) / 2.0

    max_pos_jitter_offset = (pos_jitter / 100.0) * base_brush_size

    buffer_radius = int(max_possible_stamp_radius + max_pos_jitter_offset)
    buffer_radius = max(buffer_radius, base_brush_size) # Ensure buffer is at least base brush size for safety

    min_x_pt = min(p1_canvas.x(), p2_canvas.x())
    max_x_pt = max(p1_canvas.x(), p2_canvas.x())
    min_y_pt = min(p1_canvas.y(), p2_canvas.y())
    max_y_pt = max(p1_canvas.y(), p2_canvas.y())

    process_x1 = min_x_pt - buffer_radius
    process_y1 = min_y_pt - buffer_radius

    process_x2_incl = max_x_pt + buffer_radius
    process_y2_incl = max_y_pt + buffer_radius

    process_x2_excl = process_x2_incl + 1
    process_y2_excl = process_y2_incl + 1

    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2_excl = min(canvas_width, process_x2_excl)
    process_y2_excl = min(canvas_height, process_y2_excl)

    process_w = max(0, process_x2_excl - process_x1)
    process_h = max(0, process_y2_excl - process_y1)

    process_rect_canvas = QRect(process_x1, process_y1, process_w, process_h)

    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        return QRect()

    try:
        local_canvas_area = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height())) # This should return HxWx3
        # Lienzo.crop_area already returns a copy
        if local_canvas_area is None or local_canvas_area.size == 0: # Check .size for empty array
             print("Warning: Cropping area failed or returned empty.")
             return QRect()
        if local_canvas_area.shape[:2] != (process_rect_canvas.height(), process_rect_canvas.width()) or local_canvas_area.shape[2] != 3: # Check shape HxWx3
             print(f"FATAL ERROR: Cropped area shape mismatch or invalid channels! Expected ({process_rect_canvas.height(), process_rect_canvas.width(), 3}), got {local_canvas_area.shape}. Skipping ink application.")
             return QRect()
    except Exception as e:
        print(f"Error cropping Lienzo for segment: {e}. Skipping ink application.")
        return QRect()

    try:
        # Noise texture is still grayscale HxW for feibai calculation
        area_height, area_width = local_canvas_area.shape[:2]
        noise_texture_area = np.random.rand(area_height, area_width).astype(np.float32)
    except Exception as e:
         print(f"Error generating noise texture: {e}.")
         noise_texture_area = np.ones(local_canvas_area.shape[:2], dtype=np.float32) * 0.5

    # Points relative to the local area origin (inclusive start)
    p1_local = QPoint(p1_canvas.x() - process_x1, p1_canvas.y() - process_y1)
    p2_local = QPoint(p2_canvas.x() - process_x1, p2_canvas.y() - process_y1)

    # --- Apply stamps along the interpolated path ---
    # Use linspace to get points including start and end, ensure correct number of points
    # Need num_interpolation_steps + 1 points for num_interpolation_steps intervals
    num_points_to_interpolate = num_interpolation_steps + 1
    # Use float coordinates for linspace
    interpolated_points = np.linspace([p1_local.x(), p1_local.y()], [p2_local.x(), p2_local.y()], num_points_to_interpolate)

    for point_coords in interpolated_points:
        # Convert float interpolated coords back to nearest integer pixel point for stamp center
        stamp_center_local = QPoint(int(round(point_coords[0])), int(round(point_coords[1])))

        # Apply a single brush stamp at this interpolated point
        try:
            _apply_single_brush_stamp(
                local_canvas_area, # Pass the local HxWx3 array
                stamp_center_local,
                brush_params, # Contains color and all other params
                noise_texture_area, # Still HxW noise
                segment_angle_rad
            )
        except Exception as e:
             print(f"Error applying single stamp at ({stamp_center_local.x()},{stamp_center_local.y()} relative): {e}.")

    # --- Paste the modified local area back onto the Lienzo ---
    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    # Shape consistency checked inside paste_area
    try:
        lienzo.paste_area(paste_rect_tuple, local_canvas_area) # Paste the modified HxWx3 array
        return process_rect_canvas
    except Exception as e:
        print(f"Error pasting modified area: {e}. Skipping paste.")
        return QRect()

def finalize_stroke(
    lienzo: Lienzo,
    stroke_inked_region_canvas: QRect,
    brush_params: dict # Contains wetness, size, etc.
) -> QRect:
    """Finalizes a stroke by applying localized diffusion (blur) for ink, doing nothing for eraser."""
    is_eraser = brush_params.get('is_eraser', False)

    if is_eraser:
         canvas_width, canvas_height = lienzo.get_size()
         if canvas_width <= 0 or canvas_height <= 0: return QRect()
         clamped_rect = stroke_inked_region_canvas.intersected(QRect(0, 0, canvas_width, canvas_height))
         return clamped_rect.normalized()

    else:
         final_updated_area_canvas = apply_localized_blur(
            lienzo, # Lienzo has HxWx3 Data
            stroke_inked_region_canvas,
            brush_params.get('wetness', 70),
            brush_params.get('size', 15) # Base size needed for blur radius estimate
        )
         return final_updated_area_canvas

def apply_localized_blur(
    lienzo: Lienzo, # Lienzo has HxWx3 Data
    canvas_rect_to_blur: QRect,
    wetness: int,
    brush_size: int # Base size needed for blur radius
) -> QRect:
    """Applies localized diffusion (Bilateral Filter) to a region, blends, and pastes."""
    if lienzo is None or canvas_rect_to_blur.isNull() or wetness <= 0 or canvas_rect_to_blur.width() <= 0 or canvas_rect_to_blur.height() <= 0:
        return QRect() # Return empty if wetness is 0

    canvas_height, canvas_width = lienzo.get_size()
    if canvas_height <= 0 or canvas_width <= 0: return QRect()

    brush_size = max(1, int(brush_size))
    wetness = np.clip(int(wetness), 0, 100)

    base_sigma_space = wetness / 100.0 * 20.0 # Maps wetness [0,100] to spatial sigma [0, 20]
    base_sigma_space = max(1.0, base_sigma_space) # Min spatial sigma for effect

    estimated_blur_radius_for_expansion = int(base_sigma_space * 3.0)
    estimated_blur_radius_for_expansion = max(estimated_blur_radius_for_expansion, brush_size * 2) # Use brush size related buffer
    estimated_blur_radius_for_expansion = max(estimated_blur_radius_for_expansion, 15) # Minimum buffer

    process_x1 = canvas_rect_to_blur.left() - estimated_blur_radius_for_expansion
    process_y1 = canvas_rect_to_blur.top() - estimated_blur_radius_for_expansion

    process_x2_incl = canvas_rect_to_blur.right() + estimated_blur_radius_for_expansion -1
    process_y2_incl = canvas_rect_to_blur.bottom() + estimated_blur_radius_for_expansion -1

    process_x2_excl = process_x2_incl + 1
    process_y2_excl = process_y2_incl + 1

    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2_excl = min(canvas_width, process_x2_excl)
    process_y2_excl = min(canvas_height, process_y2_excl)

    process_w = max(0, process_x2_excl - process_x1)
    process_h = max(0, process_y2_excl - process_y1)

    process_rect_canvas = QRect(process_x1, process_y1, process_w, process_h)

    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        return QRect()

    try:
        # Crop area using the calculated exclusive rectangle. Should return HxWx3.
        processing_area_bgr = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height()))

        if processing_area_bgr is None or processing_area_bgr.size == 0:
             print("Warning: Cropping area for blur failed or returned empty.")
             return QRect()
        if processing_area_bgr.shape[:2] != (process_rect_canvas.height(), process_rect_canvas.width()) or processing_area_bgr.shape[2] != 3:
             print(f"FATAL ERROR: Cropped area for blur shape mismatch or invalid channels! Expected ({process_rect_canvas.height(), process_rect_canvas.width(), 3}), got {processing_area_bgr.shape}. Skipping blur.")
             return QRect()

    except Exception as e:
        print(f"Error cropping Lienzo for blur: {e}. Skipping blur.")
        return QRect()

    original_processing_area_bgr = processing_area_bgr.copy() # Keep a copy of the original BGR area before blurring

    # sigmaColor: Color distance tolerance for BilateralFilter. Higher wetness -> Higher tolerance -> blur spreads across color differences.
    sigma_color = wetness / 100.0 * 150.0
    sigma_color = max(1.0, sigma_color)

    try:
        # Apply cv2.bilateralFilter to the BGR image data
        processed_area_blurred_bgr = cv2.bilateralFilter(processing_area_bgr, 0, float(sigma_color), float(base_sigma_space))
    except Exception as e:
         print(f"Error during cv2.bilateralFilter: {e}. Skipping blur.")
         # Even if blur fails, try to paste the original cropped area back? Or just indicate failure.
         # Let's just indicate failure for blur step.
         return QRect()

    # --- Intelligent Blending for Color ---
    # For colored ink diffusion, a simple np.minimum on BGR channels might cause color shifts.
    # A more complex approach might involve blurring luminance and blending based on that,
    # or blurring each channel independently and blending based on some ink model.
    # However, for a basic version, minimum blending on BGR channels simulates each color channel
    # getting darker independently, which is a possible behavior for some pigment mixes.
    # Let's use np.minimum as a starting point and see if it looks acceptable.

    # Blend the blurred BGR result with the original BGR area (before blur) using np.minimum channel-wise.
    blended_area_bgr = np.minimum(original_processing_area_bgr, processed_area_blurred_bgr)

    # --- Paste the blended BGR area back onto the Lienzo ---
    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    try:
        lienzo.paste_area(paste_rect_tuple, blended_area_bgr) # Paste the modified HxWx3 array
        return process_rect_canvas
    except Exception as e:
        print(f"Error pasting blended area: {e}. Skipping paste.")
        return QRect()

load_brush_shapes()