# processing/brush_engine.py

import numpy as np
import cv2
from PyQt5.QtCore import QPoint, QRect
import math
import random
import os
# Added missing import:
from processing.lienzo import Lienzo

_brush_shapes = {}
_brush_shape_folder = os.path.join(os.path.dirname(__file__), '..', 'resources')

def load_brush_shapes():
    """Loads brush shape images."""
    global _brush_shapes
    global _brush_shape_folder

    shape_files = {
        'round': 'brush_round.png',
        'flat': 'brush_flat.png',
    }

    if not os.path.exists(_brush_shape_folder):
         print(f"Warning: Resources folder not found at {_brush_shape_folder}. Cannot load brush shapes.")
         for name in shape_files.keys():
              _brush_shapes[name] = None
    else:
        for name, filename in shape_files.items():
            filepath = os.path.join(_brush_shape_folder, filename)
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
    """Returns a list of names of successfully loaded or synthesized brush types."""
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

def _apply_ink_to_local_area(
    local_area_uint8: np.ndarray,
    p1_local: QPoint,
    p2_local: QPoint,
    brush_params: dict,
    area_noise_texture: np.ndarray
):
     """Applies ink effects (density, feibai, brush shape) to a local uint8 canvas area."""
     if local_area_uint8 is None or local_area_uint8.size == 0: return
     area_height, area_width = local_area_uint8.shape[:2]
     if area_width <= 0 or area_height <= 0: return

     is_eraser = brush_params.get('is_eraser', False)

     if area_noise_texture is None or area_noise_texture.shape != local_area_uint8.shape:
          print("Error: Noise texture slice has wrong shape or is None. Feibai might not apply correctly.")
          area_noise_texture = np.ones_like(local_area_uint8, dtype=np.float32) * 0.5

     brush_size = max(1, int(brush_params.get('size', 15)))
     # Density controls opacity for both ink and eraser
     density = np.clip(float(brush_params.get('density', 60)), 0.0, 100.0)
     # Feibai applies to both ink and eraser
     feibai = np.clip(float(brush_params.get('feibai', 20)), 0.0, 100.0)
     brush_type = brush_params.get('type', 'round')

     brush_radius = brush_size // 2

     dx_local = p2_local.x() - p1_local.x()
     dy_local = p2_local.y() - p1_local.y()
     angle_degrees = 0.0
     if dx_local != 0 or dy_local != 0:
          angle_rad = math.atan2(dy_local, dx_local)
          angle_degrees = math.degrees(angle_rad)

     dist_local = math.sqrt(dx_local**2 + dy_local**2)
     num_steps = max(int(dist_local), 1)

     for i in range(num_steps + 1):
         t = float(i) / num_steps if num_steps > 0 else 0.0

         px_rel = int(p1_local.x() + t * dx_local)
         py_rel = int(p1_local.y() + t * dy_local)

         if not (0 <= px_rel < area_width and 0 <= py_rel < area_height):
              continue

         brush_mask_size = brush_size
         current_point_brush_shape_mask = get_scaled_rotated_brush_shape(brush_type, brush_mask_size, angle_degrees)

         if current_point_brush_shape_mask is None or current_point_brush_shape_mask.size == 0 or current_point_brush_shape_mask.shape != (brush_mask_size, brush_mask_size):
              continue

         brush_apply_x_start_rel = px_rel - brush_radius
         brush_apply_y_start_rel = py_rel - brush_radius

         slice_overlap_x1 = max(0, brush_apply_x_start_rel)
         slice_overlap_y1 = max(0, brush_apply_y_start_rel)
         slice_overlap_x2 = min(area_width, brush_apply_x_start_rel + brush_size)
         slice_overlap_y2 = min(area_height, brush_apply_y_start_rel + brush_size)

         if slice_overlap_x2 <= slice_overlap_x1 or slice_overlap_y2 <= slice_overlap_y1:
              continue

         brush_mask_slice_x1 = slice_overlap_x1 - brush_apply_x_start_rel
         brush_mask_slice_y1 = slice_overlap_y1 - brush_apply_y_start_rel
         brush_mask_slice_x2 = brush_mask_slice_x1 + (slice_overlap_x2 - slice_overlap_x1)
         brush_mask_slice_y2 = brush_mask_slice_y1 + (slice_overlap_y2 - slice_overlap_y1)

         current_local_area_overlap_slice = local_area_uint8[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2]
         brush_slice_opacity = current_point_brush_shape_mask[brush_mask_slice_y1:brush_mask_slice_y2, brush_mask_slice_x1:brush_mask_slice_x2]
         noise_slice = area_noise_texture[slice_overlap_y1:slice_overlap_y2, slice_overlap_x1:slice_overlap_x2]

         if current_local_area_overlap_slice.shape != brush_slice_opacity.shape or current_local_area_overlap_slice.shape != noise_slice.shape:
              print(f"Critical Slicing Error: Shape mismatch! Local:{current_local_area_overlap_slice.shape}, Brush:{brush_slice_opacity.shape}, Noise:{noise_slice.shape}. Skipping point.")
              continue

         base_density_opacity = density / 100.0
         feibai_modifier = 1.0
         if feibai > 0 and noise_slice is not None and noise_slice.shape == brush_slice_opacity.shape:
             feibai_modifier = 1.0 - (feibai / 100.0) * (1.0 - noise_slice)
             feibai_modifier = np.clip(feibai_modifier, 0.0, 1.0)

         effective_pixel_opacity = base_density_opacity * brush_slice_opacity * feibai_modifier
         effective_pixel_opacity = np.clip(effective_pixel_opacity, 0.0, 1.0)

         canvas_slice_float = current_local_area_overlap_slice.astype(np.float32)

         if not is_eraser:
             # Apply ink (darken towards 0)
             target_shade_float = 255.0 * (1.0 - effective_pixel_opacity)
             blended_slice_float = np.minimum(canvas_slice_float, target_shade_float)
         else:
             # Apply eraser (lighten towards 255)
             # Target shade for eraser is 255 (white). Opacity means how much of 255 is applied.
             # Standard alpha blending formula: result = (1-alpha)*foreground + alpha*background
             # Here: result = (1 - effective_opacity) * existing_canvas + effective_opacity * 255
             # Use float arithmetic for blending
             blended_slice_float = (1.0 - effective_pixel_opacity) * canvas_slice_float + effective_pixel_opacity * 255.0
             blended_slice_float = np.clip(blended_slice_float, 0.0, 255.0) # Ensure values are in range

         current_local_area_overlap_slice[:] = blended_slice_float.astype(np.uint8)

