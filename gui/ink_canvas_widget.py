# gui/ink_canvas_widget.py

from PyQt5.QtWidgets import QWidget, QSizePolicy, QMessageBox
from PyQt5.QtGui import QPainter, QPixmap, QMouseEvent, QPaintEvent, QImage
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal

import numpy as np
import cv2

from processing.utils import convert_cv_to_qt
from processing.brush_engine import apply_basic_brush_stroke_segment, finalize_stroke
from processing.lienzo import Lienzo

class InkCanvasWidget(QWidget):
    canvas_content_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lienzo: Lienzo = None

        self._is_drawing = False
        self._last_point_widget: QPoint = None

        self._current_brush_params = {
            'size': 40,
            'density': 60,
            'wetness': 0,
            'feibai': 20,
            'type': 'round'
        }

        self._stroke_inked_region_canvas: QRect = QRect()

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def set_lienzo(self, lienzo_instance: Lienzo):
        self._lienzo = lienzo_instance
        self.update()
        self.canvas_content_changed.emit()

    def get_lienzo(self) -> Lienzo:
        return self._lienzo

    def set_brush_params(self, params: dict):
        self._current_brush_params.update(params)

    def paintEvent(self, event: QPaintEvent):
         painter = QPainter(self)

         if self._lienzo is None or self._lienzo.get_canvas_data().size == 0:
             painter.fillRect(event.rect(), Qt.white)
             painter.drawText(event.rect(), Qt.AlignCenter, "等待加载画布或图片...")
             return

         canvas_data = self._lienzo.get_canvas_data()
         canvas_width, canvas_height = self._lienzo.get_size()
         widget_width, widget_height = self.width(), self.height()

         if canvas_width <= 0 or canvas_height <= 0 or widget_width <= 0 or widget_height <= 0:
              painter.fillRect(event.rect(), Qt.white)
              return

         pixmap = QPixmap()
         try:
             pixmap = convert_cv_to_qt(canvas_data)
         except Exception as e:
             print(f"Error converting canvas data to QPixmap for painting: {e}")
             painter.fillRect(event.rect(), Qt.white)
             painter.drawText(event.rect(), Qt.AlignCenter, "画布绘制错误!")
             return

         # Draw the entire pixmap scaled to the widget area.
         # This is simpler and more robust than trying to map dirty rectangles perfectly.
         painter.drawPixmap(self.rect(), pixmap, pixmap.rect())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.LeftButton or self._lienzo is None:
             super().mousePressEvent(event)
             return

        if 'type' not in self._current_brush_params or 'size' not in self._current_brush_params:
             print(f"Warning: Missing brush parameter(s): {self._current_brush_params}. Cannot start drawing.")
             QMessageBox.warning(self, "绘画出错", "笔刷参数不完整，无法开始绘画。")
             super().mousePressEvent(event)
             return

        self._is_drawing = True
        self._last_point_widget = event.pos()

        self._stroke_inked_region_canvas = QRect()

        canvas_point = self._widget_to_canvas(self._last_point_widget)

        try:
            inked_rect_canvas = apply_basic_brush_stroke_segment(
                 self._lienzo,
                 canvas_point,
                 canvas_point,
                 self._current_brush_params
            )
        except Exception as e:
             print(f"Error in apply_basic_brush_stroke_segment during mousePress: {e}")
             self._is_drawing = False
             self._last_point_widget = None
             self._stroke_inked_region_canvas = QRect()
             QMessageBox.critical(self, "绘画出错", f"处理第一个笔画点时发生错误: {e}")
             super().mousePressEvent(event)
             return

        if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
            self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas)
            # Request FULL repaint to avoid artifacts
            self.update() # Changed from update(rect) to update()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._is_drawing or self._lienzo is None or self._last_point_widget is None or not (event.buttons() & Qt.LeftButton) or 'type' not in self._current_brush_params:
            super().mouseMoveEvent(event)
            return

        current_point_widget = event.pos()

        canvas_last_point = self._widget_to_canvas(self._last_point_widget)
        canvas_current_point = self._widget_to_canvas(current_point_widget)

        if canvas_last_point == QPoint(-1,-1) or canvas_current_point == QPoint(-1,-1) or canvas_last_point == canvas_current_point:
             self._last_point_widget = current_point_widget
             return

        try:
            inked_rect_canvas = apply_basic_brush_stroke_segment(
                 self._lienzo,
                 canvas_last_point,
                 canvas_current_point,
                 self._current_brush_params
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

            # Request FULL repaint to avoid artifacts
            self.update() # Changed from update(rect) to update()

        self._last_point_widget = current_point_widget

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self._is_drawing or event.button() != Qt.LeftButton or self._lienzo is None:
             super().mouseReleaseEvent(event)
             return

        if 'wetness' not in self._current_brush_params or 'size' not in self._current_brush_params:
            print("Warning: Missing brush parameters for finalization. Skipping finalize_stroke.")
            self._is_drawing = False
            self._last_point_widget = None
            self._stroke_inked_region_canvas = QRect()
            super().mouseReleaseEvent(event)
            return

        if self._last_point_widget is not None:
            current_point_widget = event.pos()
            canvas_last_point = self._widget_to_canvas(self._last_point_widget)
            canvas_current_point = self._widget_to_canvas(current_point_widget)

            if canvas_last_point != QPoint(-1,-1) and canvas_current_point != QPoint(-1,-1) and canvas_last_point != canvas_current_point:
                 try:
                      inked_rect_canvas = apply_basic_brush_stroke_segment(
                           self._lienzo,
                           canvas_last_point,
                           canvas_current_point,
                           self._current_brush_params
                      )
                      if inked_rect_canvas.isValid() and not inked_rect_canvas.isNull():
                          if self._stroke_inked_region_canvas.isNull():
                              self._stroke_inked_region_canvas = inked_rect_canvas
                          else:
                              self._stroke_inked_region_canvas = self._stroke_inked_region_canvas.united(inked_rect_canvas)

                 except Exception as e:
                      print(f"Error in apply_basic_brush_stroke_segment during mouseRelease last segment: {e}")

        self._finalize_current_stroke()

        self._is_drawing = False
        self._last_point_widget = None
        self._stroke_inked_region_canvas = QRect()

        super().mouseReleaseEvent(event)

    def _finalize_current_stroke(self):
        if self._lienzo is None or self._stroke_inked_region_canvas.isNull() or not self._stroke_inked_region_canvas.isValid():
             return

        try:
            updated_canvas_rect = finalize_stroke(
                 self._lienzo,
                 self._stroke_inked_region_canvas,
                 self._current_brush_params
            )
        except Exception as e:
             print(f"Error during stroke finalization: {e}")
             updated_canvas_rect = self._stroke_inked_region_canvas.normalized()
             QMessageBox.critical(self, "绘画出错", f"完成笔画时发生错误 (可能与晕染有关): {e}")

        # Request FULL repaint after finalization to show blur correctly
        self.update() # Changed from update(rect) to update()

    # Coordinate transformation helpers (remain the same)
    def _widget_to_canvas(self, widget_point: QPoint) -> QPoint:
        """Converts a point from widget coordinates to canvas data coordinates."""
        if self._lienzo is None or self.width() <= 0 or self.height() <= 0:
             return QPoint(-1, -1)

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        if widget_width <= 0 or widget_height <= 0 or canvas_width <= 0 or canvas_height <= 0:
             return QPoint(-1, -1)

        canvas_x = int(widget_point.x() * canvas_width / widget_width)
        canvas_y = int(widget_point.y() * canvas_height / widget_height)

        canvas_x = max(0, min(canvas_x, canvas_width - 1))
        canvas_y = max(0, min(canvas_y, canvas_height - 1))

        return QPoint(canvas_x, canvas_y)

    def _canvas_to_widget_rect(self, canvas_rect: QRect) -> QRect:
        """Converts a rectangle from canvas data coordinates to widget coordinates."""
        if self._lienzo is None or self.width() <= 0 or self.height() <= 0 or canvas_rect.isNull():
             return QRect()

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        if widget_width <= 0 or widget_height <= 0 or canvas_width <= 0 or canvas_height <= 0:
             return QRect()

        widget_x1 = int(canvas_rect.left() * widget_width / canvas_width)
        widget_y1 = int(canvas_rect.top() * widget_height / canvas_height)

        widget_x2 = int(canvas_rect.right() * widget_width / canvas_width)
        widget_y2 = int(canvas_rect.bottom() * widget_height / canvas_height)

        widget_x1 = max(0, widget_x1)
        widget_y1 = max(0, widget_y1)
        widget_x2 = min(widget_width, widget_x2)
        widget_y2 = min(widget_height, widget_y2)

        widget_w = max(0, widget_x2 - widget_x1)
        widget_h = max(0, widget_y2 - widget_y1)

        if canvas_rect.width() > 0 and widget_w == 0 and widget_x1 < widget_width: widget_w = 1
        if canvas_rect.height() > 0 and widget_h == 0 and widget_y1 < widget_height: widget_h = 1

        return QRect(widget_x1, widget_y1, widget_w, widget_h)

    def _widget_to_canvas_rect(self, widget_rect: QRect) -> QRect:
        """Converts a rectangle from widget coordinates to canvas data coordinates."""
        if self._lienzo is None or self.width() <= 0 or self.height() <= 0 or widget_rect.isNull():
             return QRect()

        canvas_width, canvas_height = self._lienzo.get_size()
        widget_width, widget_height = self.width(), self.height()

        if widget_width <= 0 or widget_height <= 0 or canvas_width <= 0 or canvas_height <= 0:
             return QRect()

        canvas_x1 = int(widget_rect.left() * canvas_width / widget_width)
        canvas_y1 = int(widget_rect.top() * canvas_height / widget_height)

        canvas_x2 = int(widget_rect.right() * canvas_width / widget_width)
        canvas_y2 = int(widget_rect.bottom() * canvas_height / widget_height)

        canvas_x1 = max(0, canvas_x1)
        canvas_y1 = max(0, canvas_y1)
        canvas_x2 = min(canvas_width, canvas_x2)
        canvas_y2 = min(canvas_height, canvas_y2)

        canvas_w = max(0, canvas_x2 - canvas_x1)
        canvas_h = max(0, canvas_y2 - canvas_y1)

        if widget_rect.width() > 0 and canvas_w == 0 and canvas_x1 < canvas_width: canvas_w = 1
        if widget_rect.height() > 0 and canvas_h == 0 and canvas_y1 < canvas_height: canvas_h = 1

        return QRect(canvas_x1, canvas_y1, canvas_w, canvas_h)

    # Additional Canvas Operations (remain the same)
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

        self.update()
        self.canvas_content_changed.emit()

    def get_canvas_image_data(self) -> np.ndarray:
        """Returns the current canvas content as a NumPy array (uint8, grayscale)."""
        if self._lienzo:
            return self._lienzo.get_canvas_data().copy()
        return np.array([], dtype=np.uint8)