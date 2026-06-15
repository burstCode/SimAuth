import time
from typing import Callable

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QFormLayout,
)

import api_client
import game_manager
from config import config
from ui.settings_dialog import ServerSettingsDialog
from ui.styles import DARK


# ---------------------------------------------------------------------------
# Фоновые потоки
# ---------------------------------------------------------------------------

class PollingWorker(QThread):
    session_found = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, pc_id: str, interval: int):
        super().__init__()
        self._pc_id = pc_id
        self._interval = interval
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                session = api_client.get_pending_session(self._pc_id)
                if session:
                    self.session_found.emit(session)
                    return
            except Exception as e:
                self.error.emit(str(e))
            time.sleep(self._interval)


class ApiWorker(QThread):
    success = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn: Callable):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            self.success.emit(self._fn())
        except api_client.ApiError as e:
            self.error.emit(e.detail)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Экран регистрации
# ---------------------------------------------------------------------------

class PassportTab(QWidget):
    submit = pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout()
        outer.setContentsMargins(40, 30, 40, 30)
        outer.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name = QLineEdit(); self._name.setPlaceholderText("Иванов Иван Иванович")
        self._series = QLineEdit(); self._series.setPlaceholderText("4510"); self._series.setMaxLength(4)
        self._number = QLineEdit(); self._number.setPlaceholderText("123456"); self._number.setMaxLength(6)

        def lbl(t):
            l = QLabel(t); l.setObjectName("form_label"); return l

        form.addRow(lbl("ФИО"), self._name)
        form.addRow(lbl("Серия"), self._series)
        form.addRow(lbl("Номер"), self._number)

        self._btn = QPushButton("Начать сессию")
        self._btn.setObjectName("form_btn")
        self._btn.clicked.connect(self._on_submit)

        outer.addLayout(form)
        outer.addSpacing(8)
        outer.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addStretch()
        self.setLayout(outer)

    def _on_submit(self):
        n, s, num = self._name.text().strip(), self._series.text().strip(), self._number.text().strip()
        if n and s and num:
            self.submit.emit(n, s, num)

    def set_enabled(self, v: bool):
        for w in (self._name, self._series, self._number, self._btn):
            w.setEnabled(v)


class PhoneTab(QWidget):
    submit = pyqtSignal(str, str, str)
    otp_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout()
        outer.setContentsMargins(40, 30, 40, 30)
        outer.setSpacing(12)

        def lbl(t):
            l = QLabel(t); l.setObjectName("form_label"); return l

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._name = QLineEdit(); self._name.setPlaceholderText("Иванов Иван Иванович")
        self._phone = QLineEdit(); self._phone.setPlaceholderText("+79991234567")
        form.addRow(lbl("ФИО"), self._name)
        form.addRow(lbl("Телефон"), self._phone)
        outer.addLayout(form)

        self._otp_section = QWidget()
        olay = QVBoxLayout(self._otp_section)
        olay.setContentsMargins(0, 0, 0, 0); olay.setSpacing(6)
        olay.addWidget(lbl("Код из SMS / Telegram"))
        self._otp = QLineEdit(); self._otp.setPlaceholderText("000000"); self._otp.setMaxLength(6)
        olay.addWidget(self._otp)
        self._otp_section.hide()
        outer.addWidget(self._otp_section)
        outer.addSpacing(8)

        btn_row = QHBoxLayout()
        self._otp_btn = QPushButton("Отправить код"); self._otp_btn.setObjectName("otp_btn")
        self._otp_btn.clicked.connect(self._on_send_otp)
        self._submit_btn = QPushButton("Начать сессию"); self._submit_btn.setObjectName("form_btn")
        self._submit_btn.setEnabled(False)
        self._submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(self._otp_btn); btn_row.addStretch(); btn_row.addWidget(self._submit_btn)
        outer.addLayout(btn_row); outer.addStretch()
        self.setLayout(outer)
        self._otp_sent = False

    def _on_send_otp(self):
        phone = self._phone.text().strip()
        if phone:
            self._otp_btn.setEnabled(False)
            self.otp_requested.emit(phone)

    def show_otp_field(self):
        self._otp_section.show(); self._submit_btn.setEnabled(True); self._otp_sent = True

    def reset_otp_button(self):
        self._otp_btn.setEnabled(True)

    def _on_submit(self):
        n, p, o = self._name.text().strip(), self._phone.text().strip(), self._otp.text().strip()
        if n and p and o:
            self.submit.emit(n, p, o)

    def set_enabled(self, v: bool):
        self._name.setEnabled(v); self._phone.setEnabled(v); self._otp.setEnabled(v)
        self._otp_btn.setEnabled(v and not self._otp_sent)
        self._submit_btn.setEnabled(v and self._otp_sent)


