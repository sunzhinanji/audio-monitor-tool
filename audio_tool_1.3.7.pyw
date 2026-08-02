# -*- coding: utf-8 -*-
"""
音频监控工具 1.3.7
功能：通过 NAudio COM (Program.exe) 实时监控音频进程及其音量
      显示每个进程的峰值音量(dB)、进程状态追踪、定位物理文件
      修复：双击失效问题，改用 mouseDoubleClickEvent 直接捕获
"""

import sys
import os
import time
import threading
import subprocess
import random
import math
from datetime import datetime

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

# ==================== 全局退出标志 ====================
_should_stop = False

def set_should_stop():
    global _should_stop
    _should_stop = True

def clear_should_stop():
    global _should_stop
    _should_stop = False

def should_stop():
    return _should_stop

# ==================== 配置 ====================
PROGRAM_EXE_PATH = r"c:\Program Files\audio finder deepseek 20260727\AudioMeterCOM\publish\AudioMeterCOM.exe"

SYSTEM_PROCESSES = [
    'svchost.exe', 'audiodg.exe', 'system', 'explorer.exe',
    'sihost.exe', 'taskhostw.exe', 'runtimebroker.exe',
    'dwm.exe', 'csrss.exe', 'winlogon.exe', 'services.exe',
    'lsass.exe', 'smss.exe', 'conhost.exe', 'ctfmon.exe',
    'wininit.exe', 'fontdrvhost.exe', 'spoolsv.exe',
]

def is_system_process(name):
    return name.lower() in [p.lower() for p in SYSTEM_PROCESSES]

def get_process_exe_path(pid):
    try:
        import psutil
        proc = psutil.Process(pid)
        return proc.exe()
    except:
        return None

