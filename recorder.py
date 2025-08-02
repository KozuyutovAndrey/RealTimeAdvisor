import queue
import threading
import time
import json
from datetime import datetime
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import subprocess

class Recorder:
    def __init__(self):
        self.running = False
        self.q_client = queue.Queue()
        self.q_advisor = queue.Queue()
        self.result_text = ""
        self.model = Model("vosk-model-small-ru-0.22")
        self.sample_rate = 16000  # ⚠️ Важно
        self.rec_client = KaldiRecognizer(self.model, self.sample_rate)
        self.rec_advisor = KaldiRecognizer(self.model, self.sample_rate)
        self.client_device_id = self.find_device("CABLE-A Output")
        self.advisor_device_id = self.find_device("microphone")
        self.log_file = f"log_{datetime.now().strftime('%Y%m%d')}.txt"

    def find_device(self, name_like):
        for i, dev in enumerate(sd.query_devices()):
            if name_like.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
                return i
        return None

    def client_callback(self, indata, frames, time_info, status):
        if status:
            print("[CLIENT STATUS]", status)
        self.q_client.put(bytes(indata))

    def advisor_callback(self, indata, frames, time_info, status):
        if status:
            print("[ADVISOR STATUS]", status)
        self.q_advisor.put(bytes(indata))

    def listen_stream(self, device_id, callback, recognizer, queue_ref, role):
        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000, dtype='int16',
                               channels=1, callback=callback, device=device_id):
            while self.running:
                if not queue_ref.empty():
                    data = queue_ref.get()
                    if recognizer.AcceptWaveform(data):
                        res = json.loads(recognizer.Result())
                        text = res.get("text", "")
                        if text:
                            self.append_log(role, text)
                            self.result_text = f"{role}: {text}"
                time.sleep(0.05)

    def start(self):
        print("[DEBUG] recorder.start() вызван")

        if self.client_device_id is None or self.advisor_device_id is None:
            print("[Recorder] Не найдены устройства. Транскрипция не запущена.")
            self.result_text = "❌ Устройства не найдены"
            return

        # ⚠️ Вывод системы на CABLE-A Input
        try:
            subprocess.call(["nircmdc.exe", "setdefaultsounddevice", "CABLE-A Input", "0"])
            print("[DEBUG] Переключено устройство вывода на CABLE-A Input")
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Не удалось переключить устройство: {e}")

        if self.running:
            return
        self.running = True
        self.result_text = ""

        self.t_client = threading.Thread(
            target=self.listen_stream,
            args=(self.client_device_id, self.client_callback, self.rec_client, self.q_client, "👤 КЛИЕНТ"),
            daemon=True
        )
        self.t_advisor = threading.Thread(
            target=self.listen_stream,
            args=(self.advisor_device_id, self.advisor_callback, self.rec_advisor, self.q_advisor, "👨‍💼 СОВЕТНИК"),
            daemon=True
        )

        self.t_client.start()
        self.t_advisor.start()

    def stop(self):
        self.running = False
        try:
            subprocess.call(["nircmdc.exe", "setdefaultsounddevice", "Headset Earphone", "0"])
            print("[DEBUG] Устройство вывода возвращено на Headset Earphone")
        except Exception as e:
            print(f"[ERROR] Не удалось вернуть устройство: {e}")

    def get_latest_text(self):
        return self.result_text or "Ожидание..."

    def append_log(self, role, text):
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime('%H:%M:%S')
            f.write(f"[{timestamp}] {role}: {text}\n")