class RegistrationScreen(QWidget):
    session_created = pyqtSignal(dict)

    def __init__(self, pc_id: str):
        super().__init__()
        self._pc_id = pc_id
        self._worker: ApiWorker | None = None
        self._otp_worker: ApiWorker | None = None

        root = QVBoxLayout()
        root.setContentsMargins(60, 40, 60, 20); root.setSpacing(0)

        title = QLabel("SimAuth"); title.setObjectName("title"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("Зарегистрируйтесь для начала сессии")
        hint.setObjectName("subtitle"); hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(title); root.addSpacing(4); root.addWidget(hint); root.addSpacing(24)

        self._tabs = QTabWidget()
        self._passport_tab = PassportTab()
        self._phone_tab = PhoneTab()
        self._tabs.addTab(self._passport_tab, "Паспорт")
        self._tabs.addTab(self._phone_tab, "Телефон")
        root.addWidget(self._tabs)

        self._error = QLabel()
        self._error.setObjectName("error"); self._error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error.setWordWrap(True); self._error.hide()
        root.addSpacing(8); root.addWidget(self._error); root.addStretch()

        # Нижняя строка: станция слева, кнопка настроек справа
        bottom_row = QHBoxLayout()
        status = QLabel(f"Рабочая станция: {pc_id}")
        status.setObjectName("status")
        settings_btn = QPushButton("⚙ Настройки сервера")
        settings_btn.setObjectName("otp_btn")
        settings_btn.clicked.connect(self.settings_requested)
        bottom_row.addWidget(status)
        bottom_row.addStretch()
        bottom_row.addWidget(settings_btn)
        root.addLayout(bottom_row)
        self.setLayout(root)

        self._passport_tab.submit.connect(self._on_passport_submit)
        self._phone_tab.otp_requested.connect(self._on_otp_request)
        self._phone_tab.submit.connect(self._on_phone_submit)

    def _on_passport_submit(self, name: str, series: str, number: str):
        self._set_busy(True); self._clear_error()
        self._worker = ApiWorker(lambda: (
            api_client.register_passport(name, series, number),
            api_client.create_session("passport", [series, number], self._pc_id),
        )[-1])
        self._worker.success.connect(self._on_session_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_otp_request(self, phone: str):
        self._clear_error()
        self._otp_worker = ApiWorker(lambda: api_client.request_otp(phone))
        self._otp_worker.success.connect(lambda _: self._phone_tab.show_otp_field())
        self._otp_worker.error.connect(self._on_otp_error)
        self._otp_worker.start()

    def _on_phone_submit(self, name: str, phone: str, otp: str):
        self._set_busy(True); self._clear_error()
        self._worker = ApiWorker(lambda: (
            api_client.register_phone(name, phone, otp),
            api_client.create_session("phone", [phone], self._pc_id),
        )[-1])
        self._worker.success.connect(self._on_session_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_session_ready(self, session: dict):
        self._set_busy(False); self.session_created.emit(session)

    def _on_error(self, msg: str):
        self._set_busy(False); self._show_error(msg)

    def _on_otp_error(self, msg: str):
        self._phone_tab.reset_otp_button(); self._show_error(msg)

    settings_requested = pyqtSignal()

    def _set_busy(self, busy: bool):
        self._passport_tab.set_enabled(not busy); self._phone_tab.set_enabled(not busy)

    def _show_error(self, msg: str):
        self._error.setText(msg); self._error.show()

    def _clear_error(self):
        self._error.hide(); self._error.clear()


# ---------------------------------------------------------------------------
# Экран «Готов к старту»
# ---------------------------------------------------------------------------

class ReadyScreen(QWidget):
    ready_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(20); lay.setContentsMargins(60, 60, 60, 60)

        greeting = QLabel("Добро пожаловать!"); greeting.setObjectName("title")
        greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label = QLabel(); self.name_label.setObjectName("name")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.duration_label = QLabel(); self.duration_label.setObjectName("subtitle")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("ГОТОВ К СТАРТУ"); btn.setObjectName("ready")
        btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.clicked.connect(self.ready_clicked)

        lay.addStretch()
        lay.addWidget(greeting); lay.addSpacing(10)
        lay.addWidget(self.name_label); lay.addWidget(self.duration_label)
        lay.addSpacing(30)
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()
        self.setLayout(lay)

    def set_session(self, session: dict):
        self.name_label.setText(session["participant"]["full_name"])
        self.duration_label.setText(f"Длительность сессии: {session['duration_minutes']} мин")


# ---------------------------------------------------------------------------
# Экран «Игра идёт» (загрузка → обратный отсчёт)
# ---------------------------------------------------------------------------

class ActiveScreen(QWidget):
    time_expired = pyqtSignal()
    tick = pyqtSignal(int)  # remaining seconds, каждую секунду

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout()
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setSpacing(20); outer.setContentsMargins(60, 60, 60, 60)

        self._inner = QStackedWidget()

        # --- Страница 0: загрузка ---
        load_w = QWidget()
        load_lay = QVBoxLayout(load_w)
        load_lay.setAlignment(Qt.AlignmentFlag.AlignCenter); load_lay.setSpacing(16)
        self._load_name = QLabel(); self._load_name.setObjectName("name")
        self._load_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        load_hint = QLabel("Запуск игры, подождите..."); load_hint.setObjectName("subtitle")
        load_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grace_label = QLabel(); self._grace_label.setObjectName("status")
        self._grace_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        load_lay.addStretch()
        load_lay.addWidget(self._load_name); load_lay.addWidget(load_hint)
        load_lay.addSpacing(8); load_lay.addWidget(self._grace_label)
        load_lay.addStretch()

        # --- Страница 1: обратный отсчёт ---
        play_w = QWidget()
        play_lay = QVBoxLayout(play_w)
        play_lay.setAlignment(Qt.AlignmentFlag.AlignCenter); play_lay.setSpacing(20)
        self._play_name = QLabel(); self._play_name.setObjectName("subtitle")
        self._play_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("Осталось времени"); hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label = QLabel("10:00"); self.timer_label.setObjectName("timer")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        play_lay.addStretch()
        play_lay.addWidget(self._play_name); play_lay.addSpacing(20)
        play_lay.addWidget(hint); play_lay.addWidget(self.timer_label)
        play_lay.addStretch()

        self._inner.addWidget(load_w)   # 0 — загрузка
        self._inner.addWidget(play_w)   # 1 — отсчёт

        outer.addWidget(self._inner)
        self.setLayout(outer)

        self._remaining = 0
        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._tick)

        # Таймер обратного отсчёта для grace label
        self._grace_remaining = 0
        self._grace_ticker = QTimer(self)
        self._grace_ticker.timeout.connect(self._grace_tick)

    def show_loading(self, full_name: str, grace_seconds: int):
        self._load_name.setText(full_name)
        self._grace_remaining = grace_seconds
        self._update_grace_label()
        self._grace_ticker.start(1000)
        self._inner.setCurrentIndex(0)

    def start_countdown(self, duration_minutes: int, full_name: str):
        self._grace_ticker.stop()
        self._play_name.setText(full_name)
        self._remaining = duration_minutes * 60
        self._update_timer_label()
        self._inner.setCurrentIndex(1)
        self._ticker.start(1000)

    def stop(self):
        self._ticker.stop()
        self._grace_ticker.stop()

    def _tick(self):
        self._remaining -= 1
        self._update_timer_label()
        self.tick.emit(self._remaining)
        if self._remaining <= 0:
            self._ticker.stop()
            self.time_expired.emit()

    def _grace_tick(self):
        self._grace_remaining -= 1
        self._update_grace_label()
        if self._grace_remaining <= 0:
            self._grace_ticker.stop()

    def _update_timer_label(self):
        m, s = divmod(max(self._remaining, 0), 60)
        self.timer_label.setText(f"{m:02d}:{s:02d}")

    def _update_grace_label(self):
        if self._grace_remaining > 0:
            self._grace_label.setText(f"Таймер стартует через {self._grace_remaining} сек")
        else:
            self._grace_label.setText("")


# ---------------------------------------------------------------------------
# Экран «Игра закрылась» (неожиданно)
# ---------------------------------------------------------------------------

class GameCrashedScreen(QWidget):
    restart_clicked = pyqtSignal()
    finish_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(20); lay.setContentsMargins(60, 60, 60, 60)

        title = QLabel("Игра закрылась"); title.setObjectName("crashed_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Осталось времени сессии"); hint.setObjectName("subtitle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._remaining_label = QLabel("--:--"); self._remaining_label.setObjectName("crashed_timer")
        self._remaining_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        note = QLabel("Таймер продолжает идти"); note.setObjectName("status")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)

        restart_btn = QPushButton("Перезапустить игру"); restart_btn.setObjectName("restart_btn")
        restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restart_btn.clicked.connect(self.restart_clicked)

        finish_btn = QPushButton("Завершить сессию"); finish_btn.setObjectName("finish_btn")
        finish_btn.clicked.connect(self.finish_clicked)

        lay.addStretch()
        lay.addWidget(title); lay.addSpacing(10)
        lay.addWidget(hint); lay.addWidget(self._remaining_label); lay.addWidget(note)
        lay.addSpacing(30)
        lay.addWidget(restart_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addSpacing(10)
        lay.addWidget(finish_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()
        self.setLayout(lay)

    def update_remaining(self, seconds: int):
        m, s = divmod(max(seconds, 0), 60)
        self._remaining_label.setText(f"{m:02d}:{s:02d}")


# ---------------------------------------------------------------------------
# Экран «Сессия завершена»
# ---------------------------------------------------------------------------

class CompleteScreen(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout()
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(20); lay.setContentsMargins(60, 60, 60, 60)

        title = QLabel("Сессия завершена!"); title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label = QLabel(); self.result_label.setObjectName("result")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.note_label = QLabel("Результат сохранён"); self.note_label.setObjectName("subtitle")
        self.note_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lay.addStretch()
        lay.addWidget(title); lay.addSpacing(20)
        lay.addWidget(self.result_label); lay.addWidget(self.note_label)
        lay.addStretch()
        self.setLayout(lay)

    def set_result(self, best_lap_ms: int | None):
        if best_lap_ms:
            m, ms = divmod(best_lap_ms, 60000)
            self.result_label.setText(f"Лучший круг: {m}:{ms/1000:06.3f}")
        else:
            self.result_label.setText("Круги не засчитаны")


# ---------------------------------------------------------------------------
# Главное окно
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    _IDX_REGISTER = 0
    _IDX_READY    = 1
    _IDX_ACTIVE   = 2
    _IDX_COMPLETE = 3
    _IDX_CRASHED  = 4

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimAuth Agent")
        self.setStyleSheet(DARK)
        self.showFullScreen()

        self._session: dict | None = None
        self._process = None
        self._poller: PollingWorker | None = None
        self._finishing = False  # защита от двойного вызова _finish_session

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._reg = RegistrationScreen(config.pc_id)
        self._ready = ReadyScreen()
        self._active = ActiveScreen()
        self._complete = CompleteScreen()
        self._crashed = GameCrashedScreen()

        for w in (self._reg, self._ready, self._active, self._complete, self._crashed):
            self._stack.addWidget(w)

        self._reg.session_created.connect(self._on_session_found)
        self._reg.settings_requested.connect(self._open_settings)
        self._ready.ready_clicked.connect(self._on_ready)
        self._active.time_expired.connect(self._on_time_expired)
        self._active.tick.connect(self._crashed.update_remaining)
        self._crashed.restart_clicked.connect(self._restart_game)
        self._crashed.finish_clicked.connect(self._on_time_expired)

        # Watchdog: проверяет, жив ли процесс игры
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(3000)
        self._watchdog.timeout.connect(self._check_game_alive)

        # Grace timer: отсчёт до старта таймера сессии
        self._grace_timer = QTimer(self)
        self._grace_timer.setSingleShot(True)
        self._grace_timer.timeout.connect(self._start_countdown)

        # Lap tracker: каждые 2 сек читает лучший круг из shared memory AC
        self._live_best_lap: int | None = None
        self._lap_tracker = QTimer(self)
        self._lap_tracker.setInterval(2000)
        self._lap_tracker.timeout.connect(self._update_live_lap)

        self._show_registration()

    # --- Настройки сервера ---

    def _open_settings(self):
        # Останавливаем поллер: пока открыт диалог, не хотим внезапно
        # переключиться на ReadyScreen из-за найденной сессии
        self._stop_polling()
        dlg = ServerSettingsDialog(self)
        dlg.exec()
        # Возобновляем только если всё ещё на экране регистрации
        if self._stack.currentIndex() == self._IDX_REGISTER:
            self._poller = PollingWorker(config.pc_id, config.poll_interval_seconds)
            self._poller.session_found.connect(self._on_session_found)
            self._poller.start()

    # --- Регистрация / поллинг ---

    def _show_registration(self):
        self._finishing = False
        self._stack.setCurrentIndex(self._IDX_REGISTER)
        self._poller = PollingWorker(config.pc_id, config.poll_interval_seconds)
        self._poller.session_found.connect(self._on_session_found)
        self._poller.start()

    def _stop_polling(self):
        if self._poller:
            self._poller.stop()
            self._poller = None

    def _on_session_found(self, session: dict):
        if self._stack.currentIndex() != self._IDX_REGISTER:
            return
        self._stop_polling()
        self._session = session
        self._ready.set_session(session)
        self._stack.setCurrentIndex(self._IDX_READY)

    # --- Старт игры ---

    def _on_ready(self):
        if not self._session:
            return
        player_name = self._session["participant"]["full_name"]
        try:
            game_manager.patch_race_ini(player_name)
            self._process = game_manager.launch_game()
            api_client.start_session(self._session["id"])
        except Exception as e:
            self.setWindowTitle(f"SimAuth Agent — Ошибка: {e}")
            return

        self._live_best_lap = None
        self._active.show_loading(player_name, config.launch_grace_seconds)
        self._stack.setCurrentIndex(self._IDX_ACTIVE)

        self._watchdog.start()
        self._grace_timer.start(config.launch_grace_seconds * 1000)

    def _start_countdown(self):
        """Вызывается после grace-периода — стартует реальный отсчёт."""
        if not self._session:
            return
        player_name = self._session["participant"]["full_name"]
        self._active.start_countdown(self._session["duration_minutes"], player_name)
        self._lap_tracker.start()

    def _update_live_lap(self):
        """Каждые 2 сек опрашивает shared memory AC и сохраняет лучший круг."""
        t = game_manager.read_best_lap_live()
        if t and (self._live_best_lap is None or t < self._live_best_lap):
            self._live_best_lap = t

    # --- Watchdog ---

    def _check_game_alive(self):
        if self._finishing:
            return
        if self._process and not game_manager.is_game_running(self._process):
            self._watchdog.stop()
            self._lap_tracker.stop()
            # Финальное чтение (AC только что умер, но SM может ещё быть доступна)
            self._update_live_lap()
            self._active.stop()
            self._crashed.update_remaining(self._active._remaining)
            self._stack.setCurrentIndex(self._IDX_CRASHED)

    def _restart_game(self):
        if not self._session:
            return
        player_name = self._session["participant"]["full_name"]
        try:
            game_manager.patch_race_ini(player_name)
            self._process = game_manager.launch_game()
        except Exception:
            return

        # Если grace ещё не истёк — возвращаемся к экрану загрузки,
        # иначе сразу к таймеру (start_countdown уже был вызван)
        if self._grace_timer.isActive():
            self._active.show_loading(player_name, self._grace_timer.remainingTime() // 1000)
        else:
            # Возобновляем отсчёт с места остановки
            self._active._ticker.start(1000)

        self._stack.setCurrentIndex(self._IDX_ACTIVE)
        self._watchdog.start()

    # --- Таймер истёк или «Завершить» нажата ---

    def _on_time_expired(self):
        if self._finishing:
            return
        self._finishing = True
        self._grace_timer.stop()
        self._watchdog.stop()
        self._lap_tracker.stop()
        # Последнее чтение из shared memory пока AC ещё жива
        self._update_live_lap()
        self._active.stop()
        if self._process:
            game_manager.kill_game(self._process)
        QTimer.singleShot(2000, self._finish_session)

    def _finish_session(self):
        player_name = self._session["participant"]["full_name"] if self._session else ""
        # Приоритет: shared memory (собрана во время сессии)
        # Запасной вариант: race_out.json (работает только при нормальном выходе из AC)
        best_lap = self._live_best_lap or game_manager.read_best_lap_from_file(player_name)
        try:
            api_client.complete_session(self._session["id"], best_lap)
        except Exception:
            pass

        self._complete.set_result(best_lap)
        self._stack.setCurrentIndex(self._IDX_COMPLETE)
        QTimer.singleShot(10_000, self._reset)

    def _reset(self):
        self._session = None
        self._process = None
        self._live_best_lap = None
        self._lap_tracker.stop()
        self.setWindowTitle("SimAuth Agent")
        self._show_registration()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.showNormal()
