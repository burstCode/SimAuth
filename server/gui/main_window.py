import sys
import winreg
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCursor, QIcon, QPixmap, QPainter, QBrush, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QTextEdit,
    QLineEdit, QFormLayout, QGroupBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSystemTrayIcon, QMenu, QInputDialog, QMessageBox,
)

from config import config, AcRemoteConfig, save_config
from gui.server_thread import ServerThread


_STYLESHEET = """
QWidget {
    background-color: #0a0a0a;
    color: #e8e8e8;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow { background-color: #0a0a0a; }

QWidget#header_bar {
    background-color: #111111;
    border-bottom: 1px solid #1e1e1e;
}
QLabel#header_title {
    font-size: 16px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#header_status { color: #888888; font-size: 13px; }

QTabWidget::pane {
    border: none;
    background-color: #0a0a0a;
}
QTabWidget::tab-bar { alignment: left; }
QTabBar::tab {
    background-color: #111111;
    color: #777777;
    font-size: 13px;
    padding: 10px 24px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #ffffff;
    border-bottom: 2px solid #e51a20;
    background-color: #0a0a0a;
}
QTabBar::tab:hover:!selected { color: #bbbbbb; }

QLineEdit {
    background-color: #161616;
    color: #e8e8e8;
    border: 1px solid #2a2a2a;
    border-radius: 5px;
    padding: 6px 10px;
}
QLineEdit:focus { border-color: #e51a20; }

QGroupBox {
    border: 1px solid #222222;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    color: #888888;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QPushButton {
    background-color: #1e1e1e;
    color: #cccccc;
    border: 1px solid #333333;
    border-radius: 5px;
    padding: 6px 16px;
}
QPushButton:hover { background-color: #2a2a2a; color: #ffffff; }
QPushButton:pressed { background-color: #141414; }

QPushButton#primary_btn {
    background-color: #e51a20;
    color: #ffffff;
    border: none;
    padding: 8px 24px;
    font-weight: bold;
}
QPushButton#primary_btn:hover { background-color: #c21519; }
QPushButton#primary_btn:pressed { background-color: #a01015; }

QPushButton#danger_btn {
    background-color: transparent;
    color: #e51a20;
    border: 1px solid #e51a20;
    padding: 3px 10px;
    font-size: 12px;
}
QPushButton#danger_btn:hover { background-color: #1a0000; }

QPushButton#admin_btn {
    color: #e51a20;
    border-color: #e51a20;
}
QPushButton#admin_btn:hover { background-color: #1a0000; }

QTextEdit {
    background-color: #060606;
    color: #cccccc;
    border: none;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}

QTableWidget {
    background-color: #0d0d0d;
    color: #e8e8e8;
    gridline-color: #1e1e1e;
    border: none;
    selection-background-color: #1a0000;
    selection-color: #ffffff;
}
QTableWidget::item { padding: 4px 8px; }
QHeaderView::section {
    background-color: #161616;
    color: #888888;
    border: none;
    border-right: 1px solid #1e1e1e;
    border-bottom: 1px solid #1e1e1e;
    padding: 6px 8px;
    font-size: 12px;
}
QScrollBar:vertical {
    background: #0a0a0a;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical { background: #333333; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #444444; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QCheckBox { color: #cccccc; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #333333;
    border-radius: 3px;
    background: #161616;
}
QCheckBox::indicator:checked {
    background: #e51a20;
    border-color: #e51a20;
}

QLabel#status_normal { color: #4caf50; font-size: 12px; }
QLabel#status_admin  { color: #e51a20; font-size: 12px; font-weight: bold; }

QMenu {
    background-color: #161616;
    border: 1px solid #2a2a2a;
    color: #e8e8e8;
}
QMenu::item:selected { background-color: #e51a20; color: #ffffff; }
QMenu::separator { height: 1px; background: #2a2a2a; margin: 4px 0; }
"""

