import os
import time
import json
import threading
import os
import time
import uuid
import ctypes
import threading
import tempfile
import asyncio
import win32api
import win32con
import win32gui
import pyperclip
import speech_recognition as sr
from faster_whisper import WhisperModel
import numpy as np
import edge_tts

WAKE_WORD = "ассистент"
MODEL_SIZE = "small"

try:
    import pygame
    pygame.mixer.init()
except Exception as e:
    print(f"[Внимание] Ошибка pygame: {e}. Пробую еще раз...")
    time.sleep(1)
    pygame.mixer.init()

import tkinter as tk

class StatusIndicator:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.circle = None
        threading.Thread(target=self._run_gui, daemon=True).start()
        
    def _run_gui(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True) # Без рамок
        self.root.attributes("-topmost", True) # Поверх всех окон
        self.root.attributes("-transparentcolor", "black") # Прозрачный фон
        
        # Позиция: правый нижний угол (чуть выше панели задач)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"30x30+{screen_width - 50}+{screen_height - 150}")
        self.root.configure(bg='black')
        
        self.canvas = tk.Canvas(self.root, width=30, height=30, bg='black', highlightthickness=0)
        self.canvas.pack()
        
        self.circle = self.canvas.create_oval(5, 5, 25, 25, fill="green", outline="white", width=2)
        self.root.mainloop()

    def set_color(self, color):
        try:
            if self.canvas and self.circle:
                self.canvas.itemconfig(self.circle, fill=color)
        except:
            pass

status_indicator = StatusIndicator()

def play_audio(text, voice="ru-RU-SvetlanaNeural"):
    """Generate and play TTS audio using edge-tts and pygame."""
    def _run_tts():
        output_file = os.path.join(tempfile.gettempdir(), f"speech_{uuid.uuid4().hex}.wav")
        
        try:
            import pyttsx3
            import pythoncom
            pythoncom.CoInitialize()
            engine = pyttsx3.init()
            
            # Настройка скорости
            engine.setProperty('rate', 170)
            
            # Ищем русский голос SAPI5 (по умолчанию Ирина)
            for v in engine.getProperty('voices'):
                if 'RU' in v.id or 'Russian' in v.name or 'ru' in v.languages:
                    engine.setProperty('voice', v.id)
                    break
                    
            engine.save_to_file(text, output_file)
            engine.runAndWait()
            pythoncom.CoUninitialize()
        except Exception as e:
            print(f"[pyttsx3] Ошибка генерации: {e}")
            return
            
        try:
            if not os.path.exists(output_file):
                return
            
            print(f"[Дебаг] Воспроизведение через оффлайн TTS...")
            status_indicator.set_color("#00a2ff") # Синий цвет - говорит ассистент
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            status_indicator.set_color("#00ff00") # Зеленый - готов слушать
            
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")
        finally:
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except:
                pass
                
    threading.Thread(target=_run_tts, daemon=True).start()

def focus_antigravity():
    """Find and focus the Antigravity window."""
    target_hwnd = None
    
    def window_enum_callback(hwnd, wildcard):
        nonlocal target_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if not title: return
            
            # Проверяем по названию процесса, чтобы не зависеть от имени сессии
            try:
                import win32process
                import win32api
                import win32con
                import os
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
                exe_path = win32process.GetModuleFileNameEx(handle, 0)
                win32api.CloseHandle(handle)
                exe_name = os.path.basename(exe_path).lower()
                
                if "antigravity" in exe_name:
                    target_hwnd = hwnd
                    return True
            except:
                pass
                
            # Fallback на случай если процесс недоступен
            if "Antigravity" in title and "Visual Studio Code" not in title:
                target_hwnd = hwnd
                return True
                
    win32gui.EnumWindows(window_enum_callback, None)
    
    if target_hwnd:
        try:
            current_fg = win32gui.GetForegroundWindow()
            if current_fg != target_hwnd:
                win32gui.ShowWindow(target_hwnd, 5) 
                win32gui.SetForegroundWindow(target_hwnd)
            print(f"[Успех] Фокус переведен на Antigravity: {win32gui.GetWindowText(target_hwnd)}")
        except Exception as e:
            print(f"[Внимание] Не удалось перехватить фокус: {e}")
            return None
        return target_hwnd
    else:
        print("[Ошибка] Окно Antigravity не найдено!")
        return None