def get_audio_processes():
    if should_stop():
        return [], [], {}

    if not os.path.exists(PROGRAM_EXE_PATH):
        return [], [], {}

    pid_name_map = {}
    pid_peak_map = {}

    try:
        process = subprocess.Popen(
            [PROGRAM_EXE_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        start_time = time.time()
        line_count = 0
        max_lines = 100
        timeout = 0.5

        while line_count < max_lines and (time.time() - start_time) < timeout:
            if should_stop():
                process.terminate()
                break

            line = process.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            if line.startswith('#DEVICE|'):
                continue

            parts = line.split('|')
            if len(parts) >= 4:
                try:
                    pid = int(parts[0])
                    name = parts[1].strip()
                    peak = float(parts[2])
                    state = int(parts[3])

                    if pid > 0:
                        if name and name != "未知":
                            pid_name_map[pid] = name
                        pid_peak_map[pid] = peak
                        line_count += 1
                except:
                    continue

        process.terminate()
        process.wait(timeout=1)

    except Exception:
        return [], [], {}

    if should_stop():
        return [], [], {}

    try:
        import psutil
        for pid in list(pid_name_map.keys()):
            if pid_name_map[pid] == "未知":
                try:
                    proc = psutil.Process(pid)
                    pid_name_map[pid] = proc.name()
                except:
                    pass
    except:
        pass

    user_processes = []
    system_processes = []

    for pid in pid_name_map:
        if should_stop():
            return [], [], {}
        name = pid_name_map.get(pid, f"PID:{pid}")
        if is_system_process(name):
            system_processes.append((pid, name, pid_peak_map.get(pid, 0)))
        else:
            user_processes.append((pid, name, pid_peak_map.get(pid, 0)))

    return user_processes, system_processes, pid_peak_map


# ==================== 剪贴板操作 ====================

def copy_to_clipboard(text):
    try:
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        return True
    except Exception:
        return False

def open_file_location(exe_path):
    try:
        if sys.platform == 'win32':
            subprocess.Popen(['explorer', '/select,', exe_path])
            return True
        else:
            folder = os.path.dirname(exe_path)
            os.startfile(folder)
            return True
    except Exception:
        return False


# ==================== 像素点动画控件 ====================

class PixelDotAnimation(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 14)
        self.running = False
        self.timer = None
        self.dot_count = 12
        self.dot_size = 2
        self.spacing = 3
        self.dot_states = [1 for _ in range(self.dot_count)]
        self.setStyleSheet("background-color: transparent; border: none;")

    def start_animation(self):
        if self.running:
            return
        self.running = True
        self.dot_states = [1 for _ in range(self.dot_count)]
        self.update()
        if self.timer is None:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_dots)
            self.timer.start(80)

    def stop_animation(self):
        self.running = False
        if self.timer:
            self.timer.stop()
            self.timer = None
        self.dot_states = [0 for _ in range(self.dot_count)]
        self.update()

    def update_dots(self):
        if not self.running:
            return
        for i in range(self.dot_count):
            if random.random() < 0.20:
                self.dot_states[i] = 1 - self.dot_states[i]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        total_width = self.dot_count * (self.dot_size + self.spacing) - self.spacing
        start_x = (self.width() - total_width) // 2
        start_y = (self.height() - self.dot_size) // 2

        for i in range(self.dot_count):
            x = start_x + i * (self.dot_size + self.spacing)
            y = start_y
            if self.dot_states[i] == 1:
                painter.setBrush(QColor(255, 200, 50, 220))
                painter.setPen(Qt.NoPen)
            else:
                painter.setBrush(QColor(40, 40, 60, 20))
                painter.setPen(Qt.NoPen)
            painter.drawEllipse(x, y, self.dot_size, self.dot_size)


# ==================== 进程状态追踪 ====================

class ProcessTracker:
    def __init__(self, pid, name, exe_path=None):
        self.pid = pid
        self.name = name
        self.exe_path = exe_path
        self.first_seen = datetime.now()
        self.last_seen = datetime.now()
        self.is_active = True
        self.disappear_intervals = []
        self.last_disappear_time = None
        self.last_silent_time = None
        self.has_ever_disappeared = False
        self.current_peak = 0.0
        self._play_start_time = None
        self._was_alive = True

    def update(self, active, peak=0.0, paused=False):
        now = datetime.now()
        self.current_peak = peak
        
        if paused:
            return
        
        # 更新进程存活状态
        if active:
            if not self._was_alive:
                self.is_active = True
                self.has_ever_disappeared = True
                if self.last_disappear_time:
                    interval = (now - self.last_disappear_time).total_seconds()
                    if interval > 0.3:
                        self.disappear_intervals.append(round(interval, 1))
            self.last_seen = now
            self._was_alive = True
        else:
            if self._was_alive:
                self.is_active = False
                self.last_disappear_time = now
                self._play_start_time = None
                self.last_silent_time = None
            self._was_alive = False
        
        # 检测发声/静音状态变化
        is_playing = (peak > 0.001)
        was_playing = (self._play_start_time is not None)
        
        if is_playing and self.is_active:
            if not was_playing:
                if self.last_silent_time is not None:
                    interval = (now - self.last_silent_time).total_seconds()
                    if interval > 0.3:
                        self.disappear_intervals.append(round(interval, 1))
                        self.has_ever_disappeared = True
                self._play_start_time = now
                self.last_silent_time = None
        else:
            if was_playing:
                self._play_start_time = None
                self.last_silent_time = now

    def get_duration(self):
        if self._play_start_time is None:
            return "0秒"
        seconds = int((datetime.now() - self._play_start_time).total_seconds())
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分{seconds % 60}秒"
        else:
            return f"{seconds // 3600}时{(seconds % 3600) // 60}分"

    def get_last_disappear_time(self):
        if self.last_disappear_time:
            return self.last_disappear_time.strftime("%H:%M:%S")
        return "--"

    def get_intervals(self):
        if self.disappear_intervals:
            return "、".join([str(i) for i in self.disappear_intervals])
        return "--"

    def get_peak_text(self):
        if self.current_peak <= 0:
            return "-∞"
        db = 20 * math.log10(self.current_peak)
        return f"{db:.1f}"

    def get_status_color(self):
        # 1. 消失（进程退出）→ 灰色
        if not self.is_active:
            return "#666666"
        
        # 2. 有间隔记录且未消失 → 橙色
        if self.disappear_intervals:
            return "#f39c12"
        
        # 3. 静音（无间隔记录）→ 白色
        if self.current_peak <= 0.001:
            return "#ffffff"
        
        # 4. 首次发声 → 绿色
        return "#4CAF50"


# ==================== 自定义表格控件 ====================

class ProcessTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["进程名", "PID", "音量(dB)", "持续时间", "最后消失", "间隔记录"])
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)

        self.setColumnWidth(0, 180)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 90)
        self.setColumnWidth(3, 100)
        self.setColumnWidth(4, 100)
        self.setColumnWidth(5, 150)

        self.setWordWrap(True)
        self.setStyleSheet("""
            QTableWidget {
                background-color: #16213e;
                border: 1px solid #2a3a5e;
                border-radius: 6px;
                color: #e0e0e0;
                font-size: 13px;
                font-family: "Consolas", "Microsoft YaHei", monospace;
                gridline-color: transparent;
                outline: none;
            }
            QTableWidget::item {
                padding: 2px 4px;
                border: none;
                white-space: normal;
                word-wrap: break-word;
            }
            QTableWidget::item:selected {
                background-color: #2d4a7a;
            }
            QTableWidget::item:hover {
                background-color: #1e3a5f;
            }
            QHeaderView::section {
                background-color: #1a1a2e;
                color: #8899bb;
                padding: 2px 6px;
                border-right: 1px solid #3a4a6e;
                border-left: none;
                border-top: none;
                border-bottom: 1px solid #3a4a6e;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget::item:!selected {
                background-color: transparent;
            }
        """)

        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(False)
        self.itemSelectionChanged.connect(self.refresh_item_colors)

    def refresh_item_colors(self):
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    tracker = item.data(Qt.UserRole + 1)
                    if tracker:
                        color = tracker.get_status_color()
                        item.setForeground(QColor(color))
                    else:
                        if item.text() in ["👤 用户进程", "⚙️ 系统进程"]:
                            item.setForeground(QColor("#8899bb"))

    def add_process_row(self, tracker, is_system=False):
        row = self.rowCount()
        self.insertRow(row)

        name_item = QTableWidgetItem(tracker.name)
        name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        pid_item = QTableWidgetItem(str(tracker.pid))
        pid_item.setTextAlignment(Qt.AlignCenter)

        peak_item = QTableWidgetItem(tracker.get_peak_text())
        peak_item.setTextAlignment(Qt.AlignCenter)

        duration_item = QTableWidgetItem(tracker.get_duration())
        duration_item.setTextAlignment(Qt.AlignCenter)

        last_item = QTableWidgetItem(tracker.get_last_disappear_time())
        last_item.setTextAlignment(Qt.AlignCenter)

        interval_item = QTableWidgetItem(tracker.get_intervals())
        interval_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for item in [name_item, pid_item, peak_item, duration_item, last_item, interval_item]:
            item.setData(Qt.UserRole + 1, tracker)

        self.setItem(row, 0, name_item)
        self.setItem(row, 1, pid_item)
        self.setItem(row, 2, peak_item)
        self.setItem(row, 3, duration_item)
        self.setItem(row, 4, last_item)
        self.setItem(row, 5, interval_item)

        self.resizeRowToContents(row)

    def get_selected_tracker(self):
        selected = self.selectedItems()
        if selected:
            return selected[0].data(Qt.UserRole + 1)
        return None

    def clear_rows(self):
        self.setRowCount(0)

    def add_section_row(self, text):
        row = self.rowCount()
        self.insertRow(row)
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        item.setForeground(QColor("#8899bb"))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self.setItem(row, 0, item)
        self.setSpan(row, 0, 1, 6)
        self.setRowHeight(row, 20)

    def mouseDoubleClickEvent(self, event):
        """直接捕获鼠标双击事件，提高响应可靠性"""
        # 获取双击位置对应的行
        if hasattr(event, 'position'):
            pos = event.position().toPoint()
        else:
            pos = event.pos()
        
        index = self.indexAt(pos)
        
        if index.isValid():
            row = index.row()
            # 获取该行第一个有 tracker 数据的列
            tracker = None
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item:
                    tracker = item.data(Qt.UserRole + 1)
                    if tracker:
                        break
            
            if tracker:
                # 调用主窗口的双击处理方法
                main_window = self.window()
                if hasattr(main_window, 'on_item_double_clicked'):
                    main_window.on_item_double_clicked(tracker)
                event.accept()
                return
        
        # 如果点击无效区域，交给父类处理
        super().mouseDoubleClickEvent(event)


