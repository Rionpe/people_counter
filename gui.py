import tkinter as tk
from pathlib import Path
import queue
import cv2
from PIL import Image, ImageTk
from settings import SettingsManager
from tracker import PeopleTracker

class PeopleCounterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("People Counter")
        self.geometry("800x850")
        self.log_queue = queue.Queue()
        self.settings_mgr = SettingsManager()
        self.settings_mgr.load()
        self.tracker = None
        self._build_ui()
        self._init()
        self.video_lbl.grid_remove()
        self.after(100, self._process_logs)
        self.bind('<Key>', self._on_key)

    def _build_ui(self):
         # 모델 선택
        tk.Label(self, text="모델 선택:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.model_var = tk.StringVar(value=self.settings_mgr.settings['model'])
        model_frame = tk.Frame(self)
        model_frame.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        for m in ["yolov11n-face.pt", "yolov11s-face.pt", "yolov11m-face.pt"]:
            tk.Radiobutton(model_frame, text=m, variable=self.model_var, value=m).pack(side=tk.LEFT)

        # 결과 저장 폴더
        tk.Label(self, text="결과 저장 폴더:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.out_e = tk.Entry(self, width=50)
        self.out_e.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # CSV 파일명
        tk.Label(self, text="CSV 파일명:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.csv_e = tk.Entry(self, width=50)
        self.csv_e.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        # 영상 소스 설정
        tk.Label(self, text="영상 소스 설정:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.src_var = tk.StringVar(value=self.settings_mgr.settings['source'])
        source_frame = tk.Frame(self)
        source_frame.grid(row=3, column=1, sticky="w", padx=10, pady=5)
        tk.Radiobutton(source_frame, text="YouTube URL", variable=self.src_var, value="YouTube URL", command=self._toggle_source).pack(side=tk.LEFT)
        # (필요시 다른 옵션도 추가)

        # YouTube URL 입력
        self.src_lbl = tk.Label(self, text="YouTube 주소 입력:")
        self.src_i   = tk.Entry(self, width=50)
        # 토글 함수에서 grid/grid_remove 처리
        self._toggle_source()

        # Confidence
        tk.Label(self, text="Confidence (0~1):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.conf_e = tk.Entry(self, width=10)
        self.conf_e.grid(row=5, column=1, sticky="w", padx=10, pady=5)

        # IOU
        tk.Label(self, text="IOU (0~1):").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.iou_e = tk.Entry(self, width=10)
        self.iou_e.grid(row=6, column=1, sticky="w", padx=10, pady=5)

        # 포그라운드 실행
        self.show_v = tk.BooleanVar(value=self.settings_mgr.settings['show'])
        tk.Checkbutton(self, text="포그라운드 실행", variable=self.show_v, bg="lightblue")\
            .grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # 버튼 프레임
        bf = tk.Frame(self)
        bf.grid(row=8, column=0, columnspan=2, pady=10)
        tk.Button(bf, text="초기화", command=self._init, bg="lightblue", width=5).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="▶ 추적 시작", command=self._start, bg="lightgreen", width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="✖ 종료", command=self._stop, bg="salmon", width=5).pack(side=tk.LEFT, padx=5)

        # 로그창
        self.log_txt = tk.Text(self, height=8, width=100, state='disabled')
        self.log_txt.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        # 비디오 화면 (초기엔 숨김)
        self.video_lbl = tk.Label(self)
        self.video_lbl.grid(row=10, column=0, columnspan=2, sticky="nsew")
        self.video_lbl.grid_remove()

    def _toggle_source(self):
        if self.src_var.get()=="YouTube URL":
            self.src_lbl.grid(row=4,column=0,padx=10,pady=5,sticky="w")
            self.src_i.grid(row=4,column=1,padx=10,pady=5,sticky="w")
        else:
            self.src_lbl.grid_remove(); self.src_i.grid_remove()

    def _validate(self,val):
        try: return 0<=float(val)<=1
        except: return False

    def _init(self):
        self.settings_mgr.load()
        s=self.settings_mgr.settings
        self.model_var.set(s['model'])
        self.out_e.delete(0,tk.END);self.out_e.insert(0,s['output_directory'])
        self.csv_e.delete(0,tk.END);self.csv_e.insert(0,s['csv_filename'])
        self.src_var.set(s['source']);self.src_i.delete(0,tk.END);self.src_i.insert(0,s['url'])
        self.conf_e.delete(0,tk.END);self.conf_e.insert(0,str(s['conf']))
        self.iou_e.delete(0,tk.END);self.iou_e.insert(0,str(s['iou']))
        self.show_v.set(s['show'])
        self.log("초기화 완료")
        self._toggle_source()

    def _save(self):
        cfg={'model':self.model_var.get(),'output_directory':self.out_e.get(),
             'csv_filename':self.csv_e.get(),'source':self.src_var.get(),
             'url':self.src_i.get(),'conf':self.conf_e.get(),
             'iou':self.iou_e.get(),'show':self.show_v.get()}
        Path(cfg['output_directory']).mkdir(parents=True,exist_ok=True)
        (Path(cfg['output_directory'])/cfg['csv_filename']).touch(exist_ok=True)
        try:
            cfg['conf']=float(cfg['conf']);cfg['iou']=float(cfg['iou'])
        except:
            self.log("Error: Confidence/IOU")
            return False
        self.settings_mgr.settings.update(cfg)
        self.settings_mgr.save()
        self.log("설정 저장됨")
        return True

    def _start(self):
        if not self._save(): return
        self.video_lbl.grid()
        self.tracker = PeopleTracker()
        self.tracker.start(frame_callback=self._show, log_callback=self.log)
        self.log("추적 시작")

    def _stop(self):
        if self.tracker:
            self.tracker.stop()
            self.log("추적 종료")
        self.video_lbl.grid_remove()

    def _show(self,frame):
        img=cv2.cvtColor(cv2.resize(frame,(800,400)),cv2.COLOR_BGR2RGB)
        photo=ImageTk.PhotoImage(Image.fromarray(img))
        self.video_lbl.config(image=photo);self.video_lbl.image=photo

    def _process_logs(self):
        while not self.log_queue.empty():
            m=self.log_queue.get_nowait()
            self.log_txt.config(state='normal');self.log_txt.insert(tk.END,m+"\n")
            self.log_txt.see(tk.END);self.log_txt.config(state='disabled')
        self.after(100,self._process_logs)

    def log(self,msg): self.log_queue.put(str(msg))

    def _on_key(self,e):
        if e.char=='q': self._stop()

if __name__=='__main__':
    app=PeopleCounterApp();app.mainloop()