def send_prompt(text):
    """Inject text into the active window and press Enter."""
    hwnd = focus_antigravity()
    
    if hwnd:
        time.sleep(0.2) # Даем окну время выйти на передний план
            
    original_clipboard = pyperclip.paste()
    pyperclip.copy(text)
    time.sleep(0.05)
    
    # Robust paste using virtual key codes (ignores keyboard layout!)
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(0x56, 0, 0, 0) # 'V' key
    time.sleep(0.05)
    win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    
    time.sleep(0.05)
    
    # Robust Enter
    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
    
    try:
        pyperclip.copy(original_clipboard)
    except:
        pass



class TranscriptWatcher:
    def __init__(self, brain_dir):
        self.brain_dir = brain_dir
        self.last_pos = 0
        self.current_transcript = None
        self.running = True
        self.last_spoken_message = ""

    def get_latest_transcript(self):
        """Find the most recent conversation transcript in the brain directory."""
        if not os.path.exists(self.brain_dir):
            return None
            
        latest_transcript = None
        latest_mtime = 0
        
        for d in os.listdir(self.brain_dir):
            transcript_path = os.path.join(self.brain_dir, d, ".system_generated", "logs", "transcript_full.jsonl")
            if os.path.exists(transcript_path):
                mtime = os.path.getmtime(transcript_path)
                if mtime > latest_mtime:
                    latest_mtime = mtime
                    latest_transcript = transcript_path
                    
        return latest_transcript

    def watch(self):
        # Initial read to populate last_spoken_message and avoid reading history
        latest = self.get_latest_transcript()
        if latest and os.path.exists(latest):
            with open(latest, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line.strip())
                            if entry.get("source") == "MODEL" and entry.get("type") == "PLANNER_RESPONSE":
                                content = entry.get("content", "")
                                if content:
                                    self.last_spoken_message = content
                        except json.JSONDecodeError:
                            pass
                            
        while self.running:
            latest = self.get_latest_transcript()
            if latest and os.path.exists(latest):
                with open(latest, 'r', encoding='utf-8') as f:
                    messages = []
                    for line in f:
                        if line.strip():
                            try:
                                entry = json.loads(line.strip())
                                if entry.get("source") == "MODEL" and entry.get("type") == "PLANNER_RESPONSE":
                                    content = entry.get("content", "")
                                    if content:
                                        messages.append(content)
                            except json.JSONDecodeError:
                                pass
                                
                    if messages:
                        latest_msg = messages[-1]
                        if latest_msg != self.last_spoken_message:
                            self.last_spoken_message = latest_msg
                            
                            import re
                            # Заменяем большие блоки кода на короткую фразу, чтобы не слушать их зачитывание по буквам
                            clean_content = re.sub(r'```.*?```', ' [Тут написан код] ', latest_msg, flags=re.DOTALL)
                            
                            # Clean up markdown for TTS
                            clean_content = clean_content.replace("*", "").replace("#", "").replace("`", "").replace("_", "")
                            speak_text = clean_content.strip()
                            
                            print(f"\n[Ассистент ответил]: {speak_text[:200]}...")
                            try:
                                play_audio(speak_text)
                            except Exception as e:
                                print(f"[Ошибка озвучки]: {e}")
            time.sleep(1)

