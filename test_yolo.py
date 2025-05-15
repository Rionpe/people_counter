import cv2
import subprocess
import streamlink
from ultralytics import YOLO
import pandas as pd
import datetime
import yt_dlp
import os
import json

frame_data = []  # 데이터를 저장할 리스트
max_people = 0  # 최대 인원 수 추적
total_people = 0  # 총 사람 수 (평균 계산을 위한 총합)
frame_count = 0  # 프레임 개수 (평균 계산을 위한 개수)

model_name = "yolo11m.pt"
output_directory = "/Users/yoon/local/people-counter/"
csv_filename = "people_counting.csv"
source_type = "YouTube URL"
url = ""
conf = 0.3
iou = 0.5
show = False

# 스트리밍을 시작하면서, 스트리밍 종료 조건을 체크할 변수
stream_active = True

def load_settings():
    global model_name, output_directory, csv_filename, source_type, url, conf, iou, show  # 전역 변수 선언
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
            show = settings.get("show", "False")
    except FileNotFoundError:
        print("설정 파일이 존재하지 않습니다.")
    except Exception as e:
        print(f"설정 파일 로드 중 오류 발생: {e}")

# 유튜브 스트림 제목을 가져오는 함수
def get_youtube_title(url):
    ydl_opts = {
        'quiet': True,
        'force_generic_extractor': True,
        'extract_flat': True,  # 메타데이터만 추출, 전체 비디오를 다운로드하지 않음
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', 'unknown_title')  # 제목 추출
        print("유튜브명=> "+title)
        return title

def guess_worship_type(title):
    """영상 제목 기반으로 예배 종류 자동 추정"""
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
    
# 스트리밍 종료 시 호출될 함수
def on_stream_end(start_time, log_fn):
    global max_people, total_people, frame_count
    # 평균 사람 수 계산
    if frame_count > 0:
        avg_people = round(total_people / frame_count)  # 평균 계산
    else:
        avg_people = 0

    # 유튜브 방송 송출 제목 가져오기
    title = get_youtube_title(url)
    worship_type = guess_worship_type(title)

    # 스트리밍 종료 시간
    end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 저장할 경로 지정
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)  # 폴더가 없으면 생성

    # 저장 파일 경로 (누적 저장 파일)
    file_path = os.path.join(output_directory, csv_filename)

    # 한 줄 데이터 구성
    summary_data = {
        "type": worship_type,
        "title": title,
        "start_time": start_time,
        "end_time": end_time,
        "max_people": max_people,
        "avg_people": avg_people,
        "url": url
    }

    # CSV 파일에 이어쓰기
    df = pd.DataFrame([summary_data])
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

    log_fn(f"스트림 종료. 기록 저장 완료: {file_path}")

    # 초기화 (다음 스트림 대비)
    max_people = 0
    total_people = 0
    frame_count = 0
    
def stop_stream(log_fn=print):
    global stream_active
    log_fn("창을 닫습니다")
    stream_active = False
    if show : cv2.destroyAllWindows()
    
def track_people(log_fn=print):
    global stream_active, max_people, total_people, frame_count

    stream_active = True

    log_fn("🔍 사람 추적 시작")

    load_settings()
    
    track_url = get_youtube_url(url)

    tracked_ids = set()

    # 스트리밍 시작 시간
    start_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    model = YOLO(model_name)
    # 스트림 처리
    results = model.track(
        source=track_url,  # 수정: {}를 빼고 track_url을 그대로 사용
        show=show,  # 추적 중 화면에 결과 표시
        stream=True,  # 실시간 스트리밍 처리
        classes=[0],  # 사람만 탐지
        conf=conf,  # 수정: {} 제거, 숫자 그대로 전달
        iou=iou,  # 수정: {} 제거, 숫자 그대로 전달
        imgsz=640
    )

    for result in results:
        if not stream_active:
            log_fn("사용자 요청으로 종료합니다.")
            break

        # 스트림 종료 또는 끊김 상태 감지
        if result is None or result.path is None:
            log_fn("스트림이 끊어졌습니다. 종료합니다.")
            stop_stream(log_fn)
            break

        if show:
            if cv2.waitKey(1) & 0xFF == 27 :
                log_fn("ESC 키 눌림. 창을 닫습니다.")
                stop_stream(log_fn)
                break

        frame_id = result.path
        people_count = 0
        for box in result.boxes:
            person_id = box.id  # 추적 ID를 가져옴
            if person_id not in tracked_ids:
                tracked_ids.add(person_id)  # 새로운 ID를 카운트하고 추가
                people_count += 1

        # 최대 사람 수 추적
        if people_count > max_people:
            max_people = people_count

        total_people += people_count
        frame_count += 1

        # 각 프레임 데이터를 frame_data에 저장
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame_data.append({
            "time": timestamp,
            "people": people_count
        })

        # 화면에 표시
        log_fn(f"[{timestamp}] 사람 수: {people_count}")

    # 스트리밍이 끝날 때 호출하여 기록 저장
    if not stream_active:
        on_stream_end(start_time, log_fn=log_fn)

def get_youtube_url(url):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        if info.get('is_live', False):
            print("현재 실시간 스트리밍입니다.")
            streams = streamlink.streams(url)
            return streams["best"].url if "best" in streams else None
        
        elif info.get('was_live', False):
            print("종료된 실시간 스트리밍입니다. 일반 영상으로 처리합니다.")
            return url  # 일반 VOD처럼 사용

        else:
            print("일반 VOD 영상입니다.")
            return url


# url = get_youtube_url("https://www.youtube.com/watch?v=1yjgRhBOhAM&list=PLBiFb_Jz-KTnVRxQf3VpGCB8j-i9ch4_c&index=8")

# print(f"처리된 URL: {url}")

# track_people(url)