import logging

from PyQt6.QtCore import QThread, pyqtSignal, QObject


class _LogBridge(QObject):
    record_ready = pyqtSignal(str, str)  # levelname, formatted message


class _QtLogHandler(logging.Handler):
    def __init__(self, bridge: _LogBridge):
        super().__init__()
        self._bridge = bridge
        self.setFormatter(logging.Formatter(
            "%(asctime)s  %(message)s",
            datefmt="%H:%M:%S",
        ))

    def emit(self, record: logging.LogRecord):
        try:
            self._bridge.record_ready.emit(record.levelname, self.format(record))
        except Exception:
            pass


class ServerThread(QThread):
    log_record = pyqtSignal(str, str)   # levelname, message
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._bridge = _LogBridge()
        self._bridge.record_ready.connect(self.log_record)
        self._handler = _QtLogHandler(self._bridge)
        self._server = None

    def run(self):
        import uvicorn
        from main import app
        from database import init_db
        from config import config as srv_cfg

        init_db()

        # Configure loggers BEFORE uvicorn starts.
        # Pass log_config=None so uvicorn skips its dictConfig call and won't
        # replace our handlers with its own StreamHandlers.
        for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
            lg = logging.getLogger(name)
            lg.setLevel(logging.INFO)
            lg.handlers = []
            lg.addHandler(self._handler)
            lg.propagate = False

        uv_cfg = uvicorn.Config(
            app,
            host=srv_cfg.host,
            port=srv_cfg.port,
            log_level="info",
            log_config=None,   # prevents uvicorn from overriding our logging setup
        )
        self._server = uvicorn.Server(uv_cfg)
        self.server_started.emit()
        self._server.run()
        self.server_stopped.emit()

    def stop(self):
        if self._server:
            self._server.should_exit = True
