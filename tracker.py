import threading
import datetime
import pandas as pd
import queue
import cv2
import streamlink
import yt_dlp
from ultralytics import YOLO
from pathlib import Path
import time
import json
import yt_dlp

def get_youtube_title(url: str, log_callback=None) -> str:
        ydl_opts = {
            'quiet': True,
            'force_generic_extractor': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'unknown_title')
            if log_callback:
                log_callback(f"유튜브명=> {title}")
            return title

def guess_worship_type(title: str) -> str:
    t = title.lower()
    if "새벽" in t:       return "새벽기도"
    if "수요" in t:       return "수요예배"
    if "1부" in t:        return "주일예배1부"
    if "2부" in t:        return "주일예배2부"
    if "3부" in t:        return "주일예배3부"
    if "수련회" in t:     return "수련회"
    return "기타"

class PeopleTracker:
    """
    YOLO를 사용하여 유튜브 스트림에서 사람 수를 추적하고,
    결과를 CSV 파일에 기록합니다.
    """
    def __init__(self, config_path: str = "settings.json"):
        self.config_path = Path(config_path)
        self.settings = self._load_settings()
        self.stream_active = False
        self.max_people = 0
        self.total_people = 0
        self.frame_count = 0
        self.result_queue = queue.Queue()
        self._thread = None

    def _load_settings(self) -> dict:
        defaults = {
            "model": "yolov11m-face.pt",
            "output_directory": "./output/",
            "csv_filename": "people_counting.csv",
            "source": "YouTube URL",
            "url": "",
            "conf": 0.35,
            "iou": 0.5,
            "show": False
        }
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                defaults.update(data)
            except Exception:
                pass
        defaults["conf"] = float(defaults.get("conf", 0.35))
        defaults["iou"] = float(defaults.get("iou", 0.5))
        defaults["show"] = bool(defaults.get("show", False))
        return defaults

    def start(self, frame_callback=None, log_callback=None):
        """
        백그라운드 스레드에서 추적 시작.
        frame_callback: 프레임 표시 콜백
        log_callback: 로그 출력 콜백
        """
        self.frame_callback = frame_callback
        self.log = log_callback or (lambda m: None)
        self.stream_active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.log("▶ PeopleTracker started")

    def stop(self):
        """스트림 중지 및 자원 해제"""
        self.stream_active = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        cv2.destroyAllWindows()
        self.log("🛑 PeopleTracker stopped")

    def _get_stream_url(self, url: str):
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('is_live', False):
                self.log("🔴 실시간 스트리밍 감지")
                streams = streamlink.streams(url)
                return streams.get('best').url, True
        self.log("🎞 VOD 감지")
        return url, False

    def _run(self):
        model = YOLO(self.settings['model'])
        self.log(f"🚀 모델 로드: {self.settings['model']}")

        stream_url, is_live = self._get_stream_url(self.settings['url'])
        self.log(f"📽 Stream URL: {stream_url}")

        start_time = datetime.datetime.now()
        results = model.track(
            source=stream_url,
            device='cuda',
            stream=True,
            imgsz=640,
            conf=self.settings['conf'],
            iou=self.settings['iou'],
            show=False
        )

        last_log = 0
        tracked = set()

        for res in results:
            if not self.stream_active:
                break
            if res is None or getattr(res, 'path', None) is None:
                self.log("⚠ Stream 끊김")
                break

            frame = res.orig_img
            boxes = res.boxes
            ids = {getattr(b,'id',None) for b in boxes if getattr(b,'id',None) is not None}

            new_ids = ids - tracked
            tracked.update(new_ids)

            count = len(ids)
            self.max_people = max(self.max_people, count)
            self.total_people += len(new_ids)
            self.frame_count += 1

            now = time.time()
            if now - last_log >= 1:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.log(f"[{ts}] 현재 인원: {count}")
                last_log = now

            self.result_queue.put((frame, boxes, count, is_live))
            self._display_loop()

        self._on_stream_end(start_time)

    def _on_stream_end(self, start_time):
        end_time = datetime.datetime.now()
        avg = round(self.total_people / self.frame_count) if self.frame_count else 0

        title = get_youtube_title(self.settings['url'], self.log)
        worship_type = guess_worship_type(title)

        out_dir = Path(self.settings['output_directory'])
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_path = out_dir / self.settings['csv_filename']

        df = pd.DataFrame([{
            'type': worship_type,
            'title': title,
            'start_time': start_time.strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': end_time.strftime("%Y-%m-%d %H:%M:%S"),
            'max_people': self.max_people,
            'avg_people': avg,
            'url': self.settings['url']
        }])
        df.to_csv(
            csv_path,
            mode='a',
            index=False,
            header=not csv_path.exists(),
            encoding='utf-8-sig'
        )
        self.log(f"📁 결과 저장: {csv_path}")

        self.max_people = self.total_people = self.frame_count = 0

    def _display_loop(self):
        while not self.result_queue.empty():
            frame, boxes, count, is_live = self.result_queue.get()
            confs = boxes.conf   if boxes.conf   is not None else []
            ids   = boxes.id     if boxes.id     is not None else []
            xyxy  = boxes.xyxy   if boxes.xyxy   is not None else []

            for b, conf, bid in zip(xyxy, confs, ids):
                x1,y1,x2,y2 = map(int, b)
                cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)
                cv2.putText(frame, f"{conf:.2f}",(x1,y1-10),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
                cv2.putText(frame, f"ID:{int(bid)}",(x1,y2+20),cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,0),2)
            cv2.putText(frame,f"Max:{self.max_people} Now:{count}",(10,30),cv2.FONT_HERSHEY_SIMPLEX,1,(255,0,0),2)

            if is_live:
                # 실시간: 별도 OpenCV 창으로 표시
                cv2.imshow("Live Stream", frame)
            else:
                # VOD: 프레임 콜백으로 GUI 내부에 표시
                if self.frame_callback:
                    self.frame_callback(frame)
                
# 트래킹 알고리즘
# 1. 한프레임 최대 동시인원수
# 2. 유니크한 사람 누적수
# 테스트: 라이브,  종료된 스트림 방송(VOD)