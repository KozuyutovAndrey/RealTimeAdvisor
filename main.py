# Пример для транскрибации и обработки аудио в реальном времени
# Использует Vosk для распознавания речи и SoundDevice для захвата аудио
# и VB-Cable для перенаправления системного звука

import sounddevice as sd
import queue
import json
import subprocess
import time
import threading
import signal
from vosk import Model, KaldiRecognizer

# === Константы ===
MODEL_PATH = "vosk-model-small-ru-0.22"
NIRCMD_PATH = "nircmdc.exe"
VBCABLE_NAME = "CABLE-A Input"         # Переключение системного звука сюда
JABRA_NAME = "Headset Earphone"        # Возврат звука после работы
SAMPLE_RATE = 16000

# Названия устройств брать тут cmd: .\nircmd.exe showsounddevices

# === Очереди ===
q_mic = queue.Queue()
q_vb = queue.Queue()

# === Распознаватели ===
model = Model(MODEL_PATH)
rec_mic = KaldiRecognizer(model, SAMPLE_RATE)
rec_vb = KaldiRecognizer(model, SAMPLE_RATE)

# === Завершение по Ctrl+C
stop_flag = False
def handle_sigint(sig, frame):
    global stop_flag
    stop_flag = True
signal.signal(signal.SIGINT, handle_sigint)

# === Переключение аудио устройства вывода
def set_default_output(device_name):
    subprocess.call([NIRCMD_PATH, "setdefaultsounddevice", device_name, "0"])
    time.sleep(1)

# === Поиск устройства по названию
def find_device(name_like):
    for i, dev in enumerate(sd.query_devices()):
        if name_like.lower() in dev["name"].lower() and dev["max_input_channels"] > 0:
            return i
    return None

# === Callback'и ===
def callback_mic(indata, frames, time, status):
    q_mic.put(bytes(indata))

def callback_vb(indata, frames, time, status):
    q_vb.put(bytes(indata))

# === Потоки ===
def listen_mic(device_id):
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16',
                           channels=1, callback=callback_mic, device=device_id):
        while not stop_flag:
            if not q_mic.empty():
                data = q_mic.get()
                if rec_mic.AcceptWaveform(data):
                    result = json.loads(rec_mic.Result())
                    if result.get("text"):
                        print("👨‍💼 СОВЕТНИК:", result["text"])

def listen_vbcable(device_id):
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16',
                           channels=1, callback=callback_vb, device=device_id):
        while not stop_flag:
            if not q_vb.empty():
                data = q_vb.get()
                if rec_vb.AcceptWaveform(data):
                    result = json.loads(rec_vb.Result())
                    if result.get("text"):
                        print("🧑‍💼 КЛИЕНТ:", result["text"])

# === Главная логика ===
if __name__ == "__main__":
    try:
        print("🔍 Ищем устройства...")
        mic_id = find_device("microphone")
        vb_id = find_device("cable-a output")

        if mic_id is None or vb_id is None:
            raise RuntimeError("Не найден микрофон или CABLE-A Output. Проверьте устройства.")

        print(f"🎙️ Микрофон ID: {mic_id}")
        print(f"🎧 CABLE-A Output ID: {vb_id}")

        print("🔈 Убедитесь, что включена галочка 'Прослушивать это устройство' для CABLE-A Output.")
        print(f"🔄 Переключаем вывод системы на {VBCABLE_NAME}...")
        set_default_output(VBCABLE_NAME)

        print("🎤 Слушаем микрофон и системный звук...\nНажмите Ctrl+C для завершения.")
        t1 = threading.Thread(target=listen_mic, args=(mic_id,), daemon=True)
        t2 = threading.Thread(target=listen_vbcable, args=(vb_id,), daemon=True)

        t1.start()
        t2.start()

        while not stop_flag:
            time.sleep(0.5)

    except Exception as e:
        print(f"❌ Ошибка: {e}")

    finally:
        print(f"\n🔁 Возвращаем звук на {JABRA_NAME}...")
        set_default_output(JABRA_NAME)
        print("👋 Готово.")