def apply_basic_brush_stroke_segment(
    lienzo: Lienzo,
    p1_canvas: QPoint,
    p2_canvas: QPoint,
    brush_params: dict
) -> QRect:
    """Applies ink for a segment to the Lienzo, returns directly affected canvas area."""
    if lienzo is None: return QRect()
    canvas_width, canvas_height = lienzo.get_size()
    if canvas_width <= 0 or canvas_height <= 0: return QRect()

    brush_size = max(1, int(brush_params.get('size', 15)))
    brush_radius = brush_size // 2

    min_x = min(p1_canvas.x(), p2_canvas.x())
    max_x = max(p1_canvas.x(), p2_canvas.x())
    min_y = min(p1_canvas.y(), p2_canvas.y())
    max_y = max(p1_canvas.y(), p2_canvas.y())

    process_x1 = min_x - brush_radius
    process_y1 = min_y - brush_radius
    process_x2_idx = max_x + brush_radius
    process_y2_idx = max_y + brush_radius

    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2_idx = min(canvas_width - 1, process_x2_idx)
    process_y2_idx = min(canvas_height - 1, process_y2_idx)

    process_w = max(0, process_x2_idx - process_x1 + 1)
    process_h = max(0, process_y2_idx - process_y1 + 1)

    process_rect_canvas = QRect(process_x1, process_y1, process_w, process_h)

    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        return QRect()

    try:
        local_canvas_area_uint8 = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height()))
        if local_canvas_area_uint8 is None or local_canvas_area_uint8.size == 0:
             print("Warning: Cropping area failed or returned empty.")
             return QRect()
    except Exception as e:
        print(f"Error cropping Lienzo for segment: {e}. Skipping ink application.")
        return QRect()

    try:
        area_height, area_width = local_canvas_area_uint8.shape[:2]
        noise_texture_area = np.random.rand(area_height, area_width).astype(np.float32)
    except Exception as e:
         print(f"Error generating noise texture: {e}. Proceeding without feibai texture.")
         noise_texture_area = np.ones_like(local_canvas_area_uint8, dtype=np.float32) * 0.5

    p1_local = QPoint(p1_canvas.x() - process_rect_canvas.x(), p1_canvas.y() - process_rect_canvas.y())
    p2_local = QPoint(p2_canvas.x() - process_rect_canvas.x(), p2_canvas.y() - process_rect_canvas.y())

    try:
        _apply_ink_to_local_area(
            local_canvas_area_uint8,
            p1_local,
            p2_local,
            brush_params,
            noise_texture_area
        )
    except Exception as e:
         print(f"Error applying ink effects to local area: {e}.")
         return QRect()

    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    if local_canvas_area_uint8.shape == (process_rect_canvas.height(), process_rect_canvas.width()):
         try:
             lienzo.paste_area(paste_rect_tuple, local_canvas_area_uint8)
             return process_rect_canvas
         except Exception as e:
             print(f"Error pasting modified area: {e}. Skipping paste.")
             return QRect()
    else:
        print(f"Warning: Modified local area shape mismatch {local_canvas_area_uint8.shape} vs paste rect shape {(process_rect_canvas.height(), process_rect_canvas.width())}. Skipping paste.")
        return QRect()