_LOG_COLORS = {
    "DEBUG":    "#555555",
    "INFO":     "#cccccc",
    "WARNING":  "#ffd54f",
    "ERROR":    "#ef5350",
    "CRITICAL": "#e51a20",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_tray_icon() -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QBrush(QColor("#e51a20")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, 24, 24)
    p.end()
    return QIcon(pix)


def _autostart_supported() -> bool:
    return sys.platform == "win32"


def _autostart_enabled() -> bool:
    if not _autostart_supported():
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run")
        winreg.QueryValueEx(key, "SimAuthServer")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _set_autostart(enabled: bool) -> None:
    if not _autostart_supported():
        return
    try:
        if getattr(sys, "frozen", False):
            # Compiled exe — run directly
            cmd = f'"{sys.executable}"'
        else:
            # Dev mode — run via Python interpreter
            script = Path(__file__).resolve().parent.parent / "gui_main.py"
            cmd = f'"{sys.executable}" "{script}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        if enabled:
            winreg.SetValueEx(key, "SimAuthServer", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "SimAuthServer")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        QMessageBox.warning(
            None, "Ошибка автозапуска",
            f"Не удалось изменить настройки автозапуска:\n{e}",
        )


# ── header bar ───────────────────────────────────────────────────────────────

class _HeaderBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("header_bar")
        self.setFixedHeight(44)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 0, 18, 0)
        lay.setSpacing(0)

        title = QLabel('SimAuth <span style="color: #555555; font-weight: normal;">Server</span>')
        title.setObjectName("header_title")
        title.setTextFormat(Qt.TextFormat.RichText)

        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        self._dot.setStyleSheet("border-radius: 5px; background-color: #555555;")
        self._status_lbl = QLabel("Запускается…")
        self._status_lbl.setObjectName("header_status")

        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(self._dot)
        lay.addSpacing(6)
        lay.addWidget(self._status_lbl)

    def set_running(self, running: bool, address: str = ""):
        if running:
            self._dot.setStyleSheet("border-radius: 5px; background-color: #4caf50;")
            self._status_lbl.setText(f"Запущен  –  {address}")
        else:
            self._dot.setStyleSheet("border-radius: 5px; background-color: #e51a20;")
            self._status_lbl.setText("Остановлен")


# ── logs tab ─────────────────────────────────────────────────────────────────

class LogsTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        lay.addWidget(self._view)

        bar = QHBoxLayout()
        bar.setContentsMargins(12, 6, 12, 6)
        bar.addStretch()
        clear_btn = QPushButton("Очистить журнал")
        clear_btn.clicked.connect(self._view.clear)
        bar.addWidget(clear_btn)
        lay.addLayout(bar)

    def append(self, levelname: str, message: str):
        color = _LOG_COLORS.get(levelname, "#cccccc")
        # Escape HTML special chars in message
        safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._view.append(f'<span style="color:{color};">{safe}</span>')
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())


# ── config tab ────────────────────────────────────────────────────────────────

class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(16)

        # ── server section ──
        server_box = QGroupBox("Параметры сервера")
        sf = QFormLayout(server_box)
        sf.setSpacing(10)
        sf.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._host     = QLineEdit(config.host)
        self._port     = QLineEdit(str(config.port))
        self._duration = QLineEdit(str(config.session_duration_minutes))
        self._tz       = QLineEdit(config.timezone)
        self._admin_pw = QLineEdit(config.admin_password)
        self._admin_pw.setEchoMode(QLineEdit.EchoMode.Password)

        sf.addRow("Хост:", self._host)
        sf.addRow("Порт:", self._port)
        sf.addRow("Длительность сессии (мин):", self._duration)
        sf.addRow("Часовой пояс:", self._tz)
        sf.addRow("Пароль администратора:", self._admin_pw)
        lay.addWidget(server_box)

        # ── AC remote section ──
        ac_box = QGroupBox("Настройки AC сервера")
        af = QFormLayout(ac_box)
        af.setSpacing(10)
        af.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        rc = config.ac_remote
        self._ac_ip   = QLineEdit(rc.server_ip)
        self._ac_http = QLineEdit(str(rc.server_http_port) if rc.server_http_port else "")
        self._ac_pass = QLineEdit(rc.password or "")
        self._ac_car  = QLineEdit(rc.car)
        self._ac_skin = QLineEdit(rc.skin)

        af.addRow("IP сервера AC:", self._ac_ip)
        af.addRow("HTTP порт (CM):", self._ac_http)
        af.addRow("Пароль сервера:", self._ac_pass)
        af.addRow("Машина:", self._ac_car)
        af.addRow("Скин:", self._ac_skin)
        lay.addWidget(ac_box)

        # ── autostart ──
        self._autostart = QCheckBox("Запускать автоматически при старте Windows")
        self._autostart.setChecked(_autostart_enabled())
        if not _autostart_supported():
            self._autostart.setEnabled(False)
            self._autostart.setToolTip("Только Windows")
        lay.addWidget(self._autostart)

        lay.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def _save(self):
        try:
            config.host = self._host.text().strip() or "0.0.0.0"
            config.port = int(self._port.text().strip())
            config.session_duration_minutes = int(self._duration.text().strip())
            config.timezone = self._tz.text().strip() or "Europe/Moscow"
            config.admin_password = self._admin_pw.text() or "admin"
            config.ac_remote = AcRemoteConfig(
                server_ip=self._ac_ip.text().strip(),
                server_http_port=int(self._ac_http.text().strip() or "0"),
                password=self._ac_pass.text().strip() or None,
                car=self._ac_car.text().strip(),
                skin=self._ac_skin.text().strip(),
            )
            save_config()
            _set_autostart(self._autostart.isChecked())
            QMessageBox.information(
                self, "Сохранено",
                "Настройки сохранены.\nДля применения порта и хоста требуется перезапуск сервера.",
            )
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка ввода", str(e))


