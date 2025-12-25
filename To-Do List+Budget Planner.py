# productivity_suite.py
import sys
import io
import sqlite3
import datetime
from collections import Counter, defaultdict

# PyQt5 core and GUI
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QFormLayout, QStackedWidget, QTableWidget, 
    QTableWidgetItem, QListWidget, QListWidgetItem, QComboBox, QSpinBox,
    QFrame, QSplitter, QFileDialog, QSizePolicy, QMessageBox, QTabWidget, QDateEdit,
    QInputDialog, QHeaderView
)

# Matplotlib for charts
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

# ReportLab for PDF export
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors as reportlab_colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Image as PlatypusImage

# ------------------------
# Database setup
DB_FILE = "productivity.db"

# ------------------------
# Database helpers
# ------------------------
def init_db():
    """Initialize database tables if they don't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                completed INTEGER DEFAULT 0,
                completed_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS pomodoros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                duration INTEGER,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT DEFAULT (date('now')),
                category TEXT,
                description TEXT,
                amount REAL
            )
        """)
        conn.commit()

def db_execute(query, params=()):
    """
    Execute INSERT/UPDATE/DELETE queries.
    Returns the last inserted row id if available.
    """
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return c.lastrowid

def db_query(query, params=()):
    """
    Execute SELECT queries and return all rows.
    """
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute(query, params)
        return c.fetchall()

