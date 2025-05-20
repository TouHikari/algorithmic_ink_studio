# gui/ink_canvas_widget.py (Basic Brush API Interaction)

from PyQt5.QtWidgets import QWidget, QSizePolicy, QMessageBox # Added QMessageBox for error display
from PyQt5.QtGui import QPainter, QPixmap, QMouseEvent, QPaintEvent, QColor, QImage
from PyQt5.QtCore import Qt, QRectF, QPoint, QRect, QSize, pyqtSignal # Ensure pyqtSignal is imported

import numpy as np
import cv2 # Need cv2 for image operations if any are performed here (e.g. resize in load_image)

# Import processing modules
from processing.utils import convert_cv_to_qt
# Import brush engine functions - use the simpler ones
# Ensure these import directly usable functions defined in brush_engine.py
# apply_basic_brush_stroke_segment takes Lienzo, p1, p2, params and returns inked rect (QRect)
# finalize_stroke takes Lienzo, accumulated_inked_rect (QRect), params and returns updated_rect (QRect)
from processing.brush_engine import apply_basic_brush_stroke_segment, finalize_stroke

from processing.lienzo import Lienzo # Import Lienzo class

class InkCanvasWidget(QWidget):
    # Signal to indicate that the canvas content might have changed significantly (e.g., after image load/processing)
    canvas_content_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lienzo: Lienzo = None # Holds the reference to the Lienzo instance managed by MainWindow

        self._is_drawing = False # Flag to track if a mouse press has started a stroke
        self._last_point_widget: QPoint = None # Tracks the last mouse position in widget coordinates during drawing

        # Default brush parameters (should ideally be synced or initialized from ControlPanel defaults)
        # Ensure default type is 'round' to match simple brush shape loading/fallback
        self._current_brush_params = {
            'size': 40,          # Brush size (pixels)
            'density': 60,       # Ink density (0-100)
            'wetness': 0,        # Wetness/Diffusion amount (0-100)
            'feibai': 20,        # Feibai amount (0-100)
            'type': 'round' # Brush type (must match keys in brush_engine._brush_shapes)
        }

        # Remove _current_mode as there is only one mode now in MainWindow (implicit free drawing)
        # self._current_mode = "free_drawing" # REMOVED

        # === Variables for managing the current stroke's state ===
        # In this basic version, we only need to track the union of areas where ink was applied
        # during the stroke, before applying final blur.
        self._stroke_inked_region_canvas: QRect = QRect() # Accumulates the union of ink application rects (canvas coords)
        # The complex {'ink_layer': np.ndarray float32, 'rect_canvas': QRect} state dictionary is removed in this version.
        # self._current_stroke_state = {} # REMOVED

        # Set size policy to allow expanding
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Enable mouse tracking for real-time drawing feedback even if button is not pressed (e.g., cursor preview)
        # Always enable mouse tracking since the main window implicitly sets free drawing mode.
        self.setMouseTracking(True)

    def set_lienzo(self, lienzo_instance: Lienzo):
        """Sets the Lienzo canvas instance to be displayed and manipulated."""
        self._lienzo = lienzo_instance
        # Request a full repaint when the lienzo instance is set or replaced
        self.update()
        # Emit signal if needed externally (e.g., to update status bar with canvas size)
        self.canvas_content_changed.emit()
        # print("InkCanvasWidget set Lienzo instance.")

    def get_lienzo(self) -> Lienzo:
        """Returns the current Lienzo canvas instance."""
        return self._lienzo

    def set_brush_params(self, params: dict):
        """Updates the current brush parameters dictionary."""
        # Only update parameters that are provided in the dictionary
        self._current_brush_params.update(params)
        # print(f"Brush parameters updated: {self._current_brush_params}")

    # Remove set_current_mode as there is only one mode (implicitly free drawing via MainWindow)
    # The MainWindow handles setting setMouseTracking(True) when starting the app.
    # def set_current_mode(self, mode: str): pass # REMOVED

    def paintEvent(self, event: QPaintEvent):
         """Qt调用此方法来绘制Widget的内容."""
         painter = QPainter(self)
         # Optional: Enable anti-aliasing if drawing real-time brush preview shape with QPainter on the widget overlay
         # painter.setRenderHint(QPainter.Antialiasing, True)

         # Check if Lienzo is valid and has data to draw
         if self._lienzo is None or self._lienzo.get_canvas_data().size == 0:
             painter.fillRect(event.rect(), Qt.white) # Draw white background
             painter.drawText(event.rect(), Qt.AlignCenter, "等待加载画布或图片...")
             painter.end() # Ensure painter is ended
             return

         canvas_data = self._lienzo.get_canvas_data()
         canvas_width, canvas_height = self._lienzo.get_size()
         widget_width, widget_height = self.width(), self.height()

         # Validate widget and canvas sizes before proceeding
         if canvas_width <= 0 or canvas_height <= 0 or widget_width <= 0 or widget_height <= 0:
              painter.fillRect(event.rect(), Qt.white) # Draw white if sizes are invalid
              painter.end() # Ensure painter is ended
              return

         # Convert the grayscale NumPy array from Lienzo to a QImage/QPixmap for display
         # Getting the full canvas data and converting is simpler for now:
         canvas_data_contiguous = np.ascontiguousarray(canvas_data) # Ensure QImage needs contiguous data
         # For Grayscale8 format, bytesPerLine is width
         qt_image = QImage(canvas_data_contiguous.data, canvas_width, canvas_height, canvas_width, QImage.Format_Grayscale8)
         pixmap = QPixmap.fromImage(qt_image)

         # Calculate how to draw the pixmap onto the widget, considering scaling
         # The target rectangle on the widget is the event.rect() (the dirty area Qt wants to repaint)
         dirty_widget_rect = event.rect()

         # The corresponding source rectangle on the canvas (pixmap) is the event.rect() mapped to canvas coordinates
         canvas_dirty_rect = self._widget_to_canvas_rect(dirty_widget_rect) # Using a helper method for rect mapping

         # Draw the corresponding part of the pixmap onto the widget's dirty area
         # painter.drawPixmap(target_rect, source_pixmap, source_rect)
         # target_rect is the area on the widget (dirty_widget_rect)
         # source_pixmap is the full pixmap representing the lienzo
         # source_rect is the area on the pixmap/canvas corresponding to the widget's dirty area (canvas_dirty_rect)
         # Ensure the source rectangle is valid and intersects the pixmap's bounds
         canvas_pixmap_rect = pixmap.rect()
         if canvas_dirty_rect.isValid() and canvas_pixmap_rect.intersects(canvas_dirty_rect):
              painter.drawPixmap(dirty_widget_rect, pixmap, canvas_dirty_rect)
         else:
             # Fallback: draw the full pixmap scaled to the entire widget rect if the mapped dirty rect is invalid for drawing
             # This is less efficient but ensures something is drawn.
             painter.drawPixmap(self.rect(), pixmap, pixmap.rect())

        # TODO: If implementing real-time brush preview (cursor feedback), draw it here in paintEvent,
        # using QPainter directly on the widget overlaying the background image.
        # This drawing should be based on the current brush size and shape, and mouse position (event.pos()).
        # Avoid expensive image processing here. Just draw a simple shape outline.

        # painter.end() # QPainter is automatically ended when it goes out of scope (at end of function)

    # --- Mouse Event Handlers ---
    # These handlers capture mouse input and call the brush engine to apply ink (immediately)
    # and accumulate the inked region, then trigger final blur on release.

    def mousePressEvent(self, event: QMouseEvent):
        # Only handle left mouse button press to start a drawing stroke
        # Check if we are in drawing mode (Implicitly, this widget is for drawing mode)
        # Re-adding an explicit mode check if MainWindow manages this widget's visibility/activity
        # if not MainWindow sets MouseTracking based on mode, this check might be necessary.
        # Let's add a simple flag check that MainWindow can set if needed externally.
        # If MainWindow doesn't set a flag, this widget is always "ready" for drawing.
        # Assuming this widget is only active/visible in drawing mode for simplicity in code below.

        if event.button() != Qt.LeftButton or self._lienzo is None:
             # If not handled (e.g., right click), pass the event to the base class
             super().mousePressEvent(event)
             return # Do not handle if not left button or no lienzo

        self._is_drawing = True # Set drawing flag
        self._last_point_widget = event.pos() # Store the starting point in widget coordinates

        # === Initialize state for a new stroke ===
        # For the basic blur version, we only need to track the bounding QRect of all inked areas.
        self._stroke_inked_region_canvas = QRect() # Initialize an empty QRect for the new stroke
        # ====================================================

        # Convert the starting point from widget coordinates to canvas coordinates
        canvas_point = self._widget_to_canvas(self._last_point_widget)

        # Call the basic brush engine function to apply ink for the first segment (a point).
        # This function modifies the Lienzo directly within the inked area.
        # It returns the canvas area (QRect) that was directly inked (before blur).
        try:
            # apply_basic_brush_stroke_segment takes Lienzo, p1, p2, params and returns inked rect (QRect)
            inked_rect_canvas = apply_basic_brush_stroke_segment(
                 self._lienzo, # The Lienzo instance
                 canvas_point, # Start point (canvas coords)
                 canvas_point, # End point (canvas coords) - same as start for first point of a stroke
                 self._current_brush_params # Current brush parameters
            )
        except Exception as e:
             # Catch potential errors during the first segment processing
             print(f"Error in apply_basic_brush_stroke_segment during mousePressEvent: {e}")
             # Stop drawing and clear state to avoid issues
             self._is_drawing = False
             self._last_point_widget = None
             self._stroke_inked_region_canvas = QRect() # Clear accumulated rect
             # It might be good to show an error message to the user via QMessageBox
             QMessageBox.critical(self, "绘画出错", f"处理第一个笔画点时发生错误: {e}")
             # Pass event to base class, stop further handling here
             super().mousePressEvent(event)
             return # Stop processing this event

        # === Accumulate the inked region for this stroke ===
        # Union the inked region returned by the brush engine with the accumulated stroke region.
        # This accumulated region defines the area around which final blur will be applied on release.
        if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
            if self._stroke_inked_region_canvas.isNull():
                self._stroke_inked_region_canvas = inked_rect_canvas # Initialize with the first inked rect
            else:
                self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas) # Union with subsequent inked rects

            # Request repaint for the area directly affected by ink in this first segment.
            # This provides immediate visual feedback (ink appears as drawn).
            # Ensure the returned canvas rectangle is valid before using it for update.
            dirty_widget_rect = self._canvas_to_widget_rect(inked_rect_canvas)
            # Request repaint for the calculated widget area. Add slight margin for safety/visuals with scaling/rounding.
            self.update(dirty_widget_rect.normalized().adjusted(-2, -2, 2, 2)) # Request repaint of this small area

        # Important: Call super() to ensure the event is passed up the hierarchy.
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Only handle mouse move events if drawing is currently in progress (_is_drawing is True)
        # and the left mouse button is held down.
        # Check for valid lienzo and last_point_widget state.
        if not self._is_drawing or self._lienzo is None or self._last_point_widget is None or not (event.buttons() & Qt.LeftButton):
            # If not drawing, but mouse tracking is enabled, this event still fires.
            # Use this for real-time brush cursor feedback if implemented (drawing an outline with QPainter).
            # For now, just pass the event to the base class handler.
            super().mouseMoveEvent(event)
            return

        current_point_widget = event.pos() # Get the current mouse position in widget coordinates

        # Convert current and last recorded point from widget to canvas coordinates
        canvas_last_point = self._widget_to_canvas(self._last_point_widget)
        canvas_current_point = self._widget_to_canvas(current_point_widget)

        # If the mouse hasn't moved to a new unique canvas pixel since the last event,
        # skip processing the brush segment but still update _last_point_widget.
        # This prevents redundant processing when the mouse is held still or moves only slightly.
        if canvas_last_point == canvas_current_point:
             self._last_point_widget = current_point_widget # Always update last point in widget coords
             return # No change on canvas pixel level, skip brush engine update

        # Call the basic brush engine function to apply ink for the segment.
        # This function modifies the Lienzo directly within the inked area.
        # It returns the canvas area (QRect) that was directly inked (before blur).
        try:
            # apply_basic_brush_stroke_segment takes Lienzo, p1, p2, params and returns inked rect (QRect)
            inked_rect_canvas = apply_basic_brush_stroke_segment(
                 self._lienzo, # The Lienzo instance
                 canvas_last_point, # Start point of this segment (canvas coords)
                 canvas_current_point, # End point of this segment (canvas coords)
                 self._current_brush_params # Current brush parameters
            )
        except Exception as e:
             # Catch potential errors during segment processing
             print(f"Error in apply_basic_brush_stroke_segment during mouseMoveEvent: {e}")
             # Stop drawing and clear state to avoid issues
             self._is_drawing = False
             self._last_point_widget = None
             self._stroke_inked_region_canvas = QRect() # Clear accumulated rect
             # Optionally show an error message
             # QMessageBox.critical(self, "绘画出错", f"处理笔画片段时发生错误: {e}")
             super().mouseMoveEvent(event) # Pass event
             return # Stop processing this event

        # === Accumulate the inked region for this stroke ===
        # Union the inked region returned by the brush engine with the accumulated stroke region.
        # This accumulated region defines the area around which final blur will be applied on release.
        if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
            if self._stroke_inked_region_canvas.isNull():
                self._stroke_inked_region_canvas = inked_rect_canvas # Initialize
            else:
                self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas) # Union

            # Request immediate repaint for the area directly affected by ink in this segment.
            # This provides continuous visual feedback as the user draws (ink appears immediately).
            # Ensure the returned canvas rectangle is valid before using it for update.
            dirty_widget_rect = self._canvas_to_widget_rect(inked_rect_canvas)
            # Request repaint for the calculated widget area. Add a slight margin.
            self.update(dirty_widget_rect.normalized().adjusted(-2, -2, 2, 2)) # Use normalized() to handle inverted rects if any

        # Update the stored last point to the current point for the next mouseMoveEvent.
        self._last_point_widget = current_point_widget

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Only handle mouse release events if drawing was in progress (_is_drawing is True)
        # and the left mouse button was released.
        if not self._is_drawing or event.button() != Qt.LeftButton or self._lienzo is None:
             # If not handled, pass the event to the base class handler.
             super().mouseReleaseEvent(event)
             return

        # Handle the very last segment of the stroke if the release point is different from the last recorded point.
        if self._last_point_widget is not None: # _last_point_widget should be valid if _is_drawing is true
            current_point_widget = event.pos() # Get the mouse release position in widget coordinates
            canvas_last_point = self._widget_to_canvas(self._last_point_widget) # Last processed point on canvas
            canvas_current_point = self._widget_to_canvas(current_point_widget) # Release point on canvas

            # Only process the last segment if the canvas points are different.
            # If points are the same, the ink for this point was already applied in mousePress.
            if canvas_last_point != canvas_current_point:
                 # Call the basic brush engine function for the last segment.
                 # This updates the Lienzo directly.
                 try:
                      # apply_basic_brush_stroke_segment returns inked rect (QRect)
                      inked_rect_canvas = apply_basic_brush_stroke_segment(
                           self._lienzo, # The Lienzo instance
                           canvas_last_point, # Start point of this segment (last processed point)
                           canvas_current_point, # End point of this segment (release point)
                           self._current_brush_params # Current brush parameters
                      )
                       # === Accumulate the inked region for this stroke (for the very last segment) ===
                       # Union the inked region with the accumulated stroke region.
                      if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
                         if self._stroke_inked_region_canvas.isNull():
                             self._stroke_inked_region_canvas = inked_rect_canvas # Initialize
                         else:
                             self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas) # Union

                       # No intermediate update request here; the finalization handles the update.
                 except Exception as e:
                      # Catch potential errors during the last segment processing
                      print(f"Error in apply_basic_brush_stroke_segment during mouseReleaseEvent last segment: {e}")
                      # Proceed to finalization with the state accumulated up to the point of error.
                      # Optionally show an error message
                      # QMessageBox.critical(self, "绘画出错", f"处理最后一段笔画时发生错误: {e}")

            # If last canvas point == current canvas point, the segment was handled on mousePress, nothing more to ink on move/release.

        # === Stroke Has Finished -> Apply Localized Blur ===
        # Call the helper method to trigger the finalization process (applying blur).
        # This process applies blur to the accumulated _stroke_inked_region_canvas and pastes the result to the Lienzo.
        # It also handles the final update request.
        self._finalize_current_stroke()

        # === Reset Drawing State ===
        # Clear the drawing flag, last point, and the stored stroke inked region.
        # A new stroke will start clean on the next mousePress.
        self._is_drawing = False
        self._last_point_widget = None
        self._stroke_inked_region_canvas = QRect() # Clear the accumulated inked region for the next stroke

        # Important: Call super() to ensure the event is passed up the hierarchy.
        super().mouseReleaseEvent(event)

    def _finalize_current_stroke(self):
        """Calls the brush engine to apply localized blur to the stroke's inked region and paste the result."""
        # print("Calling finalize_stroke (basic version)...") # Debugging

        # Ensure there is a valid accumulated inked region to finalize
        if self._stroke_inked_region_canvas.isNull() or not self._stroke_inked_region_canvas.isValid():
             # print("No valid inked region found to finalize.")
             return # Nothing to finalize if the region is empty or invalid

        # Call the finalize function in brush_engine.
        # finalize_stroke takes Lienzo, accumulated_inked_rect (QRect), params and returns updated_rect (QRect).
        # This function modifies the Lienzo directly by cropping, blurring, and pasting within and around the inked region.
        # It returns the canvas rectangle that was modified on the Lienzo.
        try:
            # finalize_stroke should return the modified QRect (canvas coords)
            updated_canvas_rect = finalize_stroke(
                 self._lienzo, # The Lienzo instance
                 self._stroke_inked_region_canvas, # The accumulated inked region for this stroke
                 self._current_brush_params # Pass brush parameters (needed for wetness, size for blur area calculation)
            )
             # print("finalize_stroke call finished.")
        except Exception as e:
             # Catch potential errors during finalization (e.g., blur errors)
             print(f"Error during stroke finalization in finalize_stroke: {e}")
             # Even if an error occurs, try to update the area that was potentially modified before the error
             # (e.g., the accumulated inked area might be visible without blur).
             updated_canvas_rect = self._stroke_inked_region_canvas # Fallback to the accumulated inked rect before finalizing

             # Optionally show an error message
             QMessageBox.critical(self, "绘画出错", f"完成笔画时发生错误 (可能与晕染有关): {e}")

        # Request repaint for the area that was updated on the Lienzo during finalization (blur + paste).
        # Ensure the returned canvas rectangle from finalize_stroke is valid before using it for update.
        # The update() call needs a QRect in widget coordinates. Convert the canvas rect.
        if updated_canvas_rect.isValid() and not updated_canvas_rect.isNull():
             # Convert the updated canvas rectangle from canvas coordinates to widget coordinates for the repaint request
             dirty_widget_rect = self._canvas_to_widget_rect(updated_canvas_rect)
             # Request repaint for the calculated widget area. Add a slight margin to be sure
             # diffusion effects at the boundary are shown without clipping artifacts caused by scaling/rounding.
             # normalize() handles potential inverted rects if calculated width/height were negative (shouldn't happen with correct mapping).
             self.update(dirty_widget_rect.normalized().adjusted(-5, -5, 5, 5)) # Request repaint of this potentially large area
             # print(f"Stroke finalized. Repainting widget area: {dirty_widget_rect.normalized()}")
        else:
             pass # print("Stroke finalized, but no area needed repainting or area was invalid.")

    # --- Coordinate transformation helper functions ---
    # These are crucial for mapping between the widget's pixel coordinates and the canvas data's pixel coordinates.
    # Assumes the canvas widget currently scales the lienzo content to fit the entire widget area (stretch mode).
    # Future enhancement: Implement different scaling/alignment modes (e.g., aspect ratio, zoom, pan) and update these methods accordingly.

    def _widget_to_canvas(self, widget_point: QPoint) -> QPoint:
        """Converts a point from widget coordinates to canvas data coordinates."""
        # Ensure lienzo and widget have valid dimensions before calculation
        if self._lienzo is None or self.width() <= 0 or self.height() <= 0:
            # Return an invalid point typically represented as (-1, -1)
            return QPoint(-1, -1)

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        # Apply simple linear mapping from widget coordinates [0, widget_width-1] to canvas coordinates [0, canvas_width-1].
        # Use floating point division yielding a scaling factor, then multiply and convert to integer.
        # widget_point.x()/widget_width gives a proportion [0, 1)
        canvas_x = int(widget_point.x() * canvas_width / widget_width)
        canvas_y = int(widget_point.y() * canvas_height / widget_height)

        # Ensure the resulting canvas point is clamped to be within the valid canvas pixel index range [0, size-1].
        # This is especially important near the right/bottom edges of the widget.
        canvas_x = max(0, min(canvas_x, canvas_width - 1)) if canvas_width > 0 else 0
        canvas_y = max(0, min(canvas_y, canvas_height - 1)) if canvas_height > 0 else 0

        return QPoint(canvas_x, canvas_y)

    def _canvas_to_widget_rect(self, canvas_rect: QRect) -> QRect:
        """Converts a rectangle from canvas data coordinates to widget coordinates."""
        # Ensure lienzo and widget have valid dimensions and the canvas rect is valid
        if self._lienzo is None or self.width() <= 0 or self.height() <= 0 or canvas_rect.isNull():
             return QRect() # Return an empty (invalid) QRect if inputs are invalid

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        # Apply simple linear scaling to the top-left and bottom-right corners of the canvas rectangle.
        # QRect.left/top are inclusive. QRect.right/bottom are exclusive (return left + width, top + height).
        # Canvas indices are 0-based.

        # Map top-left (x,y)
        widget_x1 = int(canvas_rect.left() * widget_width / canvas_width)
        widget_y1 = int(canvas_rect.top() * widget_height / canvas_height)

        # Map bottom-right (exclusive) (x+w, y+h)
        widget_x2 = int(canvas_rect.right() * widget_width / canvas_width)
        widget_y2 = int(canvas_rect.bottom() * widget_height / canvas_height)

        # Clamp the resulting widget coordinates to be within the widget bounds [0, widget_size] (exclusive upper bound).
        widget_x1 = max(0, widget_x1)
        widget_y1 = max(0, widget_y1)
        widget_x2 = min(widget_width, widget_x2) # Clamp max to widget_width (exclusive)
        widget_y2 = min(widget_height, widget_y2) # Clamp max to widget_height (exclusive)

        # Calculate the width and height of the resulting widget rectangle.
        # Handle cases where the clamped x2 <= x1 or y2 <= y1 resulting in zero or negative size.
        widget_w = max(0, widget_x2 - widget_x1)
        widget_h = max(0, widget_y2 - widget_y1)

        # Optional: If the original canvas_rect had size but mapped to a 0-size widget rect (due to scaling below 1 pixel),
        # force a minimum size of 1 pixel if it's within bounds. This helps microscopic updates show visually.
        if canvas_rect.width() > 0 and widget_w == 0 and widget_x1 < widget_width: widget_w = 1
        if canvas_rect.height() > 0 and widget_h == 0 and widget_y1 < widget_height: widget_h = 1

        # Return the resulting widget rectangle
        return QRect(widget_x1, widget_y1, widget_w, widget_h)

    def _widget_to_canvas_rect(self, widget_rect: QRect) -> QRect:
        """Converts a rectangle from widget coordinates to canvas data coordinates."""
        # Ensure lienzo and widget have valid dimensions and the widget rect is valid
        if self._lienzo is None or self.width() <= 0 or self.height() <= 0 or widget_rect.isNull():
             return QRect() # Return an empty (invalid) QRect if inputs are invalid

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        # Apply simple linear scaling to the top-left and bottom-right corners of the widget rectangle.
        # Widget rect.left/top are inclusive. Widget rect.right/bottom are exclusive.

        # Map top-left (x,y)
        canvas_x1 = int(widget_rect.left() * canvas_width / widget_width)
        canvas_y1 = int(widget_rect.top() * canvas_height / widget_height)

        # Map bottom-right (exclusive) (x+w, y+h)
        canvas_x2 = int(widget_rect.right() * canvas_width / widget_width)
        canvas_y2 = int(widget_rect.bottom() * canvas_height / widget_height)

        # Clamp the resulting canvas coordinates to be within the canvas bounds [0, canvas_size] (exclusive upper bound for indices).
        canvas_x1 = max(0, canvas_x1)
        canvas_y1 = max(0, canvas_y1)
        canvas_x2 = min(canvas_width, canvas_x2) # Clamp max to canvas_width (exclusive)
        canvas_y2 = min(canvas_height, canvas_y2) # Clamp max to canvas_height (exclusive)

        # Calculate the width and height of the resulting canvas rectangle.
        # Handle cases where the clamped x2 <= x1 or y2 <= y1 resulting in zero or negative size.
        canvas_w = max(0, canvas_x2 - canvas_x1)
        canvas_h = max(0, canvas_y2 - canvas_y1)

        # Optional: If the original widget_rect had size but mapped to a 0-size canvas rect (due to scaling below 1 pixel),
        # force a minimum size of 1 pixel if it's within bounds. This helps tiny drawing movements register.
        if widget_rect.width() > 0 and canvas_w == 0 and canvas_x1 < canvas_width: canvas_w = 1
        if widget_rect.height() > 0 and canvas_h == 0 and canvas_y1 < canvas_height: canvas_h = 1

        # Return the resulting canvas rectangle
        return QRect(canvas_x1, canvas_y1, canvas_w, canvas_h)

    # --- Additional Canvas Operations ---

    def load_image_into_canvas(self, image_data: np.ndarray):
        """Resizes and sets the given NumPy image data (color or gray) to the current canvas."""
        if image_data is None or image_data.size == 0:
             print("No image data provided to load into canvas.")
             return
        if self._lienzo is None:
             print("Lienzo not initialized.")
             return

        # Lienzo.set_canvas_data handles conversion to grayscale and resizing to the current lienzo size.
        # set_canvas_data also copies the input data internally.
        self._lienzo.set_canvas_data(image_data)

        # Request repaint of the entire canvas since content changed
        self.update()
        self.canvas_content_changed.emit() # Notify external listeners (like MainWindow status bar)

    def get_canvas_image_data(self) -> np.ndarray:
        """Returns the current canvas content as a NumPy array (uint8, grayscale)."""
        if self._lienzo:
            # Return a copy to prevent external modification of Lienzo's internal data outside this class/module.
            return self._lienzo.get_canvas_data().copy()
        # Return an empty array of the expected type if Lienzo is not initialized
        return np.array([], dtype=np.uint8)