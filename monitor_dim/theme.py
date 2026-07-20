from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


ACCENT = "#4B9EFF"
BACKGROUND = "#07111F"
SURFACE = "#0E1B2D"
SURFACE_ALT = "#13243A"
TEXT = "#F5F8FC"
MUTED = "#91A4BD"


def app_icon(size: int = 128) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(BACKGROUND))
    painter.setPen(QPen(QColor("#1D416A"), max(2, size // 40)))
    painter.drawRoundedRect(QRectF(3, 3, size - 6, size - 6), size * 0.22, size * 0.22)
    painter.setBrush(QColor("#0B1A2B"))
    painter.setPen(QPen(QColor("#9AC9FF"), max(3, size // 18)))
    monitor = QRectF(size * 0.20, size * 0.23, size * 0.60, size * 0.42)
    painter.drawRoundedRect(monitor, size * 0.035, size * 0.035)
    painter.setPen(QPen(QColor(ACCENT), max(3, size // 18)))
    painter.drawLine(QPointF(size * 0.50, size * 0.67), QPointF(size * 0.50, size * 0.78))
    painter.drawLine(QPointF(size * 0.36, size * 0.79), QPointF(size * 0.64, size * 0.79))
    painter.end()
    return QIcon(pixmap)


APP_STYLESHEET = f"""
* {{
    font-family: "Segoe UI Variable", "Segoe UI";
    font-size: 10pt;
    color: {TEXT};
}}
QMainWindow, QWidget#AppRoot {{ background: {BACKGROUND}; }}
QWidget#Sidebar {{ background: #091525; border-right: 1px solid #1A2B43; }}
QFrame#Hero {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #10294A,stop:1 #0B192B);
    border: 1px solid #24496F; border-radius: 16px;
}}
QFrame#Card {{ background: {SURFACE}; border: 1px solid #1D3049; border-radius: 13px; }}
QFrame#MonitorRow {{ background: #0C192A; border: 1px solid #203752; border-radius: 13px; }}
QFrame#MonitorRow:hover {{ border-color: #315A83; }}
QLabel#Title {{ font-size: 22pt; font-weight: 700; }}
QLabel#PageTitle {{ font-size: 17pt; font-weight: 700; }}
QLabel#CardTitle {{ font-size: 11pt; font-weight: 650; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Accent {{ color: {ACCENT}; font-weight: 650; }}
QListWidget {{ background: transparent; border: none; outline: none; padding: 8px; }}
QListWidget::item {{ color: #A9B8CA; padding: 11px 12px; margin: 2px; border-radius: 8px; }}
QListWidget::item:selected {{ background: #17365A; color: white; }}
QListWidget::item:hover {{ background: #10253E; }}
QPushButton {{
    background: {SURFACE_ALT}; border: 1px solid #294361; border-radius: 8px;
    padding: 8px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: #1A3454; border-color: #3F6C9F; }}
QPushButton:pressed {{ background: #102944; }}
QPushButton:disabled {{ background: #0B1625; color: #52657B; border-color: #1B2B3E; }}
QPushButton#PrimaryButton {{ background: {ACCENT}; color: #03101F; border: none; }}
QPushButton#PrimaryButton:hover {{ background: #72B3FF; }}
QPushButton#DangerButton {{ color: #FF8D98; }}
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: #091525; border: 1px solid #28405E; border-radius: 8px;
    padding: 7px 9px; selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {SURFACE_ALT}; border: 1px solid #304B6C; selection-background-color: #24548A; }}
QSlider::groove:horizontal {{ height: 5px; background: #20334B; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: white; border: 3px solid {ACCENT}; width: 14px; margin: -6px 0; border-radius: 10px; }}
QSlider::groove:horizontal:disabled {{ background: #17263A; }}
QSlider::sub-page:horizontal:disabled {{ background: #39516B; }}
QSlider::handle:horizontal:disabled {{ background: #718296; border-color: #39516B; }}
QTableWidget {{ background: transparent; border: none; gridline-color: #1D3049; outline: none; }}
QTableWidget::item {{ padding: 8px; }}
QHeaderView::section {{ background: #0B1727; color: {MUTED}; padding: 8px; border: none; border-bottom: 1px solid #253951; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2B4665; min-height: 28px; border-radius: 5px; }}
QToolTip {{ background: #172A42; color: white; border: 1px solid #3A5C81; padding: 5px; }}
"""
