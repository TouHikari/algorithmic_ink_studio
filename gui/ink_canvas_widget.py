# gui/ink_canvas_widget.py

from PyQt5.QtWidgets import QWidget, QSizePolicy, QMessageBox, QRubberBand, QStyle
from PyQt5.QtGui import QPainter, QPixmap, QMouseEvent, QPaintEvent, QImage, QColor, QCursor, QIcon
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal, QRectF

import numpy as np
import cv2
import math
import os

from processing.utils import convert_cv_to_qt
from processing.brush_engine import apply_basic_brush_stroke_segment, finalize_stroke
from processing.lienzo import Lienzo

class InkCanvasWidget(QWidget):
    canvas_content_changed = pyqtSignal()
    strokeFinished = pyqtSignal()
    zoomLevelChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lienzo: Lienzo = None

        self._is_drawing = False
        self._last_point_widget: QPoint = None

        # Updated default parameters including new ones
        self._current_brush_params = {
            'size': 40,
            'density': 60,
            'wetness': 0,
            'feibai': 20,
            'hardness': 50, # New
            'flow': 100,   # New
            'type': 'round',
            'angle_mode': 'Direction', # New
            'fixed_angle': 0, # New
            'pos_jitter': 0, # New
            'size_jitter': 0, # New
            'angle_jitter': 0 # New
        }

        self._current_tool = "brush"

        self._stroke_inked_region_canvas: QRect = QRect()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self._zoom_factor = 1.0
        self._pan_offset_widget = QPoint(0, 0)

        self._is_panning = False
        self._pan_start_widget_pos: QPoint = None
        self._pan_start_offset: QPoint = None

        self.set_current_tool(self._current_tool)

    def _get_cursor_path(self, cursor_name: str) -> str:
        """Helper to get custom cursor path."""
        base_path = os.path.dirname(__file__)
        cursor_folder = os.path.join(base_path, '..', 'resources', 'cursors')
        filepath = os.path.join(cursor_folder, f'{cursor_name}.png')
        if os.path.exists(filepath):
             return filepath
        return ""

    def set_lienzo(self, lienzo_instance: Lienzo):
        self._lienzo = lienzo_instance
        self._zoom_factor = 1.0
        self._pan_offset_widget = QPoint(0, 0)
        self.zoomLevelChanged.emit(self._zoom_factor)
        self.update()
        self.canvas_content_changed.emit()

    def get_lienzo(self) -> Lienzo:
        return self._lienzo

    def set_brush_params(self, params: dict):
        self._current_brush_params.update(params)

    def set_current_tool(self, tool_name: str):
        """Sets the current tool ('brush' or 'eraser')."""
        if tool_name in ["brush", "eraser"]:
            self._current_tool = tool_name
            if self._current_tool == "brush":
                 custom_cursor_path = self._get_cursor_path('brush')
                 if custom_cursor_path:
                      self.setCursor(QCursor(QPixmap(custom_cursor_path)))
                 else:
                      self.setCursor(Qt.CrossCursor)
            elif self._current_tool == "eraser":
                 custom_cursor_path = self._get_cursor_path('eraser')
                 if custom_cursor_path:
                      self.setCursor(QCursor(QPixmap(custom_cursor_path)))
                 else:
                      self.setCursor(Qt.CrossCursor)
        else:
            print(f"Warning: Unknown tool name '{tool_name}'. Tool not changed.")

    def set_zoom_pan(self, zoom_factor: float, pan_offset_widget: QPoint):
        """Sets the zoom level and pan offset."""
        if self._lienzo is None:
             return

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        self._zoom_factor = max(0.01, min(zoom_factor, 100.0))

        scaled_canvas_width = canvas_width * self._zoom_factor
        scaled_canvas_height = canvas_height * self._zoom_factor

        max_px = max(0, int(widget_width - scaled_canvas_width))
        max_py = max(0, int(widget_height - scaled_canvas_height))
        min_px = min(0, int(widget_width - scaled_canvas_width))
        min_py = min(0, int(widget_height - scaled_canvas_height))

        clamped_pan_x = np.clip(pan_offset_widget.x(), min_px, max_px)
        clamped_pan_y = np.clip(pan_offset_widget.y(), min_py, max_py)

        self._pan_offset_widget = QPoint(int(clamped_pan_x), int(clamped_pan_y))

        self.zoomLevelChanged.emit(self._zoom_factor)
        self.update()

    def get_zoom_factor(self) -> float:
        return self._zoom_factor

    def get_pan_offset(self) -> QPoint:
        return self._pan_offset_widget

    def paintEvent(self, event: QPaintEvent):
         painter = QPainter(self)
         painter.fillRect(event.rect(), Qt.white)

         if self._lienzo is None or self._lienzo.get_canvas_data().size == 0:
             painter.drawText(self.rect(), Qt.AlignCenter, "等待加载画布或图片...")
             return

         canvas_data = self._lienzo.get_canvas_data()
         canvas_width, canvas_height = self._lienzo.get_size()
         widget_width, widget_height = self.width(), self.height()

         if canvas_width <= 0 or canvas_height <= 0 or widget_width <= 0 or widget_height <= 0:
              return

         pixmap = QPixmap()
         try:
             pixmap = convert_cv_to_qt(canvas_data)
         except Exception as e:
             print(f"Error converting canvas data to QPixmap for painting: {e}")
             painter.drawText(self.rect(), Qt.AlignCenter, "画布绘制错误!")
             return

         source_rect_f = QRectF(pixmap.rect())

         scaled_width = canvas_width * self._zoom_factor
         scaled_height = canvas_height * self._zoom_factor
         target_rect_f = QRectF(self._pan_offset_widget.x(), self._pan_offset_widget.y(), scaled_width, scaled_height)

         painter.drawPixmap(target_rect_f, pixmap, source_rect_f)

    def mousePressEvent(self, event: QMouseEvent):
        if self._lienzo is not None and (event.button() == Qt.MidButton or event.button() == Qt.RightButton):
            self._is_panning = True
            self._pan_start_widget_pos = event.pos()
            self._pan_start_offset = self._pan_offset_widget
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() != Qt.LeftButton or self._lienzo is None:
             super().mousePressEvent(event)
             return

        # Check for necessary brush parameters
        required_params = ['size', 'density', 'wetness', 'feibai', 'hardness', 'flow', 'type', 'angle_mode', 'fixed_angle', 'pos_jitter', 'size_jitter', 'angle_jitter']
        if not all(param in self._current_brush_params for param in required_params):
             print(f"Warning: Missing brush parameter(s). Cannot start operation. Params: {self._current_brush_params}")
             QMessageBox.warning(self, "操作出错", "笔刷参数不完整，无法开始操作。")
             super().mousePressEvent(event)
             return

        self._is_drawing = True
        self._last_point_widget = event.pos()

        self._stroke_inked_region_canvas = QRect()

        canvas_point = self._widget_to_canvas(self._last_point_widget)

        # Only proceed if canvas point is valid
        if canvas_point == QPoint(-1,-1):
             print("Warning: Start point outside canvas bounds. Cannot start operation.")
             self._is_drawing = False
             super().mousePressEvent(event)
             return

        params_for_engine = self._current_brush_params.copy()
        params_for_engine['is_eraser'] = (self._current_tool == "eraser")

        try:
            inked_rect_canvas = apply_basic_brush_stroke_segment(
                 self._lienzo,
                 canvas_point,
                 canvas_point,
                 params_for_engine
            )
        except Exception as e:
             print(f"Error in apply_basic_brush_stroke_segment during mousePress: {e}")
             self._is_drawing = False
             self._last_point_widget = None
             self._stroke_inked_region_canvas = QRect()
             QMessageBox.critical(self, "操作出错", f"处理第一个操作点时发生错误: {e}")
             super().mousePressEvent(event)
             return

        if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
            self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas)
            self.update()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            if self._pan_start_widget_pos is None or self._pan_start_offset is None or self._lienzo is None:
                 self._is_panning = False
                 self.set_current_tool(self._current_tool)
                 super().mouseMoveEvent(event)
                 return

            delta_widget = event.pos() - self._pan_start_widget_pos
            new_pan_offset_widget = self._pan_start_offset + delta_widget

            canvas_width, canvas_height = self._lienzo.get_size()
            widget_width, widget_height = self.width(), self.height()

            scaled_canvas_width = canvas_width * self._zoom_factor
            scaled_canvas_height = canvas_height * self._zoom_factor

            max_px = max(0, int(widget_width - scaled_canvas_width))
            max_py = max(0, int(widget_height - scaled_canvas_height))
            min_px = min(0, int(widget_width - scaled_canvas_width))
            min_py = min(0, int(widget_height - scaled_canvas_height))

            clamped_pan_x = np.clip(new_pan_offset_widget.x(), min_px, max_px)
            clamped_pan_y = np.clip(new_pan_offset_widget.y(), min_py, max_py)

            self._pan_offset_widget = QPoint(int(clamped_pan_x), int(clamped_pan_y))

            self.update()
            event.accept()
            return

        # Handle Drawing/Erasing only if left button is held and we are drawing
        if not self._is_drawing or self._lienzo is None or self._last_point_widget is None or not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return

        current_point_widget = event.pos()

        canvas_last_point = self._widget_to_canvas(self._last_point_widget)
        canvas_current_point = self._widget_to_canvas(current_point_widget)

        # Only process if both points are valid canvas points and they are different
        if canvas_last_point == QPoint(-1,-1) or canvas_current_point == QPoint(-1,-1) or canvas_last_point == canvas_current_point:
             self._last_point_widget = current_point_widget
             return

        params_for_engine = self._current_brush_params.copy()
        params_for_engine['is_eraser'] = (self._current_tool == "eraser")

        try:
            inked_rect_canvas = apply_basic_brush_stroke_segment(
                 self._lienzo,
                 canvas_last_point,
                 canvas_current_point,
                 params_for_engine
            )
        except Exception as e:
             print(f"Error in apply_basic_brush_stroke_segment during mouseMove: {e}")
             self._is_drawing = False
             self._last_point_widget = None
             self._stroke_inked_region_canvas = QRect()
             super().mouseMoveEvent(event)
             return

        if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
            if self._stroke_inked_region_canvas.isNull():
                self._stroke_inked_region_canvas = inked_rect_canvas
            else:
                self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas)

            self.update()

        self._last_point_widget = current_point_widget

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_panning:
            self._is_panning = False
            self.set_current_tool(self._current_tool)
            event.accept()
            return

        if not self._is_drawing or event.button() != Qt.LeftButton or self._lienzo is None:
             super().mouseReleaseEvent(event)
             return

        params_for_engine = self._current_brush_params.copy()
        params_for_engine['is_eraser'] = (self._current_tool == "eraser")

        # Handle the very last segment if needed
        if self._last_point_widget is not None:
            current_point_widget = event.pos()
            canvas_last_point = self._widget_to_canvas(self._last_point_widget)
            canvas_current_point = self._widget_to_canvas(current_point_widget)

            # Only process if both points are valid canvas points and they are different
            if canvas_last_point != QPoint(-1,-1) and canvas_current_point != QPoint(-1,-1) and canvas_last_point != canvas_current_point:
                 try:
                      inked_rect_canvas = apply_basic_brush_stroke_segment(
                           self._lienzo,
                           canvas_last_point,
                           canvas_current_point,
                           params_for_engine
                      )
                      if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
                          if self._stroke_inked_region_canvas.isNull():
                              self._stroke_inked_region_canvas = inked_rect_canvas
                          else:
                              self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas)

                 except Exception as e:
                      print(f"Error in apply_basic_brush_stroke_segment during mouseRelease last segment: {e}")

        self._finalize_current_stroke(params_for_engine)

        self._is_drawing = False
        self._last_point_widget = None
        self._stroke_inked_region_canvas = QRect()

        self.strokeFinished.emit()

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Handles mouse wheel for zooming."""
        if self._lienzo is None:
             super().wheelEvent(event)
             return

        angle_delta = event.angleDelta().y()

        if angle_delta != 0:
            zoom_step_factor = 1.1
            new_zoom_factor = self._zoom_factor

            if angle_delta > 0:
                new_zoom_factor *= zoom_step_factor
            else:
                new_zoom_factor /= zoom_step_factor

            new_zoom_factor = max(0.01, min(new_zoom_factor, 100.0))

            if new_zoom_factor != self._zoom_factor:
                mouse_pos_widget = event.pos()
                canvas_pos_before_zoom = self._widget_to_canvas(mouse_pos_widget)

                if canvas_pos_before_zoom == QPoint(-1, -1):
                     widget_center_widget = QPoint(self.width() // 2, self.height() // 2)
                     canvas_pos_before_zoom = self._widget_to_canvas(widget_center_widget)
                     if canvas_pos_before_zoom == QPoint(-1, -1):
                          canvas_pos_before_zoom = QPoint(0,0)

                new_pan_offset_widget_x = mouse_pos_widget.x() - canvas_pos_before_zoom.x() * new_zoom_factor
                new_pan_offset_widget_y = mouse_pos_widget.y() - canvas_pos_before_zoom.y() * new_zoom_factor

                self.set_zoom_pan(new_zoom_factor, QPoint(int(new_pan_offset_widget_x), int(new_pan_offset_widget_y)))

            event.accept()
        else:
             super().wheelEvent(event)

    def resizeEvent(self, event):
        """Handles widget resizing. Readjust pan offset if needed."""
        old_width = event.oldSize().width()
        old_height = event.oldSize().height()
        new_width = event.size().width()
        new_height = event.size().height()

        if new_width > 0 and new_height > 0 and self._lienzo is not None:
             self.set_zoom_pan(self._zoom_factor, self._pan_offset_widget)

        super().resizeEvent(event)

    def _finalize_current_stroke(self, params_for_engine: dict):
        if self._lienzo is None or self._stroke_inked_region_canvas.isNull() or not self._stroke_inked_region_canvas.isValid():
             return

        try:
            updated_canvas_rect = finalize_stroke(
                 self._lienzo,
                 self._stroke_inked_region_canvas,
                 params_for_engine
            )
        except Exception as e:
             print(f"Error during stroke finalization: {e}")
             updated_canvas_rect = self._stroke_inked_region_canvas.normalized()
             QMessageBox.critical(self, "操作出错", f"完成操作时发生错误: {e}")

        self.update()

    def _widget_to_canvas(self, widget_point: QPoint) -> QPoint:
        """Converts a point from widget coordinates to canvas data coordinates, considering zoom and pan."""
        if self._lienzo is None or self._zoom_factor <= 0 or self.width() <= 0 or self.height() <= 0:
             return QPoint(-1, -1)

        relative_widget_x = widget_point.x() - self._pan_offset_widget.x()
        relative_widget_y = widget_point.y() - self._pan_offset_widget.y()

        canvas_x = int(relative_widget_x / self._zoom_factor)
        canvas_y = int(relative_widget_y / self._zoom_factor)

        canvas_width, canvas_height = self._lienzo.get_size()
        if canvas_width <= 0 or canvas_height <= 0:
             return QPoint(-1, -1)

        if not (0 <= canvas_x < canvas_width and 0 <= canvas_y < canvas_height):
             return QPoint(-1, -1)

        return QPoint(canvas_x, canvas_y)

    def _canvas_to_widget_rect(self, canvas_rect: QRect) -> QRect:
        """Converts a rectangle from canvas data coordinates to widget coordinates, considering zoom and pan."""
        if self._lienzo is None or self._zoom_factor <= 0 or canvas_rect.isNull():
             return QRect()

        widget_x1 = int(canvas_rect.left() * self._zoom_factor + self._pan_offset_widget.x())
        widget_y1 = int(canvas_rect.top() * self._zoom_factor + self._pan_offset_widget.y())

        widget_x2 = int(canvas_rect.right() * self._zoom_factor + self._pan_offset_widget.x())
        widget_y2 = int(canvas_rect.bottom() * self._zoom_factor + self._pan_offset_widget.y())

        widget_w = max(0, widget_x2 - widget_x1)
        widget_h = max(0, widget_y2 - widget_y1)

        if canvas_rect.width() > 0 and widget_w == 0 and widget_x1 < self.width() and widget_x2 > 0 : widget_w = max(1, int(canvas_rect.width() * self._zoom_factor))
        if canvas_rect.height() > 0 and widget_h == 0 and widget_y1 < self.height() and widget_y2 > 0 : widget_h = max(1, int(canvas_rect.height() * self._zoom_factor))

        return QRect(widget_x1, widget_y1, widget_w, widget_h)

    def _widget_to_canvas_rect(self, widget_rect: QRect) -> QRect:
        """Converts a rectangle from widget coordinates to canvas data coordinates, considering zoom and pan."""
        if self._lienzo is None or self._zoom_factor <= 0 or widget_rect.isNull():
             return QRect()

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        if widget_width <= 0 or widget_height <= 0 or canvas_width <= 0 or canvas_height <= 0:
             return QRect()

        canvas_x1_float = (widget_rect.left() - self._pan_offset_widget.x()) / self._zoom_factor
        canvas_y1_float = (widget_rect.top() - self._pan_offset_widget.y()) / self._zoom_factor

        canvas_x2_float = (widget_rect.right() - self._pan_offset_widget.x()) / self._zoom_factor
        canvas_y2_float = (widget_rect.bottom() - self._pan_offset_widget.y()) / self._zoom_factor

        canvas_x1 = int(canvas_x1_float)
        canvas_y1 = int(canvas_y1_float)

        canvas_x2 = int(canvas_x2_float)
        canvas_y2 = int(canvas_y2_float)

        canvas_w = max(0, canvas_x2 - canvas_x1)
        canvas_h = max(0, canvas_y2 - canvas_y1)

        if widget_rect.width() > 0 and canvas_w == 0: canvas_w = max(1, int(widget_rect.width()/self._zoom_factor))
        if widget_rect.height() > 0 and canvas_h == 0: canvas_h = max(1, int(widget_rect.height()/self._zoom_factor))

        temp_rect = QRect(canvas_x1, canvas_y1, canvas_w, canvas_h)

        clamped_rect = temp_rect.intersected(QRect(0, 0, canvas_width, canvas_height))

        return clamped_rect

    def load_image_into_canvas(self, image_data: np.ndarray):
        """Resizes and sets the given NumPy image data to the current canvas."""
        if image_data is None or image_data.size == 0:
             print("No image data provided.")
             return
        if self._lienzo is None:
             print("Lienzo not initialized.")
             return

        try:
            self._lienzo.set_canvas_data(image_data)
        except Exception as e:
             print(f"Error setting image data to lienzo: {e}")
             QMessageBox.critical(self, "加载出错", f"将图片数据载入画布时发生错误: {e}")
             return
        self._zoom_factor = 1.0
        self._pan_offset_widget = QPoint(0, 0)
        self.set_zoom_pan(self._zoom_factor, self._pan_offset_widget)
        self.update()
        self.canvas_content_changed.emit()

    def get_canvas_image_data(self) -> np.ndarray:
        """Returns the current canvas content as a NumPy array (uint8, grayscale)."""
        if self._lienzo:
            return self._lienzo.get_canvas_data().copy()
        return np.array([], dtype=np.uint8)

    def get_canvas_size(self) -> QSize:
         """Returns the canvas size as a QSize."""
         if self._lienzo:
              w, h = self._lienzo.get_size()
              return QSize(w, h)
         return QSize(0, 0)