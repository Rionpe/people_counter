import tkinter as tk
from tkinter import messagebox
import json
import threading
import os
from test_yolo import track_people, stop_stream

root = tk.Tk()
root.title("People Counter")
root.geometry("700x500")

# 모델 선택 라디오 버튼
tk.Label(root, text="모델 선택:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
model_var = tk.StringVar(value="yolo11m.pt")
model_frame = tk.Frame(root)
model_frame.grid(row=0, column=1, padx=10, pady=5, sticky="w")
for model in ["yolo11n.pt", "yolo11m.pt", "yolo11s.pt"]:
    tk.Radiobutton(model_frame, text=model, variable=model_var, value=model).pack(side=tk.LEFT)

# 결과 저장 디렉토리
tk.Label(root, text="결과 저장 폴더:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
output_entry = tk.Entry(root, width=50)
output_entry.insert(0, "/Users/yoon/local/people-counter/")
output_entry.grid(row=1, column=1, padx=10, pady=5)

# CSV 파일명
tk.Label(root, text="CSV 파일명:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
csv_entry = tk.Entry(root, width=50)
csv_entry.insert(0, "people_counting.csv")
csv_entry.grid(row=2, column=1, padx=10, pady=5)

# 영상 소스 선택
tk.Label(root, text="영상 소스 설정:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
source_var = tk.StringVar(value="YouTube URL")
source_frame = tk.Frame(root)
source_frame.grid(row=3, column=1, padx=10, pady=5, sticky="w")

def toggle_source_input():
    if source_var.get() == "YouTube URL":
        source_input.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        source_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)  # 라벨도 보이게 함
    else:
        source_input.grid_remove()
        source_label.grid_remove()  # 라벨도 숨김

tk.Radiobutton(source_frame, text="YouTube URL", variable=source_var, value="YouTube URL", command=toggle_source_input).pack(side=tk.LEFT)
# tk.Radiobutton(source_frame, text="웹캠 (0)", variable=source_var, value="0", command=toggle_source_input).pack(side=tk.LEFT)
# tk.Radiobutton(source_frame, text="웹캠 (1)", variable=source_var, value="1", command=toggle_source_input).pack(side=tk.LEFT)

# 유튜브 URL 입력 라벨
source_label = tk.Label(root, text="YouTube 주소 입력:")
source_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)

# 유튜브 URL 입력
source_input = tk.Entry(root, width=50)
source_input.insert(0, "https://www.youtube.com/watch?v=xxxx")
source_input.grid(row=4, column=1, padx=10, pady=5, sticky="w")
source_input.grid_remove()  # 처음에는 숨기기

# Confidence
tk.Label(root, text="Confidence 최소 신뢰도 (0~1):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
conf_entry = tk.Entry(root, width=10)
conf_entry.insert(0, "0.3")
conf_entry.grid(row=5, column=1, sticky="w", padx=10, pady=5)

# IOU
tk.Label(root, text="IOU 교차영역 중복방지 (0~1):").grid(row=6, column=0, sticky="w", padx=10, pady=5)
iou_entry = tk.Entry(root, width=10)
iou_entry.insert(0, "0.5")
iou_entry.grid(row=6, column=1, sticky="w", padx=10, pady=5)


# 숫자만 입력되도록 검증
def validate_float(entry):
    try:
        val = float(entry.get())
        return 0 <= val <= 1
    except ValueError:
        return False

# 설정을 저장할 파일 경로
settings_file = "settings.json"

# 설정을 파일에 저장하는 함수
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
     # 파일이 존재하지 않으면 생성
    file_path = os.path.join(output_entry.get(), csv_entry.get())
    if not os.path.isfile(file_path):
        try:
            with open(file_path, "w"):
                log_message(f"✅ 파일 '{file_path}' 생성됨.")
        except Exception as e:
            log_message(f"파일 생성 중 오류 발생: {e}")
            return

    # 설정 파일 저장
    try:
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=4)
        log_message("✅ 설정 저장됨. 사람 추적 시작 중...")
    except Exception as e:
        log_message(f"설정 저장 중 오류 발생: {e}")

def load_settings_init():
    model_var.set("yolo11m.pt")
    output_entry.delete(0, tk.END)
    output_entry.insert(0, "/Users/yoon/local/people-counter/")
    csv_entry.delete(0, tk.END)
    csv_entry.insert(0, "people_counting.csv")
    source_var.set("YouTube URL")
    source_input.delete(0, tk.END)
    source_input.insert(0, "https://www.youtube.com/watch?v=xxxx")
    conf_entry.delete(0, tk.END)
    conf_entry.insert(0, 0.3)
    iou_entry.delete(0, tk.END)
    iou_entry.insert(0, 0.5)
    show_entry.delete(0, tk.END)
    show_entry.set(False)
    log_message("초기화 완료.")
    
# 설정을 로드하는 함수
def load_settings():
    try:
        with open(settings_file, "r") as f:
            settings = json.load(f)
            model_var.set(settings.get("model", "yolo11m.pt"))
            output_entry.delete(0, tk.END)
            output_entry.insert(0, settings.get("output_directory", "/Users/yoon/local/people-counter/"))
            csv_entry.delete(0, tk.END)
            csv_entry.insert(0, settings.get("csv_filename", "people_counting.csv"))
            source_var.set(settings.get("source", "YouTube URL"))
            source_input.delete(0, tk.END)
            source_input.insert(0, settings.get("url", "https://www.youtube.com/watch?v=xxxx"))
            conf_entry.delete(0, tk.END)
            conf_entry.insert(0, settings.get("conf", "0.3"))
            iou_entry.delete(0, tk.END)
            iou_entry.insert(0, settings.get("iou", "0.5"))
            show_entry.set(settings.get("show", False))
        log_message("설정이 로드되었습니다.")
    except FileNotFoundError:
        log_message("저장된 설정이 없습니다.")
    except Exception as e:
        log_message(f"설정 로드 중 오류 발생: {e}")

def on_start():
    if not validate_float(conf_entry) or not validate_float(iou_entry):
        messagebox.showerror("입력 오류", "Confidence 및 IOU는 0~1 사이의 숫자여야 합니다.")
        return

    save_settings()
    
    # 백그라운드 실행 여부에 따른 동작 분기
    if show_entry.get():
        log_message("추적이 포그라운드에서 실행됩니다.")
        track_people(log_fn=log_message)
    else:
      # 백그라운드에서 실행
        tracking_thread = threading.Thread(
            target=lambda: track_people(log_fn=log_message),  # log_message 함수도 넘김
            daemon=True
        )
        tracking_thread.start()
        log_message("추적이 백그라운드에서 실행됩니다.")

button_frame = tk.Frame(root)
button_frame.grid(row=9, column=0, columnspan=2, pady=20)

tk.Button(button_frame, text="초기화", command=load_settings_init, bg="lightblue", width=5).grid(row=0, column=1, padx=5)

# 백그라운드 실행 여부 체크박스 배치 (왼쪽에)
show_entry = tk.BooleanVar(value=False)
tk.Checkbutton(button_frame, text="포그라운드 실행 (화면 표시)", variable=show_entry, bg="lightblue", width=20).grid(row=0, column=0, padx=5)

# 오른쪽에 추적 시작, 종료 버튼 배치
tk.Button(button_frame, text="▶ 추적 시작", command=on_start, bg="lightgreen", width=5).grid(row=0, column=2, padx=5)
tk.Button(button_frame, text="✖ 종료", command=stop_stream, bg="salmon", width=5).grid(row=0, column=3, padx=5)

# 로그 출력용 텍스트 박스 (GUI 맨 아래 추가)
log_text = tk.Text(root, height=10, width=80)
log_text.grid(row=10, column=0, columnspan=2, padx=10, pady=10)
log_text.configure(state='disabled')  # 읽기 전용으로 설정

def log_message(message):
    log_text.configure(state='normal')
    log_text.insert(tk.END, f"{message}\n")
    log_text.see(tk.END)  # 항상 최신 로그가 보이도록 스크롤
    log_text.configure(state='disabled')


load_settings()
toggle_source_input()  # 초기 상태에 따라 유튜브 입력창 표시
root.mainloop()