def finalize_stroke(
    lienzo: Lienzo,
    stroke_inked_region_canvas: QRect,
    brush_params: dict
) -> QRect:
    """Finalizes a stroke by applying localized diffusion (blur)."""
    is_eraser = brush_params.get('is_eraser', False)

    if is_eraser:
         # Eraser strokes do not get diffusion
         # The relevant area for updating the UI is just the inked region itself now
         return stroke_inked_region_canvas.normalized()
    else:
         # Ink strokes get diffusion
         final_updated_area_canvas = apply_localized_blur(
            lienzo,
            stroke_inked_region_canvas,
            brush_params.get('wetness', 70),
            brush_params.get('size', 15)
        )
         return final_updated_area_canvas

def apply_localized_blur(
    lienzo: Lienzo,
    canvas_rect_to_blur: QRect,
    wetness: int,
    brush_size: int
) -> QRect:
    """Applies localized diffusion (Bilateral Filter) to a region, blends, and pastes."""
    if lienzo is None or canvas_rect_to_blur.isNull() or wetness <= 0 or canvas_rect_to_blur.width() <= 0 or canvas_rect_to_blur.height() <= 0:
        return QRect()

    canvas_height, canvas_width = lienzo.get_size()
    if canvas_height <= 0 or canvas_width <= 0: return QRect()

    brush_size = max(1, int(brush_size))
    wetness = np.clip(int(wetness), 0, 100)

    base_sigma_space = wetness / 100.0 * 20.0
    base_sigma_space = max(1.0, base_sigma_space)

    estimated_blur_radius = int(base_sigma_space * 3.0)
    estimated_blur_radius = max(estimated_blur_radius, brush_size // 2)
    estimated_blur_radius = max(estimated_blur_radius, 5)

    process_x1 = canvas_rect_to_blur.left() - estimated_blur_radius
    process_y1 = canvas_rect_to_blur.top() - estimated_blur_radius
    process_x2_idx = canvas_rect_to_blur.right() + estimated_blur_radius -1
    process_y2_idx = canvas_rect_to_blur.bottom() + estimated_blur_radius -1

    process_x1 = max(0, process_x1)
    process_y1 = max(0, process_y1)
    process_x2_idx = min(canvas_width - 1, process_x2_idx)
    process_y2_idx = min(canvas_height - 1, process_y2_idx)

    process_w = max(0, process_x2_idx - process_x1 + 1)
    process_h = max(0, process_y2_idx - process_y1 + 1)

    process_rect_canvas = QRect(process_x1, process_y1, process_w, process_h)

    if process_rect_canvas.width() <= 0 or process_rect_canvas.height() <= 0:
        return QRect()

    try:
        processing_area_uint8 = lienzo.crop_area((process_rect_canvas.x(), process_rect_canvas.y(),
                                                  process_rect_canvas.width(), process_rect_canvas.height()))
        if processing_area_uint8 is None or processing_area_uint8.size == 0:
             print("Warning: Cropping area for blur failed or returned empty.")
             return QRect()
    except Exception as e:
        print(f"Error cropping Lienzo for blur: {e}. Skipping blur.")
        return QRect()

    original_processing_area_uint8 = processing_area_uint8.copy()

    sigma_color = wetness / 100.0 * 150.0
    sigma_color = max(1.0, sigma_color)

    try:
        processed_area_blurred = cv2.bilateralFilter(processing_area_uint8, 0, float(sigma_color), float(base_sigma_space))
    except Exception as e:
         print(f"Error during cv2.bilateralFilter: {e}. Skipping blur.")
         return QRect()

    blended_area_uint8 = np.minimum(original_processing_area_uint8, processed_area_blurred)

    paste_rect_tuple = (process_rect_canvas.x(), process_rect_canvas.y(),
                        process_rect_canvas.width(), process_rect_canvas.height())

    if blended_area_uint8.shape == (process_rect_canvas.height(), process_rect_canvas.width()):
         try:
             lienzo.paste_area(paste_rect_tuple, blended_area_uint8)
             return process_rect_canvas
         except Exception as e:
             print(f"Error pasting blended area: {e}. Skipping paste.")
             return QRect()
    else:
        print(f"Warning: Blended area shape mismatch {blended_area_uint8.shape} vs paste rect shape {(process_rect_canvas.height(), process_rect_canvas.width())}. Skipping paste.")
        return QRect()

load_brush_shapes()