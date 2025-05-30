```
# 프로젝트 폴더로 이동 (필요에 따라 경로 수정)
cd {프로젝트_폴더_경로}

# 1. 가상 환경 생성
python -m venv venv

# 2. 가상 환경 활성화
source venv/bin/activate  (macOS/Linux)
venv\Scripts\activate.bat  (Windows)

# 실행 정책 변경
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
Get-ExecutionPolicy -List
.\venv\Scripts\Activate.ps1

# 3. 필요한 패키지 설치
pip install -r requirements.txt

# 4. PyInstaller 설치
pip install pyinstaller

# 5. 실행 파일 빌드
pyinstaller --noconfirm {--console/--windowed} gui.py
# 재빌드
pyinstaller gui.spec

# create exe
echo "빌드 완료! 실행 파일은 dist/ 폴더 내에 생성"
```


```
# 데이터셋 검색 후 다운로드
* https://universe.roboflow.com/mohamed-traore-2ekkp/face-detection-mik1i/model/25
https://universe.roboflow.com/leo-ueno/people-detection-o4rdr/dataset/8
//.py
from roboflow import Roboflow
rf = Roboflow(api_key="apikey")
project = rf.workspace("mohamed-traore-2ekkp").project("face-detection-mik1i")
version = project.version(25)
dataset = version.download("yolov11")

# training
1. yolo11n.pt를 기반으로 data.yaml을 가중치로 더함
def main():
    model = YOLO('yolo11n.pt')
    results = model.train(
         data=r"C:\Users\COM\Documents\GitHub\people_counter\Face-Detection-25\data.yaml",
         epochs=100,
         imgsz=416,
         batch=8
    )

if __name__ == '__main__':
    main()

2. 만들어진 best.pt 로드후 사용

model = YOLO(r'C:\Users\COM\Documents\GitHub\people_counter\runs\detect\train\weights\best.pt')

3. 중지후 재실행 하려면?
model = YOLO(r'C:\Users\COM\Documents\GitHub\people_counter\runs\detect\train\weights\last.pt')
results = model.train(
      resume=True
)

# 추론
from ultralytics import YOLO

def main():
    # 학습된 모델 로드
    model = YOLO("runs/detect/yolov11-person/weights/best.pt")  # 또는 last.pt

    # 이미지/폴더/영상 추론
    # results = model.predict(source="sample.jpg", show=True, conf=0.3)
    # results = model.predict(source="folder_path/", show=True, conf=0.3)
    # results = model.predict(source="video.mp4", show=True, conf=0.3)

if __name__ == "__main__":
    main()


                
```

```
https://github.com/akanametov/yolo-face?tab=readme-ov-file
```
