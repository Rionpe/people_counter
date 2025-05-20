import tkinter as tk
from tkinter import scrolledtext
import json
import threading
import os
from test_yolo import track_people, stop_stream
import queue

# log queue start
log_queue = queue.Queue()

def log_message_from_queue():
    while not log_queue.empty():
        msg = log_queue.get_nowait()
        log_text.config(state='normal')
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)
        log_text.config(state='disabled')
    root.after(100, log_message_from_queue)

def log_message(msg):
    log_queue.put(msg)
# log queue end

# 숫자 범위 검증 (0~1)
def validate_float(value):
    try:
        val = float(value)
        return 0 <= val <= 1
    except ValueError:
        return False

# Entry 초기화 함수
def set_entry(entry, value):
    entry.delete(0, tk.END)
    entry.insert(0, value)

root = tk.Tk()
root.title("People Counter")
root.geometry("800x850")

# 모델 선택
tk.Label(root, text="모델 선택:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
model_var = tk.StringVar(value="yolo11m.pt")
model_frame = tk.Frame(root)
model_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
for model in ["yolo11n.pt", "yolo11m.pt", "yolo11s.pt"]:
    tk.Radiobutton(model_frame, text=model, variable=model_var, value=model).pack(side=tk.LEFT)

# 결과 저장 폴더
tk.Label(root, text="결과 저장 폴더:", width=18, anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=5)
output_entry = tk.Entry(root, width=50)
output_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

# CSV 파일명
tk.Label(root, text="CSV 파일명:", width=18, anchor="w").grid(row=2, column=0, sticky="w", padx=10, pady=5)
csv_entry = tk.Entry(root, width=50)
csv_entry.grid(row=2, column=1, sticky="w", padx=10, pady=5)

# 영상 소스 선택 및 유튜브 URL 입력
tk.Label(root, text="영상 소스 설정:", width=18, anchor="w").grid(row=3, column=0, sticky="w", padx=10, pady=5)
source_var = tk.StringVar(value="YouTube URL")
source_frame = tk.Frame(root)
source_frame.grid(row=3, column=1, padx=10, pady=5, sticky="w")

def toggle_source_input():
    if source_var.get() == "YouTube URL":
        source_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)
        source_input.grid(row=4, column=1, padx=10, pady=5, sticky="w")
    else:
        source_label.grid_remove()
        source_input.grid_remove()

tk.Radiobutton(source_frame, text="YouTube URL", variable=source_var, value="YouTube URL", command=toggle_source_input).pack(side=tk.LEFT)

source_label = tk.Label(root, text="YouTube 주소 입력:", width=18, anchor="w")
source_input = tk.Entry(root, width=50)

# Confidence
tk.Label(root, text="Confidence 최소 신뢰도 (0~1):", width=30, anchor="w").grid(row=5, column=0, sticky="w", padx=10, pady=5)
conf_entry = tk.Entry(root, width=10)
conf_entry.grid(row=5, column=1, sticky="w", padx=10, pady=5)

# IOU
tk.Label(root, text="IOU 교차영역 중복방지 (0~1):", width=30, anchor="w").grid(row=6, column=0, sticky="w", padx=10, pady=5)
iou_entry = tk.Entry(root, width=10)
iou_entry.grid(row=6, column=1, sticky="w", padx=10, pady=5)

# 포그라운드 실행 체크박스
show_entry = tk.BooleanVar(value=False)
show_check = tk.Checkbutton(root, text="포그라운드 실행 (화면 표시)", variable=show_entry, bg="lightblue")
show_check.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w")

# 버튼 프레임
button_frame = tk.Frame(root)
button_frame.grid(row=8, column=0, columnspan=2, pady=20)

