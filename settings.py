from pathlib import Path
import json

class SettingsManager:
    """
    settings.json 로 설정 로드/저장
    """
    DEFAULTS = {
        "model": "yolov11m-face.pt",
        "output_directory": "./output/",
        "csv_filename": "people_counting.csv",
        "source": "YouTube URL",
        "url": "",
        "conf": 0.35,
        "iou": 0.5,
        "show": False
    }

    def __init__(self, path: str = "settings.json"):
        self.path = Path(path)
        self.settings = self.DEFAULTS.copy()

    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.settings.update(data)
            except Exception:
                pass
        # 타입 보정
        try:
            self.settings["conf"] = float(self.settings.get("conf", 0.35))
            self.settings["iou"] = float(self.settings.get("iou", 0.5))
            self.settings["show"] = bool(self.settings.get("show", False))
        except Exception:
            self.settings = self.DEFAULTS.copy()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.settings, ensure_ascii=False, indent=4),
            encoding="utf-8"
        )