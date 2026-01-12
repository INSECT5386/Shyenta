!pip install PyQt6
!pip install rdp
!pip install fonttools
import sys
import numpy as np
from rdp import rdp
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QHBoxLayout
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

# 1. 음소 리스트 (로마자 키와 직접 매핑)
# 복합 음소(sh, ch 등)는 일단 PUA 영역에 두거나, 
# 사용하지 않는 알파벳 키(q, x 등)에 할당하는 것이 타이핑에 유리합니다.
PHONEME_LIST = [
{"char": "sh", "key": "S", "desc": "/ʃ/ (Voiceless post-alveolar fricative)"}, 
    {"char": "ch", "key": "C", "desc": "/tʃ/ (Voiceless post-alveolar affricate)"}, 
    {"char": "zh", "key": "Z", "desc": "/ʒ/ (Voiced post-alveolar fricative)"}, 
    {"char": "f", "key": "F", "desc": "/f/ (Voiceless labiodental fricative)"},
    {"char": "v", "key": "V", "desc": "/v/ (Voiced labiodental fricative)"}, 
    {"char": "l", "key": "L", "desc": "/l/ (Alveolar lateral approximant)"},
    {"char": "k", "key": "K", "desc": "/k/ (Voiceless velar plosive)"}, 
    {"char": "t", "key": "T", "desc": "/t/ (Voiceless alveolar plosive)"},
    {"char": "h", "key": "H", "desc": "/h/ (Voiceless glottal fricative)"}, 
    {"char": "n", "key": "N", "desc": "/n/ (Alveolar nasal)"}, 
    {"char": "m", "key": "M", "desc": "/m/ (Bilabial nasal)"},
    {"char": "oe", "desc": "oe", "key": "W"}, # 예: W 키에 매핑
    {"char": "wi", "desc": "wi", "key": "Q"}, # 예: Q 키에 매핑
    {"char": "ui", "desc": "ui", "key": "X"}, # 예: X 키에 매핑
    {"char": "yo", "desc": "yo", "key": "Y"},
    {"char": "ya", "desc": "ya", "key": "J"}, # 예: J 키에 매핑
    {"char": "ye", "desc": "ye", "key": "P"},
    {"char": "e", "desc": "e", "key": "E"}, 
    {"char": "u", "desc": "u", "key": "U"},
    {"char": "a", "desc": "a", "key": "A"}, 
    {"char": "i", "desc": "i", "key": "I"}
]

class WedgeManager:
    def __init__(self):
        self.all_glyphs = {} 
        self.current_idx = 0
        
    def save_current(self, points):
        # 유니코드를 해당 알파벳의 ASCII 코드로 설정
        char_key = PHONEME_LIST[self.current_idx]["key"]
        code = ord(char_key) 
        self.all_glyphs[code] = points
        self.current_idx += 1
        return self.current_idx < len(PHONEME_LIST)

def create_wedge_font(output_path, glyph_data):
    fb = FontBuilder(unitsPerEm=1024)
    glyph_names = [".notdef"] + [f"uni{code:04X}" for code in glyph_data.keys()]
    fb.setupGlyphOrder(glyph_names)
    fb.setupCharacterMap({code: f"uni{code:04X}" for code in glyph_data.keys()})
    
    glyph_set = {".notdef": TTGlyphPen(None).glyph()}
    h_metrics = {".notdef": (500, 0)}
    
    for code, points in glyph_data.items():
        pen = TTGlyphPen(None)
        if len(points) > 2:
            pen.moveTo(points[0])
            for p in points[1:]: pen.lineTo(p)
            pen.closePath()
        g_name = f"uni{code:04X}"
        glyph_set[g_name] = pen.glyph()
        
        # 선형 구조 핵심: 글자 너비를 실제 그린 폭에 딱 맞춤
        xs = [p[0] for p in points] if points else [0]
        width = int(max(xs) + 150) # 여백을 약간 줄여서 글자가 이어지게 함
        h_metrics[g_name] = (width, 0)

    fb.setupGlyf(glyph_set)
    fb.setupHorizontalMetrics(h_metrics)
    fb.setupHorizontalHeader()
    fb.setupNameTable({"familyName": "WedgeLinear", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    fb.save(output_path)

class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 600)
        self.points = []
        self.drawing = False
        self.setStyleSheet("background-color: white; border: 2px solid black;")

    def mousePressEvent(self, event):
        self.points = [event.position()]
        self.drawing = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.points.append(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        self.drawing = False
        if len(self.points) < 3: return
        raw_pts = [[p.x(), 600 - p.y()] for p in self.points]
        self.simplified_points = rdp(raw_pts, epsilon=2.0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if len(self.points) > 1:
            pen = QPen(Qt.GlobalColor.black, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            for i in range(len(self.points)-1):
                painter.drawLine(self.points[i], self.points[i+1])
    
    def clear(self):
        self.points = []
        if hasattr(self, 'simplified_points'): del self.simplified_points
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = WedgeManager()
        self.setWindowTitle("선형 인공어 폰트 제작기")
        
        layout = QVBoxLayout()
        self.info_label = QLabel(self.get_current_text())
        self.info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.info_label)
        
        self.canvas = Canvas()
        layout.addWidget(self.canvas)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("다음 음소 저장")
        self.save_btn.clicked.connect(self.next_step)
        self.export_btn = QPushButton("선형 폰트 생성 (.ttf)")
        self.export_btn.clicked.connect(self.export_ttf)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    def get_current_text(self):
        if self.manager.current_idx < len(PHONEME_LIST):
            w = PHONEME_LIST[self.manager.current_idx]
            return f"그릴 문자: {w['char']} ({w['desc']})  -> 매핑될 키: [{w['key']}]"
        return "모든 음소 완료! 폰트를 생성하세요."

    def next_step(self):
        if hasattr(self.canvas, 'simplified_points'):
            pts = np.array(self.canvas.simplified_points)
            pts[:, 0] -= pts[:, 0].min()
            pts[:, 1] -= pts[:, 1].min()
            scale = 800 / max(pts.max(), 1)
            final_pts = (pts * scale).astype(int).tolist()
            
            has_next = self.manager.save_current(final_pts)
            self.canvas.clear()
            self.info_label.setText(self.get_current_text())
            if not has_next:
                self.save_btn.setEnabled(False)
        else:
            print("그림을 그려주세요.")

    def export_ttf(self):
        if not self.manager.all_glyphs: return
        create_wedge_font("conlang_linear.ttf", self.manager.all_glyphs)
        print("✅ 선형 폰트 생성 완료!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