def save_settings():
    settings = {
        "model": model_var.get(),
        "output_directory": output_entry.get(),
        "csv_filename": csv_entry.get(),
        "source": source_var.get(),
        "url": source_input.get(),
        "conf": conf_entry.get(),
        "iou": iou_entry.get(),
        "show": show_entry.get()
    }

    file_path = os.path.join(settings["output_directory"], settings["csv_filename"])
    if not os.path.isfile(file_path):
        try:
            with open(file_path, "w"):
                log_message(f"✅ 파일 '{file_path}' 생성됨.")
        except Exception as e:
            log_message(f"파일 생성 중 오류 발생: {e}")
            return False

    try:
        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)
        log_message("✅ 설정 저장됨. 사람 추적 시작 중...")
        return True
    except Exception as e:
        log_message(f"설정 저장 중 오류 발생: {e}")
        return False

def load_settings():
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
        model_var.set(settings.get("model", "yolo11m.pt"))
        set_entry(output_entry, settings.get("output_directory", "/Users/yoon/local/people-counter/"))
        set_entry(csv_entry, settings.get("csv_filename", "people_counting.csv"))
        source_var.set(settings.get("source", "YouTube URL"))
        set_entry(source_input, settings.get("url", "https://www.youtube.com/watch?v=xxxx"))
        set_entry(conf_entry, settings.get("conf", "0.3"))
        set_entry(iou_entry, settings.get("iou", "0.5"))
        show_entry.set(settings.get("show", False))
        log_message("설정이 로드되었습니다.")
    except FileNotFoundError:
        log_message("저장된 설정이 없습니다.")
    except Exception as e:
        log_message(f"설정 로드 중 오류 발생: {e}")
    toggle_source_input()

def load_settings_init():
    model_var.set("yolo11m.pt")
    set_entry(output_entry, "/Users/yoon/local/people-counter/")
    set_entry(csv_entry, "people_counting.csv")
    source_var.set("YouTube URL")
    set_entry(source_input, "https://www.youtube.com/watch?v=xxxx")
    set_entry(conf_entry, "0.3")
    set_entry(iou_entry, "0.5")
    show_entry.set(False)
    log_message("초기화 완료.")
    toggle_source_input()

def on_start():
    if not validate_float(conf_entry.get()) or not validate_float(iou_entry.get()):
        log_message("입력 오류", "Confidence 및 IOU는 0~1 사이의 숫자여야 합니다.")
        return

    if not save_settings():
        return

    if show_entry.get():
        log_message("추적이 포그라운드에서 실행됩니다.")
        threading.Thread(target=lambda: track_people(
            frame_callback=show_frame_in_gui,
            log_callback=log_message
        ), daemon=True).start()
        if video_label is not None:
            video_label.grid(row=10, column=0, columnspan=2, sticky="nsew")
    else:
        log_message("추적이 백그라운드에서 실행됩니다.")
        threading.Thread(target=lambda: track_people(
            frame_callback=None,
            log_callback=log_message
        ), daemon=True).start()

def on_key_press(event):
    if event.char == 'q':
        log_message("q 눌림. 스트림 종료합니다.")
        stop_stream(video_label=video_label, log_callback=log_message)

root.bind('<Key>', on_key_press)

tk.Button(button_frame, text="초기화", command=load_settings_init, bg="lightblue", width=5).grid(row=0, column=0, padx=5)
tk.Button(button_frame, text="▶ 추적 시작", command=on_start, bg="lightgreen", width=8).grid(row=0, column=1, padx=5)
tk.Button(button_frame, text="✖ 종료", command=lambda: stop_stream(video_label=video_label, log_callback=log_message), bg="salmon", width=5).grid(row=0, column=2, padx=5)

video_label = tk.Label(root)
video_label.grid(row=10, column=0, columnspan=2, sticky="nsew")

import cv2
from PIL import Image, ImageTk

def show_frame_in_gui(frame):
    # OpenCV → PIL → ImageTk
    frame = cv2.resize(frame, (800, 400))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = ImageTk.PhotoImage(Image.fromarray(frame))
    video_label.config(image=img)
    video_label.image = img

log_text = tk.Text(root, height=8, width=100, state='disabled')
log_text.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")


load_settings()
root.after(100, log_message_from_queue)
root.mainloop()
