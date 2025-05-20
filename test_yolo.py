import cv2
import streamlink
from ultralytics import YOLO
import pandas as pd
import datetime
import yt_dlp
import os
import json
import time

import threading
import queue

# import torch
# import torchvision
# print("CUDA available:", torch.cuda.is_available())
# print("GPU name:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Not available")

# GPU 사용 가능한지 확인
# if torch.cuda.is_available():
#     device = 'cuda'
# else:
#     device = 'cpu'
# print(device)
# model.to(device)
# end

# print(torch.__version__)
# print(torchvision.__version__)
# print(torch.cuda.is_available())
# print(torch.version.cuda)

# [Main Thread]
# ├─ Tkinter GUI (root.mainloop())
# ├─ OpenCV Display (cv2.imshow)
# │
# └─ Background Thread
#     ├─ model.track(show=False)
#     └─ Queue로 결과 전달 (Frame, BBox 등)
    # gpu test
    # import torch
    # print("CUDA available:", torch.cuda.is_available())
    # print("GPU name:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Not available")

    # # GPU 사용 가능한지 확인
    # if torch.cuda.is_available():
    #     device = 'cuda'
    # else:
    #     device = 'cpu'
    # print(device)
    # model.to(device)
    # # end
    
frame_queue = queue.Queue()
result_queue = queue.Queue()

frame_data = []
max_people = 0
total_people = 0
frame_count = 0

model_name = "yolo11m.pt"
output_directory = "/Users/yoon/local/people-counter/"
csv_filename = "people_counting.csv"
source_type = "YouTube URL"
url = "https://www.youtube.com/watch?v=HdzniTPezs8"
conf = 0.3
iou = 0.5
show = False
stream_active = True

def get_youtube_title(url, log_callback=None):
    ydl_opts = {
        'quiet': True,
        'force_generic_extractor': True,
        'extract_flat': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', 'unknown_title')
        log_callback("유튜브명=> " + title)
        return title

def guess_worship_type(title):
    title = title.lower()
    if "새벽" in title:
        return "새벽기도"
    elif "수요" in title:
        return "수요예배"
    elif "1부" in title:
        return "주일예배1부"
    elif "2부" in title:
        return "주일예배2부"
    elif "3부" in title:
        return "주일예배3부"
    elif "수련회" in title:
        return "수련회"
    else:
        return "기타"

def on_stream_end(start_time, log_callback=None):
    global max_people, total_people, frame_count
    avg_people = round(total_people / frame_count) if frame_count > 0 else 0
    title = get_youtube_title(url, log_callback)
    worship_type = guess_worship_type(title)
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    file_path = os.path.join(output_directory, csv_filename)
    summary_data = {
        "type": worship_type,
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "max_people": max_people,
        "avg_people": avg_people,
        "url": url
    }

    df = pd.DataFrame([summary_data])
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

    log_callback(f"❌ 스트림 종료. 기록 저장 완료: ({file_path} {start_time})")

    max_people = 0
    total_people = 0
    frame_count = 0

def stop_stream(video_label=None, log_callback=None):
    global stream_active

    log_callback("사용자 요청으로 종료합니다.")
    stream_active = False
    with result_queue.mutex:
        result_queue.queue.clear()
    if video_label is not None:
        video_label.grid_forget()

def load_settings():
    global model_name, output_directory, csv_filename, source_type, url, conf, iou, show
    try:
        with open("settings.json", "r") as f:
            settings = json.load(f)
            model_name = settings.get("model", "yolo11m.pt")
            output_directory = settings.get("output_directory", "/Users/yoon/local/people-counter/")
            csv_filename = settings.get("csv_filename", "people_counting.csv")
            source_type = settings.get("source", "YouTube URL")
            url = settings.get("url", "")
            conf = float(settings.get("conf", 0.3))
            iou = float(settings.get("iou", 0.5))
            show = settings.get("show", False)
    except FileNotFoundError:
        print("설정 파일이 존재하지 않습니다.")
    except Exception as e:
        print(f"설정 파일 로드 중 오류 발생: {e}")

def get_youtube_url(input_url, log_callback=None):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(input_url, download=False)

        if info.get('is_live', False):
            log_callback("현재 실시간 스트리밍입니다.")
            streams = streamlink.streams(input_url)
            return streams.get("best").url if "best" in streams else None
        elif info.get('was_live', False):
            log_callback("종료된 실시간 스트리밍입니다. 일반 영상으로 처리합니다.")
            return input_url
        else:
            log_callback("일반 VOD 영상입니다.")
            return input_url
        
def tracking_thread(model, log_callback=None):
    global stream_active, max_people, total_people, frame_count

    log_callback(f"모델명 = {model_name}")
    log_callback(f"저장폴더 = {output_directory}")
    log_callback(f"파일명 = {csv_filename}")

    log_callback(f"url = {url}")
    log_callback(f"conf = {conf}")
    log_callback(f"iou = {iou}")
    log_callback(f"show = {show}")
    log_callback(f"stream_active = {stream_active}")

    results = model.track(
        source=get_youtube_url(url, log_callback),
        device='cuda',
        show=False,
        stream=True,
        classes=[0],
        conf=conf,
        iou=iou,
        imgsz=480,
    )

    tracked_ids = set()
    last_log_time = 0

    for result in results:
        if not stream_active:
            log_callback("추적쓰레드 종료합니다.")
            stop_stream(log_callback=log_callback)
            break

        if result is None or getattr(result, "path", None) is None:
            log_callback("스트림이 끊어졌습니다. 종료합니다.")
            stop_stream(log_callback=log_callback)
            break

        frame = result.orig_img.copy()
        boxes = result.boxes

        new_ids = {
            getattr(box, "id", None)
            for box in boxes
            if getattr(box, "id", None) not in tracked_ids
        }
        new_ids.discard(None)

        people_count = len(new_ids)
        tracked_ids.update(new_ids)

        max_people = max(max_people, people_count)
        total_people += people_count
        frame_count += 1

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if time.time() - last_log_time >= 1:
            log_callback(f"[{timestamp}] 사람 수: {people_count}")
            last_log_time = time.time()

        frame_data.append({"time": timestamp, "people": people_count})
        result_queue.put((frame, boxes))

import time
def track_people(frame_callback=None, log_callback=None):
    global stream_active

    load_settings()
    
    model = YOLO(model_name)
    threading.Thread(target=tracking_thread, args=(model, log_callback), daemon=True).start()

    log_callback("👀 추적 시작")
    stream_active = True
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    while stream_active:
        if show:
            if not result_queue.empty():
                    frame, boxes = result_queue.get()

                    if boxes is not None:
                        for box in boxes.xyxy:
                            x1, y1, x2, y2 = map(int, box)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    if frame_callback:
                        frame_callback(frame)
        time.sleep(0.01)
    
    on_stream_end(start_time, log_callback)

# # ffmpeg