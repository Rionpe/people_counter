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
pyinstaller --noconfirm --windowed --onefile gui.py

# create exe
echo "빌드 완료! 실행 파일은 dist/ 폴더 내에 생성"
```