# ── database tab ──────────────────────────────────────────────────────────────

def _fmt_lap(ms: int | None) -> str:
    if ms is None:
        return "–"
    m, rem = divmod(ms, 60000)
    return f"{m}:{rem / 1000:06.3f}"


def _fmt_duration(s) -> str:
    """Actual elapsed time if both timestamps exist, otherwise planned duration."""
    if s.started_at and s.completed_at:
        total = int((s.completed_at - s.started_at).total_seconds())
        m, sec = divmod(total, 60)
        return f"{m} мин {sec:02d} с"
    if s.started_at and not s.completed_at:
        return "активна"
    return f"{s.duration_minutes} мин (план)"


class DatabaseTab(QWidget):
    _P_DEL_COL = 5   # participants delete column index
    _S_DEL_COL = 7   # sessions delete column index
    _DEL_COL_W = 90  # fixed width for delete columns

    def __init__(self):
        super().__init__()
        self._admin = False
        self._refreshing = False  # guard against itemChanged firing during fill

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)

        self._admin_ind = QLabel("● Обычный режим")
        self._admin_ind.setObjectName("status_normal")
        self._admin_btn = QPushButton("Режим администратора")
        self._admin_btn.setObjectName("admin_btn")
        self._admin_btn.clicked.connect(self._toggle_admin)

        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        toolbar.addWidget(self._admin_ind)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._admin_btn)
        lay.addLayout(toolbar)

        # ── participants table ──
        # Cols: ID | Фамилия | Имя | Отчество | Зарегистрирован | [Удалить]
        self._p_tbl = self._make_table(
            ["ID", "Фамилия", "Имя", "Отчество", "Зарегистрирован", ""]
        )
        h = self._p_tbl.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(self._P_DEL_COL, QHeaderView.ResizeMode.Fixed)
        self._p_tbl.setColumnWidth(self._P_DEL_COL, self._DEL_COL_W)
        self._p_tbl.setColumnHidden(self._P_DEL_COL, True)
        # Inline editing enabled (DoubleClicked); flags on items control which cells
        self._p_tbl.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        self._p_tbl.itemChanged.connect(self._on_participant_changed)
        self._p_tbl.verticalHeader().setDefaultSectionSize(44)

        # ── sessions table ──
        # Cols: ID | Участник | ПК | Статус | Дата | Длит. | Лучший круг | [Удалить]
        self._s_tbl = self._make_table(
            ["ID", "Участник", "ПК", "Статус", "Дата", "Длит.", "Лучший круг", ""]
        )
        h2 = self._s_tbl.horizontalHeader()
        h2.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        h2.setSectionResizeMode(self._S_DEL_COL, QHeaderView.ResizeMode.Fixed)
        self._s_tbl.setColumnWidth(self._S_DEL_COL, self._DEL_COL_W)
        self._s_tbl.setColumnHidden(self._S_DEL_COL, True)

        # sub-tabs
        self._sub = QTabWidget()
        self._sub.addTab(self._p_tbl, "Участники")
        self._sub.addTab(self._s_tbl, "Сессии")
        lay.addWidget(self._sub)

        self.refresh()

    @staticmethod
    def _make_table(headers: list[str]) -> QTableWidget:
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setStretchLastSection(False)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(True)
        t.setAlternatingRowColors(True)
        return t

    def refresh(self):
        try:
            from sqlalchemy.orm import Session as DbSession, joinedload
            from database import engine
            from models import Participant, GameSession

            with DbSession(engine) as db:
                participants = db.query(Participant).order_by(Participant.id.desc()).all()
                # joinedload prevents lazy-load errors after session closes
                sessions = (
                    db.query(GameSession)
                    .options(joinedload(GameSession.participant))
                    .order_by(GameSession.id.desc())
                    .limit(300)
                    .all()
                )
                # detach objects so they survive outside the session
                db.expunge_all()

            self._fill_participants(participants)
            self._fill_sessions(sessions)
        except Exception:
            pass  # DB not ready yet on first launch

    def _fill_participants(self, rows):
        self._refreshing = True
        self._p_tbl.setRowCount(len(rows))
        editable_flag = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        readonly_flag = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        for r, p in enumerate(rows):
            items = [
                (0, str(p.id),                         readonly_flag),
                (1, p.last_name,                       editable_flag if self._admin else readonly_flag),
                (2, p.first_name,                      editable_flag if self._admin else readonly_flag),
                (3, p.middle_name or "",               editable_flag if self._admin else readonly_flag),
                (4, p.created_at.strftime("%d.%m.%Y %H:%M"), readonly_flag),
            ]
            for col, text, flags in items:
                item = QTableWidgetItem(text)
                item.setFlags(flags)
                self._p_tbl.setItem(r, col, item)

            btn = QPushButton("Удалить")
            btn.setObjectName("danger_btn")
            btn.clicked.connect(lambda _, pid=p.id: self._delete_participant(pid))
            self._p_tbl.setCellWidget(r, self._P_DEL_COL, btn)

        self._refreshing = False

    def _fill_sessions(self, rows):
        self._s_tbl.setRowCount(len(rows))
        for r, s in enumerate(rows):
            name = s.participant.display_name if s.participant else "–"
            data = [
                str(s.id), name, s.pc_id, s.status.value,
                s.play_date.strftime("%d.%m.%Y"),
                _fmt_duration(s),
                _fmt_lap(s.best_lap_ms),
            ]
            for col, text in enumerate(data):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self._s_tbl.setItem(r, col, item)

            btn = QPushButton("Удалить")
            btn.setObjectName("danger_btn")
            btn.clicked.connect(lambda _, sid=s.id: self._delete_session(sid))
            self._s_tbl.setCellWidget(r, self._S_DEL_COL, btn)

    def _toggle_admin(self):
        if self._admin:
            self._admin = False
            self._admin_btn.setText("Режим администратора")
            self._admin_ind.setText("● Обычный режим")
            self._admin_ind.setObjectName("status_normal")
        else:
            pw, ok = QInputDialog.getText(
                self, "Вход в режим администратора",
                "Введите пароль:", QLineEdit.EchoMode.Password,
            )
            if not ok:
                return
            if pw != config.admin_password:
                QMessageBox.warning(self, "Ошибка", "Неверный пароль")
                return
            QMessageBox.warning(
                self, "Режим суперадминистратора",
                "Вы входите в режим суперадминистратора.\n\n"
                "В этом режиме доступны редактирование и удаление "
                "данных участников и сессий. Операции необратимы.\n\n"
                "По завершении работы обязательно выйдите из этого режима.",
            )
            self._admin = True
            self._admin_btn.setText("Выйти из режима администратора")
            self._admin_ind.setText("● Режим администратора")
            self._admin_ind.setObjectName("status_admin")

        # Re-polish label so CSS objectName change takes effect
        self._admin_ind.style().unpolish(self._admin_ind)
        self._admin_ind.style().polish(self._admin_ind)

        # Show / hide delete columns
        self._p_tbl.setColumnHidden(self._P_DEL_COL, not self._admin)
        self._s_tbl.setColumnHidden(self._S_DEL_COL, not self._admin)

        self.refresh()

    def _on_participant_changed(self, item: QTableWidgetItem):
        if self._refreshing or not self._admin:
            return
        col = item.column()
        if col not in (1, 2, 3):
            return
        row = item.row()
        id_item = self._p_tbl.item(row, 0)
        if not id_item:
            return
        pid = int(id_item.text())
        col_to_field = {1: "last_name", 2: "first_name", 3: "middle_name"}
        field = col_to_field[col]
        value = item.text().strip() or None

        try:
            from sqlalchemy.orm import Session as DbSession
            from database import engine
            from models import Participant

            with DbSession(engine) as db:
                p = db.get(Participant, pid)
                if p:
                    setattr(p, field, value or "")
                    p.full_name = " ".join(
                        x for x in [p.last_name, p.first_name, p.middle_name] if x
                    )
                    db.commit()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

    def _delete_participant(self, pid: int):
        reply = QMessageBox.question(
            self, "Удаление участника",
            f"Удалить участника #{pid} и все его сессии?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from sqlalchemy.orm import Session as DbSession
            from database import engine
            from models import Participant, IdentityDocument, GameSession

            with DbSession(engine) as db:
                db.query(GameSession).filter(GameSession.participant_id == pid).delete()
                db.query(IdentityDocument).filter(IdentityDocument.participant_id == pid).delete()
                p = db.get(Participant, pid)
                if p:
                    db.delete(p)
                db.commit()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        self.refresh()

    def _delete_session(self, sid: int):
        reply = QMessageBox.question(
            self, "Удаление сессии",
            f"Удалить сессию #{sid}?\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            from sqlalchemy.orm import Session as DbSession
            from database import engine
            from models import GameSession

            with DbSession(engine) as db:
                s = db.get(GameSession, sid)
                if s:
                    db.delete(s)
                db.commit()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
        self.refresh()


# ── main window ───────────────────────────────────────────────────────────────

class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimAuth Server")
        self.setMinimumSize(960, 640)
        self.resize(1140, 720)
        self.setStyleSheet(_STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = _HeaderBar()
        root.addWidget(self._header)

        self._tabs = QTabWidget()
        self._logs_tab   = LogsTab()
        self._config_tab = ConfigTab()
        self._db_tab     = DatabaseTab()
        self._tabs.addTab(self._logs_tab,   "Журнал")
        self._tabs.addTab(self._config_tab, "Конфигурация")
        self._tabs.addTab(self._db_tab,     "База данных")
        root.addWidget(self._tabs)

        self._setup_tray()

        self._server = ServerThread()
        self._server.log_record.connect(self._logs_tab.append)
        self._server.server_started.connect(self._on_started)
        self._server.server_stopped.connect(self._on_stopped)
        self._server.start()

    # ── tray ──

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(_make_tray_icon(), self)
        self._tray.setToolTip("SimAuth Server")

        menu = QMenu()
        self._toggle_act = menu.addAction("Скрыть окно")
        self._toggle_act.triggered.connect(self._toggle_visibility)
        menu.addSeparator()
        quit_act = menu.addAction("Выйти")
        quit_act.triggered.connect(self._quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
            self._toggle_act.setText("Показать окно")
        else:
            self.show()
            self.activateWindow()
            self._toggle_act.setText("Скрыть окно")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visibility()

    # ── server signals ──

    def _on_started(self):
        addr = f"{config.host}:{config.port}"
        self._header.set_running(True, addr)
        self._tray.setToolTip(f"SimAuth Server – {addr}")
        self._logs_tab.append("INFO", f"00:00:00  Сервер запущен на http://{addr}")

    def _on_stopped(self):
        self._header.set_running(False)
        self._tray.setToolTip("SimAuth Server – остановлен")

    # ── window close → tray ──

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self._toggle_act.setText("Показать окно")
        self._tray.showMessage(
            "SimAuth Server",
            "Сервер продолжает работать в фоновом режиме.",
            QSystemTrayIcon.MessageIcon.Information,
            2500,
        )

    def _count_active_sessions(self) -> int:
        try:
            from sqlalchemy.orm import Session as DbSession
            from database import engine
            from models import GameSession, SessionStatus

            with DbSession(engine) as db:
                return db.query(GameSession).filter(
                    GameSession.status == SessionStatus.ACTIVE
                ).count()
        except Exception:
            return 0

    def _quit(self):
        active = self._count_active_sessions()
        if active > 0:
            noun = (
                "игрок" if active == 1
                else "игрока" if active in (2, 3, 4)
                else "игроков"
            )
            reply = QMessageBox.warning(
                self, "Активные игроки",
                f"Прямо сейчас {active} {noun} в активной сессии.\n"
                "При закрытии сервера их прогресс может быть утерян.\n\n"
                "Всё равно завершить работу?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._tray.hide()
        self._server.stop()
        self._server.wait(4000)
        QApplication.quit()