def listen_loop():
    print("Загрузка модели Whisper (может занять некоторое время при первом запуске)...")
    # Load model on CPU with INT8 for fast performance
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    
    recognizer = sr.Recognizer()
    
    # Настройки для микрофона:
    # Включаем динамический порог обратно, иначе он записывает тишину (отсюда галлюцинации Whisper)
    recognizer.dynamic_energy_threshold = True  
    recognizer.pause_threshold = 1.8   # Немного увеличил, чтобы не съедало концы фраз
    recognizer.non_speaking_duration = 0.5

    print("\n--- ГОЛОСОВОЙ МОСТ АКТИВЕН ---")
    print(f"Кодовое слово: '{WAKE_WORD}'")
    print("Пример: 'Ассистент, объясни этот код'")

    # Try to find the default microphone
    with sr.Microphone() as source:
        print("Калибровка микрофона (помолчите 2 сек)...")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        
        # ФИКС: Отключаем плавающий порог ПОСЛЕ калибровки. 
        # Теперь порог зафиксирован идеально под вашу комнату и не будет "глушить" тихие звуки в начале!
        recognizer.dynamic_energy_threshold = False
        
        print("Микрофон откалиброван. Жду команд.")
        
        while True:
            try:
                # Убираем phrase_time_limit, чтобы он не обрезал звук ровно через 15 секунд
                status_indicator.set_color("#00ff00") # Зеленый - готов слушать
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=None)
                
                status_indicator.set_color("#ff0000") # Красный - распознавание текста (Whisper)
                
                # Convert directly to numpy float32 array in memory (Whisper expects 16kHz)
                raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                audio_np = np.frombuffer(raw_data, np.int16).astype(np.float32) / 32768.0
                
                # Transcribe with faster-whisper from RAM
                segments, info = model.transcribe(audio_np, language="ru")
                text = " ".join([segment.text for segment in segments]).strip().lower()
                
                # Clean up punctuation from the wake word detection
                clean_text = text.replace(",", "").replace(".", "").replace("!", "").replace("?", "")
                
                if not text:
                    continue
                    
                # Игнорируем частые "галлюцинации" Whisper на фоновый шум (кашель, скрип стула)
                hallucinations = ["субтитров", "amara.org", "продолжение следует", "подпишитесь на", "n.zkamaldino", "закомолдина", "музыка"]
                if any(h in clean_text for h in hallucinations):
                    continue
                    
                print(f"[Вы]: {text}")
                
                # Check for wake word
                if WAKE_WORD in clean_text:
                    # Find the command after the wake word
                    parts = clean_text.split(WAKE_WORD, 1)
                    if len(parts) > 1 and parts[1].strip():
                        # Use the original text but sliced from where the wake word ended
                        # This preserves original punctuation in the prompt
                        lower_text = text.lower()
                        start_idx = lower_text.find(WAKE_WORD) + len(WAKE_WORD)
                        command = text[start_idx:].strip()
                        # Trim leading punctuation if any
                        while command and command[0] in ' ,.!?':
                            command = command[1:].strip()
                            
                        if command:
                            print(f"[Команда отправлена]: {command}")
                            # Остановка текущей речи (Прерывание)
                            try:
                                pygame.mixer.music.stop()
                            except:
                                pass
                                
                            # Звуковой сигнал (Успех)
                            import winsound
                            winsound.Beep(1000, 100)
                            winsound.Beep(1200, 100)
                            
                            send_prompt(command)
                        else:
                            print("[Замечено кодовое слово без команды]")
                            try:
                                pygame.mixer.music.stop()
                            except:
                                pass
                            import winsound
                            winsound.Beep(800, 200) # Сигнал ошибки
                    else:
                        print("[Замечено кодовое слово без команды]")
                        try:
                            pygame.mixer.music.stop()
                        except:
                            pass
                        import winsound
                        winsound.Beep(800, 200) # Сигнал ошибки
                        
            except sr.WaitTimeoutError:
                pass # Just keep listening
            except Exception as e:
                print(f"[Ошибка при распознавании]: {e}")

if __name__ == "__main__":
    try:
        # The brain directory where transcripts are kept
        brain_directory = os.path.expanduser(r"~/.gemini/antigravity/brain")
        
        # 1. Start transcript watcher in a background thread
        watcher = TranscriptWatcher(brain_directory)
        watcher_thread = threading.Thread(target=watcher.watch, daemon=True)
        watcher_thread.start()
        
        # 2. Start microphone listening loop
        listen_loop()
    except KeyboardInterrupt:
        print("\n[Система] Скрипт остановлен пользователем (Ctrl+C). До свидания! 👋")