# ==================== 自动换行历史记录 ====================

class AutoWrapHistoryList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QListWidget {
                background-color: #16213e;
                border: 1px solid #2a3a5e;
                border-radius: 6px;
                padding: 2px 6px;
                color: #8899bb;
                font-size: 12px;
                font-family: "Microsoft YaHei", "Consolas", monospace;
            }
            QListWidget::item {
                padding: 0px 2px;
                min-height: 16px;
                border: none;
                word-wrap: break-word;
            }
            QListWidget::item:selected {
                background-color: transparent;
                color: #8899bb;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
        """)
        self.setSelectionMode(QAbstractItemView.NoSelection)

    def add_history_item(self, text):
        self.addItem(text)
        self.scrollToBottom()


# ==================== 监控线程 ====================

class MonitorThread(QThread):
    data_updated = Signal(object, object, object, object, object)
    scanning_started = Signal()
    scanning_finished = Signal()

    def __init__(self):
        super().__init__()
        self.running = True
        self.paused = False

    def run(self):
        global _should_stop
        trackers = {}

        while self.running and not should_stop():
            if not self.paused:
                scan_start_time = datetime.now()
                self.scanning_started.emit()

                user_procs, system_procs, peak_map = get_audio_processes()

                scan_complete_time = datetime.now()

                if not should_stop():
                    active_pids = set()
                    all_procs = user_procs + system_procs

                    for pid, name, peak in all_procs:
                        active_pids.add(pid)
                        if pid not in trackers:
                            exe_path = get_process_exe_path(pid)
                            trackers[pid] = ProcessTracker(pid, name, exe_path)
                        else:
                            trackers[pid].name = name
                            if trackers[pid].exe_path is None:
                                trackers[pid].exe_path = get_process_exe_path(pid)
                        trackers[pid].update(True, peak, self.paused)

                    for pid in list(trackers.keys()):
                        if pid not in active_pids:
                            trackers[pid].update(False, 0, self.paused)

                    now = datetime.now()
                    to_remove = []
                    for pid, tracker in trackers.items():
                        if not tracker.is_active:
                            delta = (now - tracker.last_seen).total_seconds()
                            if delta > 300:
                                to_remove.append(pid)
                    for pid in to_remove:
                        del trackers[pid]

                    self.data_updated.emit(user_procs, system_procs, trackers, scan_start_time, scan_complete_time)
                    self.scanning_finished.emit()
                else:
                    self.scanning_finished.emit()
                    break

            for _ in range(1):
                if should_stop() or not self.running:
                    break
                time.sleep(0.05)

    def stop(self):
        self.running = False

    def toggle_pause(self):
        self.paused = not self.paused


# ==================== 主窗口 ====================

class AudioMonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 音频监控工具 1.3.7")

        screen = QApplication.primaryScreen().geometry()
        self.screen_height = screen.height()

        window_width = 1050
        window_height = min(750, int(self.screen_height * 0.85))
        self.setGeometry(100, 100, window_width, window_height)
        self.setMinimumSize(850, 500)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
                color: white;
            }
            QPushButton#kill_btn {
                background-color: #e74c3c;
            }
            QPushButton#kill_btn:hover {
                background-color: #c0392b;
            }
            QPushButton#kill_btn:disabled {
                background-color: #555;
                color: #888;
            }
            QPushButton#folder_btn {
                background-color: #3498db;
            }
            QPushButton#folder_btn:hover {
                background-color: #2980b9;
            }
            QPushButton#folder_btn:disabled {
                background-color: #555;
                color: #888;
            }
            QPushButton#pause_btn {
                background-color: #3498db;
            }
            QPushButton#pause_btn:hover {
                background-color: #2980b9;
            }
            QPushButton#export_btn {
                background-color: #2ecc71;
            }
            QPushButton#export_btn:hover {
                background-color: #27ae60;
            }
            QPushButton#clear_btn {
                background-color: #95a5a6;
            }
            QPushButton#clear_btn:hover {
                background-color: #7f8c8d;
            }
            QFrame#line {
                background-color: #2a3a5e;
                max-height: 1px;
                min-height: 1px;
            }
            QScrollBar:vertical {
                background-color: #16213e;
                border: none;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #2a4a7a;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3a5a8a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #16213e;
                border: none;
                height: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background-color: #2a4a7a;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #3a5a8a;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ========== 标题行 ==========
        title_layout = QHBoxLayout()
        title_label = QLabel("🎵 音频监控工具 1.3.7")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        engine_label = QLabel("🔊 NAudio COM")
        engine_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold; background-color: #1a3a3a; padding: 2px 12px; border-radius: 10px;")
        title_layout.addWidget(engine_label)

        self.status_label = QLabel("● 监控中")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 13px; font-weight: bold;")
        title_layout.addWidget(self.status_label)
        main_layout.addLayout(title_layout)

        # ========== 统计行 ==========
        stats_layout = QHBoxLayout()
        self.count_label = QLabel("进程数: 0")
        self.count_label.setStyleSheet("font-size: 13px; color: #8899bb;")
        stats_layout.addWidget(self.count_label)

        stats_layout.addStretch()
        self.current_time_label = QLabel("")
        self.current_time_label.setStyleSheet("font-size: 13px; color: #8899bb; font-weight: bold;")
        stats_layout.addWidget(self.current_time_label)

        main_layout.addLayout(stats_layout)

        # ========== 扫描动画行 ==========
        scan_anim_layout = QHBoxLayout()
        scan_anim_layout.addStretch()
        self.pixel_dot = PixelDotAnimation()
        scan_anim_layout.addWidget(self.pixel_dot)
        self.scan_text_label = QLabel("")
        self.scan_text_label.setStyleSheet("font-size: 12px; color: #f39c12;")
        scan_anim_layout.addWidget(self.scan_text_label)
        scan_anim_layout.addStretch()
        main_layout.addLayout(scan_anim_layout)

        self._scan_text_timer = QTimer()
        self._scan_text_timer.setSingleShot(True)
        self._scan_text_timer.timeout.connect(self._clear_scan_text)

        # ========== 分隔线 ==========
        line = QFrame()
        line.setObjectName("line")
        line.setFrameShape(QFrame.HLine)
        main_layout.addWidget(line)

        # ========== 进程表格 ==========
        self.process_table = ProcessTableWidget(self)
        self.process_table.setMinimumHeight(250)
        self.process_table.itemSelectionChanged.connect(self.on_selection_changed)
        main_layout.addWidget(self.process_table, 1)

        # ========== 操作按钮行 ==========
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.kill_btn = QPushButton("✕ 结束选中的进程")
        self.kill_btn.setObjectName("kill_btn")
        self.kill_btn.setEnabled(False)
        self.kill_btn.clicked.connect(self.kill_selected_process)
        btn_layout.addWidget(self.kill_btn)

        self.folder_btn = QPushButton("📂 定位进程对应的物理文件")
        self.folder_btn.setObjectName("folder_btn")
        self.folder_btn.setEnabled(False)
        self.folder_btn.clicked.connect(self.open_process_file_location)
        btn_layout.addWidget(self.folder_btn)

        self.pause_btn = QPushButton("⏸ 暂停监控")
        self.pause_btn.setObjectName("pause_btn")
        self.pause_btn.clicked.connect(self.toggle_monitoring)
        btn_layout.addWidget(self.pause_btn)

        self.export_btn = QPushButton("📤 导出日志")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.clicked.connect(self.export_log)
        btn_layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton("🗑 清空历史")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(self.clear_btn)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # ========== 历史记录 ==========
        history_title = QLabel("📜 历史记录")
        history_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #e0e0e0; margin-top: 3px;")
        main_layout.addWidget(history_title)

        self.history_list = AutoWrapHistoryList()
        self.history_list.setMinimumHeight(100)
        self.history_list.setMaximumHeight(150)
        main_layout.addWidget(self.history_list)

        # ========== 底部信息 ==========
        footer_label = QLabel("💡 静音=白色 | 首次发声=绿色 | 恢复/有间隔记录=橙色 | 消失=灰色 | 双击行执行操作")
        footer_label.setStyleSheet("font-size: 11px; color: #556688; margin-top: 3px;")
        main_layout.addWidget(footer_label)

        # ========== 初始化 ==========
        self.history = []
        self.max_history = 100
        self.trackers = {}
        self._last_pids = set()
        self._prev_scan_start_time = None
        self._scan_count = 0
        self._first_scan_done = False

        clear_should_stop()
        self.monitor_thread = MonitorThread()
        self.monitor_thread.data_updated.connect(self.update_display)
        self.monitor_thread.scanning_started.connect(self.on_scan_start)
        self.monitor_thread.scanning_finished.connect(self.on_scan_finish)
        self.monitor_thread.start()

        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)

    def update_time(self):
        self.current_time_label.setText(datetime.now().strftime("%H:%M:%S"))

    def _clear_scan_text(self):
        self.scan_text_label.setText("")

    def on_scan_start(self):
        self.pixel_dot.start_animation()
        self.scan_text_label.setText("扫描中...")
        self._scan_text_timer.stop()

    def on_scan_finish(self):
        self.pixel_dot.stop_animation()
        self._scan_text_timer.start(300)

    def update_display(self, user_procs, system_procs, trackers, scan_start_time, scan_complete_time):
        self._scan_count += 1

        self.trackers = trackers

        total_active = 0
        total_disappeared = 0
        for t in trackers.values():
            if t.is_active:
                total_active += 1
            else:
                total_disappeared += 1

        self.count_label.setText(f"活跃: {total_active}  消失: {total_disappeared}")

        current_pids = set(trackers.keys())

        # ========== 历史记录：只记录进程变化 ==========
        if self._first_scan_done:
            added = current_pids - self._last_pids
            removed = self._last_pids - current_pids

            if added:
                names = []
                for pid in added:
                    if pid in trackers:
                        names.append(trackers[pid].name)
                if names:
                    self.add_history(f"➕ 新增: {', '.join(names)}")

            if removed:
                names = []
                for pid in removed:
                    if pid in trackers:
                        names.append(trackers[pid].name)
                if names:
                    self.add_history(f"➖ 消失: {', '.join(names)}")
        else:
            self._first_scan_done = True
            if total_active > 0:
                proc_names = []
                for pid, t in trackers.items():
                    if t.is_active:
                        proc_names.append(t.name)
                if proc_names:
                    display_names = proc_names[:5]
                    if len(proc_names) > 5:
                        display_names.append("...")
                    self.add_history(f"🟢 初始进程: {', '.join(display_names)} ({len(proc_names)}个进程)")
            else:
                self.add_history("⚪ 无音频进程")

        self._prev_scan_start_time = scan_start_time
        self._last_pids = current_pids.copy()

        # ========== 分类显示进程表格 ==========
        user_active = []
        user_inactive = []
        sys_active = []
        sys_inactive = []

        sys_pids = {pid for pid, _, _ in system_procs}

        for pid, t in trackers.items():
            is_system = pid in sys_pids or t.name.lower() in [p.lower() for p in SYSTEM_PROCESSES]

            if is_system:
                if t.is_active:
                    sys_active.append(t)
                else:
                    sys_inactive.append(t)
            else:
                if t.is_active:
                    user_active.append(t)
                else:
                    user_inactive.append(t)

        sorted_trackers = user_active + user_inactive + sys_active + sys_inactive

        self.process_table.clear_rows()

        if user_active or user_inactive:
            self.process_table.add_section_row("👤 用户进程")
            for t in user_active + user_inactive:
                self.process_table.add_process_row(t, False)

        if sys_active or sys_inactive:
            self.process_table.add_section_row("⚙️ 系统进程")
            for t in sys_active + sys_inactive:
                self.process_table.add_process_row(t, True)

        if not sorted_trackers:
            self.process_table.insertRow(0)
            empty_item = QTableWidgetItem("暂无检测到音频进程")
            empty_item.setTextAlignment(Qt.AlignCenter)
            empty_item.setForeground(QColor("#556688"))
            self.process_table.setItem(0, 0, empty_item)
            self.process_table.setSpan(0, 0, 1, 6)
            self.process_table.setRowHeight(0, 50)

        self.process_table.refresh_item_colors()

    def on_selection_changed(self):
        has_selection = len(self.process_table.selectedItems()) > 0
        self.kill_btn.setEnabled(has_selection)
        self.folder_btn.setEnabled(has_selection)
        self.process_table.refresh_item_colors()

    def get_selected_tracker(self):
        return self.process_table.get_selected_tracker()

    def on_item_double_clicked(self, tracker):
        """双击处理 - 直接接收 tracker 对象"""
        if not tracker:
            return

        if tracker.is_active:
            # 非灰色进程：复制 PID + 打开任务管理器
            copy_to_clipboard(str(tracker.pid))
            self.add_history(f"📋 {datetime.now().strftime('%H:%M:%S')} - 已复制: {tracker.name} (PID: {tracker.pid})")
            self.status_label.setText(f"📋 已复制 PID: {tracker.pid}")
            self.status_label.setStyleSheet("color: #f39c12; font-size: 13px; font-weight: bold;")

            def restore_status():
                time.sleep(2)
                if not self.monitor_thread.paused:
                    self.status_label.setText("● 监控中")
                    self.status_label.setStyleSheet("color: #4CAF50; font-size: 13px; font-weight: bold;")
            threading.Thread(target=restore_status, daemon=True).start()

            try:
                os.startfile('taskmgr.exe')
            except:
                pass
        else:
            # 灰色进程：定位物理文件
            self.locate_process_file(tracker)

    def locate_process_file(self, tracker):
        if not tracker.exe_path:
            tracker.exe_path = get_process_exe_path(tracker.pid)

        if tracker.exe_path and os.path.exists(tracker.exe_path):
            if open_file_location(tracker.exe_path):
                self.add_history(f"📂 {datetime.now().strftime('%H:%M:%S')} - 定位: {tracker.name} -> {tracker.exe_path}")
                self.status_label.setText(f"📂 已定位: {tracker.name}")
                self.status_label.setStyleSheet("color: #2ecc71; font-size: 13px; font-weight: bold;")

                def restore_status():
                    time.sleep(2)
                    if not self.monitor_thread.paused:
                        self.status_label.setText("● 监控中")
                        self.status_label.setStyleSheet("color: #4CAF50; font-size: 13px; font-weight: bold;")
                threading.Thread(target=restore_status, daemon=True).start()
                return True
            else:
                QMessageBox.warning(self, "错误", f"无法定位文件:\n{tracker.exe_path}")
                return False
        else:
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        if proc.info['name'] == tracker.name:
                            exe_path = proc.info['exe']
                            if exe_path and os.path.exists(exe_path):
                                tracker.exe_path = exe_path
                                if open_file_location(exe_path):
                                    self.add_history(f"📂 {datetime.now().strftime('%H:%M:%S')} - 定位: {tracker.name} -> {exe_path}")
                                    return True
                    except:
                        pass
            except:
                pass

            QMessageBox.warning(
                self,
                "无法定位",
                f"无法定位进程 {tracker.name} 的物理文件\n\n"
                f"可能原因：\n"
                f"1. 进程已结束，文件可能已被删除\n"
                f"2. 该进程是系统服务，无法直接定位\n"
                f"3. 权限不足"
            )
            return False

    def open_process_file_location(self):
        tracker = self.get_selected_tracker()
        if not tracker:
            return
        self.locate_process_file(tracker)

    def kill_selected_process(self):
        tracker = self.get_selected_tracker()
        if not tracker:
            return

        reply = QMessageBox.question(
            self,
            "确认结束进程",
            f"确定要结束进程\n\n  {tracker.name} (PID: {tracker.pid})\n\n吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            subprocess.run(['taskkill', '/F', '/PID', str(tracker.pid)], capture_output=True)
            self.add_history(f"✅ {datetime.now().strftime('%H:%M:%S')} - 已结束: {tracker.name}")
        except Exception as e:
            self.add_history(f"❌ {datetime.now().strftime('%H:%M:%S')} - 结束失败: {str(e)}")

    def toggle_monitoring(self):
        self.monitor_thread.toggle_pause()
        paused = self.monitor_thread.paused
        self.pause_btn.setText("▶ 继续监控" if paused else "⏸ 暂停监控")
        self.status_label.setText("⏸ 已暂停" if paused else "● 监控中")
        self.status_label.setStyleSheet(
            "color: #f39c12; font-size: 13px; font-weight: bold;"
            if paused else
            "color: #4CAF50; font-size: 13px; font-weight: bold;"
        )

    def add_history(self, text):
        self.history.append(text)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        self.history_list.add_history_item(text)

    def export_log(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存日志",
            f"audio_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=" * 50 + "\n")
                    f.write("音频监控日志\n")
                    f.write("=" * 50 + "\n")
                    f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    for item in self.history:
                        f.write(item + "\n")
                self.add_history(f"📤 {datetime.now().strftime('%H:%M:%S')} - 日志已导出")
                QMessageBox.information(self, "成功", f"日志已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

    def clear_history(self):
        self.history = []
        self.history_list.clear()

    def closeEvent(self, event):
        set_should_stop()
        self.monitor_thread.stop()
        if not self.monitor_thread.wait(500):
            self.monitor_thread.terminate()
            self.monitor_thread.wait()
        self.time_timer.stop()
        self.pixel_dot.stop_animation()
        self._scan_text_timer.stop()
        clear_should_stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("音频监控工具")
    window = AudioMonitorWindow()
    window.show()
    sys.exit(app.exec())