# ------------------------
# To-Do Widget
# ------------------------
class ToDoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.load_tasks()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e9e9e9;
            }
            QLineEdit, QPushButton, QListWidget {
                font-size: 14px;
            }
            QListWidget::item:selected {
                background-color: #1565C0;
                color: #ffffff;
            }
            QPushButton {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QLineEdit {
                background-color: #1E1E1E;
                border: 1px solid #333;
                color: #ffffff;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel("To-Do")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        hl = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter a new task...")
        self.add_btn = QPushButton("Add Task")
        self.add_btn.clicked.connect(self.add_task)
        self.task_input.returnPressed.connect(self.add_task)
        hl.addWidget(self.task_input)
        hl.addWidget(self.add_btn)
        layout.addLayout(hl)

        self.task_list = QListWidget()
        self.task_list.itemDoubleClicked.connect(self.edit_task_dialog)
        layout.addWidget(self.task_list)

        btn_row = QHBoxLayout()
        self.mark_btn = QPushButton("Mark Done")
        self.mark_btn.clicked.connect(self.mark_done)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_task)
        self.select_for_pomo_btn = QPushButton("Select for Pomodoro")
        self.select_for_pomo_btn.clicked.connect(self.select_for_pomodoro)
        btn_row.addWidget(self.mark_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addWidget(self.select_for_pomo_btn)
        layout.addLayout(btn_row)

        note = QLabel("Double-click a task to edit it.")
        note.setStyleSheet("color: gray; font-size: 11px")
        layout.addWidget(note)

    def load_tasks(self):
        self.task_list.clear()
        rows = db_query("SELECT id, title, completed FROM tasks ORDER BY created_at DESC")
        for tid, title, completed in rows:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, tid)
            if completed:
                item.setForeground(Qt.gray)
                font = item.font()
                font.setStrikeOut(True)
                item.setFont(font)
            self.task_list.addItem(item)
        
        if hasattr(self.parent, "analytics_widget"):
            self.parent.analytics_widget.update_stats()

    def add_task(self):
        title = self.task_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Warning", "Please enter a task.")
            return
        now = datetime.datetime.now().isoformat()
        db_execute("INSERT INTO tasks (title, created_at) VALUES (?, ?)", (title, now))
        self.task_input.clear()
        self.load_tasks()

    def edit_task_dialog(self, item):
        tid = item.data(Qt.UserRole)
        old = item.text()
        if hasattr(item.font(), "strikeOut") and item.font().strikeOut():
            old = old  # Already handled visually
        text, ok = QInputDialog.getText(self, "Edit Task", "Task:", text=old)
        if ok and text.strip():
            db_execute("UPDATE tasks SET title=? WHERE id=?", (text.strip(), tid))
            self.load_tasks()

    def mark_done(self):
        item = self.task_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Select a task")
            return
        tid = item.data(Qt.UserRole)
        now = datetime.datetime.now().isoformat()
        db_execute("UPDATE tasks SET completed=1, completed_at=? WHERE id=?", (now, tid))
        self.load_tasks()

    def delete_task(self):
        item = self.task_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Select a task")
            return
        tid = item.data(Qt.UserRole)
        confirm = QMessageBox.question(self, "Delete", "Delete selected task?")
        if confirm != QMessageBox.Yes:
            return
        db_execute("DELETE FROM tasks WHERE id=?", (tid,))
        self.load_tasks()

    def select_for_pomodoro(self):
        item = self.task_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Select a task to focus on.")
            return
        tid = item.data(Qt.UserRole)
        task_title = item.text()
        if hasattr(item.font(), "strikeOut") and item.font().strikeOut():
            task_title = task_title  # Keep the text as is
        self.parent.pomodoro_widget.set_current_task(tid, task_title)


# ------------------------
# Pomodoro Widget
# ------------------------
class PomodoroWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.work_duration = 25 * 60
        self.short_break = 5 * 60
        self.long_break = 15 * 60
        self.is_running = False
        self.is_work = True
        self.remaining = self.work_duration
        self.pomodoros_done = 0
        self.current_task_id = None
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e9e9e9;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #888;
            }
            QPushButton:hover:!disabled {
                background-color: #1565C0;
            }
            QSpinBox {
                background-color: #1E1E1E;
                color: #ffffff;
                border: 1px solid #333;
                padding: 2px 4px;
            }
        """)

        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel("Pomodoro")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        self.timer_label = QLabel("25:00")
        self.timer_label.setFont(QFont("Consolas", 36, QFont.Bold))
        self.timer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.timer_label)

        # Start / Pause / Reset row
        row = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset)
        self.pause_btn.setEnabled(False)  # Initially disabled
        row.addWidget(self.start_btn)
        row.addWidget(self.pause_btn)
        row.addWidget(self.reset_btn)
        layout.addLayout(row)

        # Info row
        info_row = QHBoxLayout()
        self.session_label = QLabel("Session: Work")
        self.selected_task_label = QLabel("No task selected")
        info_row.addWidget(self.session_label)
        info_row.addStretch()
        info_row.addWidget(self.selected_task_label)
        layout.addLayout(info_row)

        # Quick session settings
        quick_row = QHBoxLayout()
        quick_row.addWidget(QLabel("Work (min):"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(25)
        quick_row.addWidget(self.work_spin)

        quick_row.addWidget(QLabel("Short break (min):"))
        self.short_spin = QSpinBox()
        self.short_spin.setRange(1, 60)
        self.short_spin.setValue(5)
        quick_row.addWidget(self.short_spin)

        quick_row.addWidget(QLabel("Long break (min):"))
        self.long_spin = QSpinBox()
        self.long_spin.setRange(1, 60)
        self.long_spin.setValue(15)
        quick_row.addWidget(self.long_spin)

        layout.addLayout(quick_row)

    def set_current_task(self, tid, title):
        self.current_task_id = tid
        self.selected_task_label.setText(f"Task: {title}")

    def start(self):
        self.work_duration = int(self.work_spin.value()) * 60
        self.short_break = int(self.short_spin.value()) * 60
        self.long_break = int(self.long_spin.value()) * 60
        if not self.is_running:
            self.is_running = True
            if self.is_work and self.remaining <= 0:
                self.remaining = self.work_duration
            self.timer.start()
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)

    def pause(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)

    def reset(self):
        self.pause()
        self.is_work = True
        self.remaining = self.work_duration
        self._update_label()
        self.session_label.setText("Session: Work")

    def _tick(self):
        if self.remaining > 0:
            self.remaining -= 1
            self._update_label()
        else:
            self.timer.stop()
            self.is_running = False
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self._record_pomodoro()

            if self.is_work:
                self.pomodoros_done += 1
                if self.pomodoros_done % 4 == 0:
                    self.remaining = self.long_break
                    msg = "Long break time!"
                else:
                    self.remaining = self.short_break
                    msg = "Short break time!"
                self.is_work = False
                self.session_label.setText("Session: Break")
                QMessageBox.information(self, "Break", msg)
            else:
                self.is_work = True
                self.remaining = self.work_duration
                self.session_label.setText("Session: Work")
                QMessageBox.information(self, "Work", "Break is over. Back to work!")

            self._update_label()

            if hasattr(self.parent, "analytics_widget"):
                self.parent.analytics_widget.update_stats()

            if self.current_task_id and not self.is_work:
                resp = QMessageBox.question(self, "Pomodoro finished", "Mark selected task as completed?")
                if resp == QMessageBox.Yes:
                    now = datetime.datetime.now().isoformat()
                    db_execute("UPDATE tasks SET completed=1, completed_at=? WHERE id=?", (now, self.current_task_id))
                    self.parent.todo_widget.load_tasks()

    def _record_pomodoro(self):
        dur = int(self.work_spin.value()) * 60
        ts = datetime.datetime.now().isoformat()
        db_execute("INSERT INTO pomodoros (task_id, duration, timestamp) VALUES (?,?, ?)", (self.current_task_id, dur, ts))

    def _update_label(self):
        m, s = divmod(self.remaining, 60)
        self.timer_label.setText(f"{int(m):02d}:{int(s):02d}")


# ------------------------
# Analytics Widget
# ------------------------
class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.update_stats()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e9e9e9;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QLabel("Analytics")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        self.tasks_total_lbl = QLabel("Tasks total: 0")
        self.tasks_done_lbl = QLabel("Tasks done today: 0")
        self.pomo_total_lbl = QLabel("Pomodoros total: 0")
        self.focus_time_lbl = QLabel("Focus time (min): 0")

        for lbl in [self.tasks_total_lbl, self.tasks_done_lbl, self.pomo_total_lbl, self.focus_time_lbl]:
            lbl.setFont(QFont("Arial", 12))
            layout.addWidget(lbl)

        charts_row = QHBoxLayout()
        # Tasks completed chart
        self.fig1, self.ax1 = plt.subplots(figsize=(4, 3), facecolor="#121212")
        self._style_ax_dark(self.ax1)
        self.canvas1 = FigureCanvas(self.fig1)
        self.canvas1.setStyleSheet("background-color: transparent;")
        self.canvas1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        charts_row.addWidget(self.canvas1)

        # Pomodoros chart
        self.fig2, self.ax2 = plt.subplots(figsize=(4, 3), facecolor="#121212")
        self._style_ax_dark(self.ax2)
        self.canvas2 = FigureCanvas(self.fig2)
        self.canvas2.setStyleSheet("background-color: transparent;")
        self.canvas2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        charts_row.addWidget(self.canvas2)
        layout.addLayout(charts_row)

    def _style_ax_dark(self, ax):
        ax.set_facecolor("#1e1e1e")
        ax.tick_params(colors="white", labelcolor="white")
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.title.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.xaxis.label.set_color("white")
        ax.grid(True, color="#333333", linestyle="--", linewidth=0.5, alpha=0.5)

    def update_stats(self):
        tasks = db_query("SELECT id, completed, completed_at FROM tasks")
        total = len(tasks)
        done_today = 0
        for tid, completed, completed_at in tasks:
            if completed and completed_at:
                try:
                    dt = datetime.datetime.fromisoformat(completed_at)
                    if dt.date() == datetime.date.today():
                        done_today += 1
                except:
                    pass

        pomos = db_query("SELECT timestamp, duration FROM pomodoros")
        pomo_total = len(pomos)
        focus_minutes = sum((p[1] for p in pomos), 0) // 60 if pomos else 0

        self.tasks_total_lbl.setText(f"Tasks total: {total}")
        self.tasks_done_lbl.setText(f"Tasks done today: {done_today}")
        self.pomo_total_lbl.setText(f"Pomodoros total: {pomo_total}")
        self.focus_time_lbl.setText(f"Focus time (min): {focus_minutes}")

        # Tasks completed chart (last 14 days)
        self.ax1.clear()
        self._style_ax_dark(self.ax1)
        rows = db_query("SELECT completed_at FROM tasks WHERE completed=1 AND completed_at IS NOT NULL")
        dates = []
        for (ts,) in rows:
            try:
                dates.append(datetime.datetime.fromisoformat(ts).date())
            except:
                pass
        counts = Counter(dates)
        last_days = [datetime.date.today() - datetime.timedelta(days=i) for i in range(13, -1, -1)]
        x = [d.strftime("%b %d") for d in last_days]
        y = [counts.get(d, 0) for d in last_days]
        self.ax1.bar(x, y, color="#1565C0")
        self.ax1.set_title("Tasks Completed (last 14 days)")
        self.ax1.tick_params(axis='x', rotation=45)
        self.fig1.tight_layout()
        self.canvas1.draw()

        # Pomodoros chart (last 14 days)
        self.ax2.clear()
        self._style_ax_dark(self.ax2)
        rows = db_query("SELECT timestamp FROM pomodoros")
        pdays = []
        for (ts,) in rows:
            try:
                pdays.append(datetime.datetime.fromisoformat(ts).date())
            except:
                pass
        pcounts = Counter(pdays)
        y2 = [pcounts.get(d, 0) for d in last_days]
        self.ax2.plot(x, y2, marker='o', color="#FFB300", linewidth=2)
        self.ax2.set_title("Pomodoros (last 14 days)")
        self.ax2.tick_params(axis='x', rotation=45)
        self.fig2.tight_layout()
        self.canvas2.draw()


class BudgetWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.load_expenses()

    def setup_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #e9e9e9;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QDateEdit, QTableWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #333333;
            }
            QPushButton {
                background-color: #1565C0;
                color: white;
                border-radius: 4px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        layout = QVBoxLayout(self)

        # ---------- Header ----------
        header = QLabel("Budget Planner")
        header.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(header)

        # ---------- Form ----------
        form = QFormLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)

        self.cat_input = QLineEdit()
        self.desc_input = QLineEdit()
        self.amount_input = QLineEdit()

        form.addRow("Date:", self.date_edit)
        form.addRow("Category:", self.cat_input)
        form.addRow("Description:", self.desc_input)
        form.addRow("Amount:", self.amount_input)
        layout.addLayout(form)

        # ---------- Buttons ----------
        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("Add Expense")
        self.add_btn.clicked.connect(self.add_expense)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)

        self.pdf_btn = QPushButton("Generate Receipt PDF")
        self.pdf_btn.clicked.connect(self.generate_pdf)

        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.delete_btn)
        btn_row.addWidget(self.pdf_btn)
        layout.addLayout(btn_row)

        # ---------- Table ----------
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Date", "Category", "Description", "Amount (₦)"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        # Header styling
        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #1e1e1e;
                color: white;
                padding: 6px;
                border: 1px solid #333;
                font-weight: bold;
            }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

        # Row styling
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #181818;
                gridline-color: #333;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)

        layout.addWidget(self.table)

        # ---------- Total ----------
        self.total_lbl = QLabel("Total: ₦0.00")
        self.total_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.total_lbl)

    # ---------- Load ----------
    def load_expenses(self):
        self.table.setRowCount(0)
        rows = db_query(
            "SELECT id, date, category, description, amount FROM expenses ORDER BY date DESC"
        )

        total = 0.0
        for rid, date, cat, desc, amt in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            self.table.setItem(r, 0, QTableWidgetItem(date))
            self.table.setItem(r, 1, QTableWidgetItem(cat))
            self.table.setItem(r, 2, QTableWidgetItem(desc))

            amt_item = QTableWidgetItem(f"{amt:.2f}")
            amt_item.setData(Qt.UserRole, rid)  # SAFE row ID storage
            self.table.setItem(r, 3, amt_item)

            total += amt

        self.total_lbl.setText(f"Total: ₦{total:.2f}")

    # ---------- Add ----------
    def add_expense(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        cat = self.cat_input.text().strip()
        desc = self.desc_input.text().strip()
        amt_text = self.amount_input.text().strip()

        if not cat or not desc or not amt_text:
            QMessageBox.warning(self, "Warning", "All fields are required")
            return

        try:
            amt = float(amt_text)
        except ValueError:
            QMessageBox.warning(self, "Warning", "Amount must be a number")
            return

        db_execute(
            "INSERT INTO expenses (date, category, description, amount) VALUES (?, ?, ?, ?)",
            (date, cat, desc, amt)
        )

        self.cat_input.clear()
        self.desc_input.clear()
        self.amount_input.clear()
        self.load_expenses()

    # ---------- Delete ----------
    def delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Select an expense")
            return

        rid = self.table.item(row, 3).data(Qt.UserRole)
        if rid is None:
            QMessageBox.warning(self, "Error", "Invalid row")
            return

        confirm = QMessageBox.question(self, "Delete", "Delete this expense?")
        if confirm != QMessageBox.Yes:
            return

        db_execute("DELETE FROM expenses WHERE id=?", (rid,))
        self.load_expenses()

    # ---------- PDF ----------
    def generate_pdf(self):
        rows = db_query(
            "SELECT date, category, description, amount FROM expenses ORDER BY date DESC"
        )
        if not rows:
            QMessageBox.information(self, "No data", "No expenses to export")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", "expense_receipt.pdf", "PDF files (*.pdf)"
        )
        if not filename:
            return

        doc = SimpleDocTemplate(filename, pagesize=letter)
        elements = []

        data = [["Date", "Category", "Description", "Amount (₦)"]]
        for d, c, desc, a in rows:
            data.append([d, c, desc, f"{a:.2f}"])

        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), reportlab_colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), reportlab_colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, reportlab_colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # Chart (dark theme)
        fig, ax = plt.subplots(figsize=(6, 3), facecolor="#121212")
        ax.set_facecolor("#1e1e1e")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")

        agg = defaultdict(float)
        for _, cat, _, amt in rows:
            agg[cat] += amt

        ax.bar(agg.keys(), agg.values(), color="#FFB300")
        ax.set_title("Expenses by Category", color="white")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", facecolor="#121212")
        plt.close(fig)
        buf.seek(0)

        elements.append(PlatypusImage(buf, width=400, height=200))
        doc.build(elements)

        QMessageBox.information(self, "Saved", f"Saved PDF to {filename}")




# ------------------------
# Dashboard / Main Window
# ------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        init_db()
        self.setWindowTitle("Productivity Suite — Dashboard")
        self.resize(1100, 700)
        self.setup_ui()
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QLabel {
                color: #e9e9e9;
            }
            QPushButton {
                background-color: #1565C0;
                color: white;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QFrame {
                background-color: #1e1e1e;
            }
        """)

    def setup_ui(self):
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Sidebar
        sidebar = QVBoxLayout()
        sidebar_widget = QFrame()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(300)
        sidebar_widget.setFrameShape(QFrame.StyledPanel)

        title = QLabel("Productivity Suite")
        title.setFont(QFont("Times New Roman", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        sidebar.addWidget(title)
        sidebar.addSpacing(15)

        # Sidebar buttons
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_todo = QPushButton("To-Do")
        self.btn_pomodoro = QPushButton("Pomodoro")
        self.btn_analytics = QPushButton("Analytics")
        self.btn_budget = QPushButton("Budget")

        for b in [self.btn_dashboard, self.btn_todo, self.btn_pomodoro, self.btn_analytics, self.btn_budget]:
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            sidebar.addWidget(b)
        sidebar.addStretch()

        # Right: stacked content area
        content_layout = QVBoxLayout()
        content_widget = QFrame()
        content_widget.setLayout(content_layout)

        # Top header
        self.header_lbl = QLabel("Welcome — Dashboard")
        self.header_lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))
        content_layout.addWidget(self.header_lbl)

        # Stacked pages
        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages)

        # Instantiate widgets
        self.dashboard_tab = QWidget()
        self.todo_widget = ToDoWidget(parent=self)
        self.pomodoro_widget = PomodoroWidget(parent=self)
        self.analytics_widget = AnalyticsWidget(parent=self)
        self.budget_widget = BudgetWidget(parent=self)

        # Add pages to stacked widget
        self.pages.addWidget(self.dashboard_tab)    # index 0
        self.pages.addWidget(self.todo_widget)      # index 1
        self.pages.addWidget(self.pomodoro_widget)  # index 2
        self.pages.addWidget(self.analytics_widget) # index 3
        self.pages.addWidget(self.budget_widget)    # index 4

        # Dashboard layout
        d_layout = QVBoxLayout()
        self.dashboard_tab.setLayout(d_layout)
        d_title = QLabel("Dashboard Overview")
        d_title.setFont(QFont("Arial", 16, QFont.Bold))
        d_layout.addWidget(d_title)

        self.overview_label = QLabel("")
        self.overview_label.setFont(QFont("Arial", 12, QFont.Bold))
        d_layout.addWidget(self.overview_label)

        small_hr = QFrame()
        small_hr.setFrameShape(QFrame.HLine)
        small_hr.setStyleSheet("color: #555555;")
        d_layout.addWidget(small_hr)

        # Quick summary widgets
        quick_row = QHBoxLayout()
        quick_left = QVBoxLayout()
        quick_right = QVBoxLayout()
        quick_row.addLayout(quick_left, 1)
        quick_row.addLayout(quick_right, 2)
        d_layout.addLayout(quick_row)

        self.quick_tasks_lbl = QLabel("Tasks: 0")
        self.quick_pomo_lbl = QLabel("Pomodoros: 0")
        self.quick_focus_lbl = QLabel("Focus (min): 0")
        quick_left.addWidget(self.quick_tasks_lbl)
        quick_left.addWidget(self.quick_pomo_lbl)
        quick_left.addWidget(self.quick_focus_lbl)

        # Dashboard chart
        self.db_fig, self.db_ax = plt.subplots(figsize=(5, 3), facecolor="#121212")
        self.db_ax.set_facecolor("#1e1e1e")
        self.db_canvas = FigureCanvas(self.db_fig)
        quick_right.addWidget(self.db_canvas)

        # Connect sidebar buttons to pages and header
        self.btn_dashboard.clicked.connect(lambda: (self.pages.setCurrentIndex(0), self.set_header("Dashboard")))
        self.btn_todo.clicked.connect(lambda: (self.pages.setCurrentIndex(1), self.set_header("To-Do")))
        self.btn_pomodoro.clicked.connect(lambda: (self.pages.setCurrentIndex(2), self.set_header("Pomodoro")))
        self.btn_analytics.clicked.connect(lambda: (self.pages.setCurrentIndex(3), self.set_header("Analytics")))
        self.btn_budget.clicked.connect(lambda: (self.pages.setCurrentIndex(4), self.set_header("Budget")))

        # Put sidebar and content in main layout
        main_layout.addWidget(sidebar_widget)
        main_layout.addWidget(content_widget)

        # Refresh summary timer
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(2000)
        self.refresh_timer.timeout.connect(self.update_overview)
        self.refresh_timer.start()

        # Initial update
        self.update_overview()

    # Method to update the header text
    def set_header(self, text):
        self.header_lbl.setText(f"Welcome to {text}")

    # Update dashboard overview
    def update_overview(self):
        rows = db_query("SELECT COUNT(*) FROM tasks")
        total_tasks = rows[0][0] if rows else 0
        rows = db_query("SELECT COUNT(*) FROM pomodoros")
        total_pomos = rows[0][0] if rows else 0
        rows = db_query("SELECT SUM(amount) FROM expenses")
        total_spent = rows[0][0] if rows and rows[0][0] is not None else 0.0
        rows = db_query("SELECT SUM(duration) FROM pomodoros")
        total_focus_min = (rows[0][0] if rows and rows[0][0] is not None else 0) // 60

        self.quick_tasks_lbl.setText(f"Tasks: {total_tasks}")
        self.quick_pomo_lbl.setText(f"Pomodoros: {total_pomos}")
        self.quick_focus_lbl.setText(f"Focus (min): {total_focus_min}")
        self.overview_label.setText(f"Total spent: ₦{total_spent:.2f}")

        # Dashboard chart: pomodoros last 7 days
        self.db_ax.clear()
        rows = db_query("SELECT timestamp FROM pomodoros")
        dates = []
        for (ts,) in rows:
            try:
                dates.append(datetime.datetime.fromisoformat(ts).date())
            except:
                pass
        counts = Counter(dates)
        last7 = [datetime.date.today() - datetime.timedelta(days=i) for i in range(6, -1, -1)]
        x = [d.strftime("%b %d") for d in last7]
        y = [counts.get(d, 0) for d in last7]
        self.db_ax.bar(x, y, color="#FFB300")
        self.db_ax.set_title("Pomodoros (last 7 days)", color="white")
        self.db_ax.tick_params(axis='x', rotation=45, colors="white")
        self.db_ax.tick_params(axis='y', colors="white")
        self.db_fig.tight_layout()
        self.db_canvas.draw()

        # Refresh analytics widget
        self.analytics_widget.update_stats()


# ------------------------
# Run App
# ------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())