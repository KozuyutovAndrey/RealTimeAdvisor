from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QTextEdit, QFrame, QHBoxLayout, QSizePolicy, QTextBrowser
from PySide6.QtCore import Qt, QTimer, QPoint, QCoreApplication, Signal, Slot, QSize
from PySide6.QtGui import QIcon
from PySide6.QtGui import QTextOption, QTextCursor
from recorder import Recorder
import threading
import cohere
import json

class GPTWindow(QWidget):
    update_signal = Signal(object)

    def __init__(self, context_getter):
        super().__init__()
        self.context_getter = context_getter

        # Frameless, translucent always-on-top window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.7)
        self.setStyleSheet("""
            QWidget { background-color: rgba(30,30,30,200);
                      color: white; font-size:12px;
                      border:1px solid #888; border-radius:8px; }
            QPushButton { background-color:#444; padding:6px;
                         border:none; border-radius:4px; }
            QPushButton:hover { background-color:#666; }
            QTextEdit, QTextBrowser { background-color:#222;
                                      color:white; border:none;
                                      border-radius:4px; }
        """)

        # --- Input area ---
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Введите запрос…")
        # Фиксируем высоту поля ввода
        self.input_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_edit.setFixedHeight(50)

        # Кнопка с иконкой Telegram
        self.send_btn = QPushButton()
        self.send_btn.setIcon(QIcon(r"images\6751069-middle.png"))
        self.send_btn.setIconSize(QSize(24, 24))
        # чтобы кнопка была квадратной
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.clicked.connect(self.send_query)

        # --- Response area (renders Markdown) ---
        self.response_edit = QTextBrowser()
        self.response_edit.setReadOnly(True)
        self.response_edit.setOpenExternalLinks(True)
        self.response_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Buffer for accumulating Markdown
        self._full_md = ""
        self.update_signal.connect(self.append_chunk)

        # --- Layout ---
        controls = QHBoxLayout()
        controls.setContentsMargins(5, 5, 5, 5)
        controls.addWidget(self.input_edit)
        controls.addWidget(self.send_btn)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addLayout(controls)
        main_layout.addWidget(self.response_edit)
        self.setLayout(main_layout)

        # --- Sizing & limits ---
        self.base_height = 200
        self.resize(400, self.base_height)
        self.setMaximumHeight(600)

        # --- Cohere client setup ---
        with open('credentions.json', encoding='utf-8') as f:
            secrets = json.load(f)
        api_key = secrets.get('COHERE_API_KEY')
        self.co = cohere.ClientV2(api_key)

    def send_query(self):
        context = self.context_getter() or ""
        user_text = self.input_edit.toPlainText().strip()
        prompt = f"{context}\n\n{user_text}" if user_text else context

        self.send_btn.setEnabled(False)
        self.input_edit.setReadOnly(True)
        self._full_md = ""
        self.response_edit.clear()
        self.resize(self.width(), self.base_height)

        def worker():
            stream = self.co.chat_stream(
                model='command-a-03-2025',
                messages=[{'role':'user', 'content': prompt}]
            )
            for chunk in stream:
                if chunk and chunk.type == 'content-delta':
                    self.update_signal.emit(chunk.delta.message.content.text)
            self.update_signal.emit(None)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object)
    def append_chunk(self, text):
        if text is None:
            self.send_btn.setEnabled(True)
            self.input_edit.setReadOnly(False)
            self.input_edit.clear()
            self.input_edit.setFocus()
            return

        self._full_md += text
        self.response_edit.setMarkdown(self._full_md)

        sb = self.response_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

        doc_h = int(self.response_edit.document().size().height())
        desired_h = doc_h + self.input_edit.height() + 20
        max_h = 600
        new_h = min(max(self.base_height, desired_h), max_h)
        if new_h != self.height():
            self.resize(self.width(), new_h)

class OverlayUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget { background-color: rgba(30,30,30,100); color: white; font-size:12px; border:1px solid #888; border-radius:8px; }
            QPushButton { background-color:#444; padding:6px; border:none; border-radius:4px; }
            QPushButton:hover { background-color:#666; }
        """)
        self.setWindowOpacity(0.7)
        self.setMinimumSize(400,150)
        self.resize(500,300)
        self.move(1000,100)

        # recorder setup
        self.recorder = Recorder()
        self.is_listening = False

        # controls
        self.toggle_record_btn = QPushButton('▶ Слушать')
        self.toggle_btn = QPushButton('⬇ Скрыть диалог')
        self.gpt_btn = QPushButton('GPT')
        self.close_btn = QPushButton('❌')
        self.close_btn.clicked.connect(QCoreApplication.instance().quit)
        self.status = QLabel('🕒 Готово')
        self.label = QTextEdit()  # transcription display
        self.label.setReadOnly(True)
        self.label.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.label.setStyleSheet('background-color:#222; color:white; border:none;')
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # transcript frame
        self.transcript_frame = QFrame()
        tl = QVBoxLayout(); tl.setContentsMargins(10,7,10,10)
        tl.addWidget(self.status); tl.addWidget(self.label)
        self.transcript_frame.setLayout(tl)

        # connect signals
        self.toggle_record_btn.clicked.connect(self.toggle_recording)
        self.toggle_btn.clicked.connect(self.toggle_transcript)
        self.gpt_btn.clicked.connect(self.open_gpt_window)

        # button bar layout
        bar = QHBoxLayout(); bar.setContentsMargins(10,10,10,10); bar.setSpacing(10)
        bar.addWidget(self.toggle_record_btn); bar.addWidget(self.toggle_btn)
        bar.addWidget(self.gpt_btn); bar.addWidget(self.close_btn)
        btn_frame = QFrame(); btn_frame.setLayout(bar)

        # main layout
        ml = QVBoxLayout(); ml.setContentsMargins(0,0,0,0)
        ml.addWidget(btn_frame); ml.addWidget(self.transcript_frame)
        self.setLayout(ml)

        # timer for transcript
        self._show_text = True
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.refresh_transcript)
        self._update_timer.start(500)

        # dragging vars
        self._drag_active = False
        self._drag_position = QPoint()

        # GPT window reference
        self.gpt_window = None

    def toggle_recording(self):
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()

    def start_listening(self):
        self.status.setText('🎙 Запись...')
        self.toggle_record_btn.setText('⏹ Остановить')
        self.is_listening = True
        threading.Thread(target=self.recorder.start, daemon=True).start()

    def stop_listening(self):
        self.status.setText('⏹ Остановлено')
        self.toggle_record_btn.setText('▶ Слушать')
        self.is_listening = False
        self.recorder.stop()

    def toggle_transcript(self):
        self._show_text = not self._show_text
        self.transcript_frame.setVisible(self._show_text)
        self.toggle_btn.setText('⬇ Скрыть диалог' if self._show_text else '⬆ Показать диалог')
        if self._show_text:
            self.refresh_transcript()

    def refresh_transcript(self):
        if self._show_text:
            new = self.recorder.get_latest_text()
            if new and new not in self.label.toPlainText():
                self.label.append(new)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_active = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_active:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_active = False

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.gpt_window and self.gpt_window.isVisible():
            self._position_gpt()

    def _position_gpt(self):
        g = self.geometry()
        self.gpt_window.move(g.x() + g.width() + 10, g.y())

    def open_gpt_window(self):
        # create or update GPT window
        if not self.gpt_window:
            # pass context_getter to always fetch latest transcript
            self.gpt_window = GPTWindow(lambda: self.label.toPlainText())
        # toggle visibility
        if self.gpt_window.isVisible():
            self.gpt_window.hide()
        else:
            self._position_gpt()
            self.gpt_window.show()
            self.gpt_window.raise_()
