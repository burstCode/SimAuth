import json
import urllib.request

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton,
)

from config import AcRemoteConfig, save_remote_config
from ui.styles import DARK


class ServerSettingsDialog(QDialog):
    """Диалог настройки AC-сервера. Изменения сохраняются в config.json."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки сервера")
        self.setStyleSheet(DARK)
        self.setMinimumWidth(540)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )

        root = QVBoxLayout()
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        title = QLabel("Настройки сервера AC")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addSpacing(6)

        hint = QLabel("Заполненные поля применяются к race.ini перед каждым запуском игры")
        hint.setObjectName("status")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        root.addWidget(hint)
        root.addSpacing(24)

        root.addWidget(self._separator("Подключение"))
        root.addSpacing(12)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def lbl(t: str) -> QLabel:
            l = QLabel(t)
            l.setObjectName("form_label")
            return l

        self._server_ip = QLineEdit()
        self._server_ip.setPlaceholderText("173.234.30.178")

        self._server_http_port = QLineEdit()
        self._server_http_port.setPlaceholderText("8308  (HTTP-порт из CM / инвайт-ссылки)")

        self._password = QLineEdit()
        self._password.setPlaceholderText("(пусто — без пароля)")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow(lbl("IP-адрес"), self._server_ip)
        form.addRow(lbl("HTTP-порт"), self._server_http_port)
        form.addRow(lbl("Пароль"), self._password)
        root.addLayout(form)

        # Кнопка «Проверить» + строка статуса
        root.addSpacing(12)
        check_row = QHBoxLayout()
        btn_check = QPushButton("Проверить подключение")
        btn_check.setObjectName("finish_btn")
        btn_check.clicked.connect(self._test_connection)
        check_row.addStretch()
        check_row.addWidget(btn_check)
        root.addLayout(check_row)

        root.addSpacing(6)
        self._check_status = QLabel("")
        self._check_status.setObjectName("status")
        self._check_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._check_status.setWordWrap(True)
        root.addWidget(self._check_status)

        root.addSpacing(20)
        root.addWidget(self._separator("Автомобиль"))
        root.addSpacing(12)

        form2 = QFormLayout()
        form2.setSpacing(12)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._car = QLineEdit()
        self._car.setPlaceholderText("ks_toyota_ae86_tuned  (ID модели в AC)")

        self._skin = QLineEdit()
        self._skin.setPlaceholderText("04_trd_86  (пусто — не менять)")

        form2.addRow(lbl("Модель"), self._car)
        form2.addRow(lbl("Ливрея"), self._skin)
        root.addLayout(form2)

        root.addSpacing(28)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("finish_btn")
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("form_btn")
        btn_save.clicked.connect(self._save)

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)

        self.setLayout(root)
        self._load_values()

    @staticmethod
    def _separator(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("form_label")
        lbl.setStyleSheet(
            "QLabel { border-bottom: 1px solid #333333; padding-bottom: 4px; color: #888888; }"
        )
        return lbl

    def _load_values(self):
        from config import config
        rc = config.ac_remote
        if rc.server_ip:
            self._server_ip.setText(rc.server_ip)
        if rc.server_http_port:
            self._server_http_port.setText(str(rc.server_http_port))
        if rc.password is not None:
            self._password.setText(rc.password)
        if rc.car:
            self._car.setText(rc.car)
        if rc.skin:
            self._skin.setText(rc.skin)

    def _test_connection(self):
        ip = self._server_ip.text().strip()
        try:
            http_port = int(self._server_http_port.text().strip())
        except ValueError:
            self._check_status.setText("Укажите HTTP-порт")
            return
        if not ip:
            self._check_status.setText("Укажите IP-адрес")
            return
        self._check_status.setText("Запрос...")
        try:
            url = f"http://{ip}:{http_port}/INFO"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            name = data.get("name", "?")
            clients = data.get("clients", 0)
            maxc = data.get("maxclients", 0)
            game_port = data.get("port", "?")
            self._check_status.setText(
                f"✓  {name}\n"
                f"Онлайн: {clients}/{maxc}   игровой порт: {game_port}"
            )
        except Exception as e:
            self._check_status.setText(f"Ошибка: {e}")

    def _save(self):
        def _int(field: QLineEdit) -> int:
            try:
                return int(field.text().strip())
            except ValueError:
                return 0

        rc = AcRemoteConfig(
            server_ip=self._server_ip.text().strip(),
            server_http_port=_int(self._server_http_port),
            password=self._password.text() if self._password.text() != "" else None,
            car=self._car.text().strip(),
            skin=self._skin.text().strip(),
        )
        save_remote_config(rc)
        self.accept()
