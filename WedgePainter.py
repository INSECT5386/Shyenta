import sys
import math
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox
)
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

PUA_START = 0xE000
GRID_SIZE = 50

PHONEME_LIST = [
    "a","i","u","e","o","w","y",
    "n","m","h","s","c","k","f",
    "j","v","t","r","x","q","l","g","d"
]

# =========================
# Stroke primitives
# =========================
class CurveStroke:
    def __init__(self, p1, p2, cp=None):
        self.p1 = p1
        self.p2 = p2
        self.cp = cp if cp else QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)

class DotStroke:
    def __init__(self, p, r=12):
        self.p = p
        self.r = r

# =========================
# Canvas
# =========================
class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 600)
        self.curves = []
        self.dots = []
        self.selected = None
        self.target = None
        self.show_grid = True
        self.dot_mode = False
        self.setStyleSheet("background:white;border:2px solid black;")

    def snap(self, p):
        return QPointF(
            round(p.x()/GRID_SIZE)*GRID_SIZE,
            round(p.y()/GRID_SIZE)*GRID_SIZE
        )

    def bezier(self, c, t):
        x = (1-t)**2*c.p1.x() + 2*(1-t)*t*c.cp.x() + t**2*c.p2.x()
        y = (1-t)**2*c.p1.y() + 2*(1-t)*t*c.cp.y() + t**2*c.p2.y()
        return QPointF(x, y)

    def mousePressEvent(self, e):
        pos = self.snap(e.position())

        if self.dot_mode:
            self.dots.append(DotStroke(pos))
            self.update()
            return

        for c in self.curves:
            for name, p in (("p1",c.p1),("p2",c.p2),("cp",c.cp)):
                if math.hypot(p.x()-pos.x(), p.y()-pos.y()) < 15:
                    self.selected = c
                    self.target = name
                    return

        c = CurveStroke(pos, pos)
        self.curves.append(c)
        self.selected = c
        self.target = "p2"

    def mouseMoveEvent(self, e):
        if not self.selected:
            return
        pos = self.snap(e.position())
        if self.target == "p1": self.selected.p1 = pos
        elif self.target == "p2": self.selected.p2 = pos
        elif self.target == "cp": self.selected.cp = pos
        self.update()

    def mouseReleaseEvent(self, e):
        self.target = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.show_grid:
            p.setPen(QPen(QColor(230,230,230),1))
            for i in range(0,601,GRID_SIZE):
                p.drawLine(i,0,i,600)
                p.drawLine(0,i,600,i)

        for c in self.curves:
            for i in range(24):
                t1 = i/24
                t2 = (i+1)/24
                a = self.bezier(c,t1)
                b = self.bezier(c,t2)
                w = 3 + 10*math.sin(math.pi*t1)
                p.setPen(QPen(QColor(Qt.GlobalColor.black),w,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))

                p.drawLine(a,b)

            p.setPen(QPen(QColor(200,0,0),1))
            p.drawEllipse(c.p1,5,5)
            p.drawEllipse(c.p2,5,5)
            p.setBrush(QColor(0,0,255,80))
            p.drawEllipse(c.cp,7,7)

        p.setBrush(Qt.GlobalColor.black)
        for d in self.dots:
            p.drawEllipse(d.p, d.r, d.r)

    def undo(self):
        if self.dot_mode and self.dots:
            self.dots.pop()
        elif self.curves:
            self.curves.pop()
        self.update()

    def clear(self):
        self.curves.clear()
        self.dots.clear()
        self.update()

# =========================
# Main window
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.glyphs = {}
        self.idx = 0
        self.setWindowTitle("PUA Font Builder Pro")

        w = QWidget()
        v = QVBoxLayout(w)

        self.info = QLabel(f"현재 문자: {PHONEME_LIST[0]}")
        v.addWidget(self.info)

        self.canvas = Canvas()
        v.addWidget(self.canvas)

        h = QHBoxLayout()

        undo = QPushButton("되돌리기")
        save = QPushButton("글자 저장")
        undo.clicked.connect(self.canvas.undo)
        save.clicked.connect(self.save_glyph)

        grid = QCheckBox("격자")
        grid.setChecked(True)
        grid.stateChanged.connect(lambda s: setattr(self.canvas, "show_grid", bool(s)))

        dot = QCheckBox("점 모드")
        dot.stateChanged.connect(lambda s: setattr(self.canvas, "dot_mode", bool(s)))

        h.addWidget(undo)
        h.addWidget(save)
        h.addWidget(grid)
        h.addWidget(dot)
        v.addLayout(h)

        export = QPushButton("TTF 생성")
        export.clicked.connect(self.export)
        v.addWidget(export)

        self.setCentralWidget(w)

    def save_glyph(self):
        if not self.canvas.curves and not self.canvas.dots:
            return

        strokes = []

        for c in self.canvas.curves:
            line = []
            for i in range(32):
                p = self.canvas.bezier(c,i/31)
                line.append((p.x(), p.y()))
            strokes.append(("curve", line))

        for d in self.canvas.dots:
            strokes.append(("dot", (d.p.x(), d.p.y(), d.r)))

        self.glyphs[PUA_START+self.idx] = strokes
        self.idx += 1

        if self.idx < len(PHONEME_LIST):
            self.info.setText(f"다음 문자: {PHONEME_LIST[self.idx]}")
            self.canvas.clear()
        else:
            self.info.setText("완료")

    def export(self):
        try:
            save_font("conlang_PUA.ttf", self.glyphs)
            self.info.setText("TTF 생성 완료")
        except:
            traceback.print_exc()

def save_font(path, data):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    import math

    UNITS_PER_EM = 1024
    SCALE = 0.85 # 글자 크기를 살짝 줄여 여백 확보
    LEFT_MARGIN = 100 # 좌측 여백 증가
    BASELINE = int(UNITS_PER_EM * 0.15)

    # [수정] 두께를 5로 낮추어 훨씬 날카로운 펜 느낌 구현
    BASE_THICK = 5  
    DOT_R = 7 # 점 크기도 더 작게 조절

    fb = FontBuilder(UNITS_PER_EM, isTTF=True)

    glyph_order = [".notdef"] + [f"uni{c:04X}" for c in data]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({c: f"uni{c:04X}" for c in data})

    glyf = {".notdef": TTGlyphPen(None).glyph()}
    hmtx = {".notdef": (UNITS_PER_EM, 0)}

    for c, strokes in data.items():
        pen = TTGlyphPen(None)
        
        all_xs, all_ys = [], []
        for kind, obj in strokes:
            if kind == "curve":
                for x, y in obj:
                    all_xs.append(x); all_ys.append(y)
            else:
                x, y, r = obj
                all_xs.extend([x - r, x + r])
                all_ys.extend([y - r, y + r])

        if not all_xs:
            minx, maxx, miny, maxy = 0, 0, 0, 0
        else:
            minx, maxx = min(all_xs), max(all_xs)
            miny, maxy = min(all_ys), max(all_ys)

        width = maxx - minx
        height = maxy - miny
        if width == 0: width = 1
        if height == 0: height = 1

        def tx(x):
            return int((x - minx) / width * UNITS_PER_EM * SCALE + LEFT_MARGIN)

        def ty(y):
            return int((maxy - y) / height * UNITS_PER_EM * SCALE + BASELINE)

        maxx_adv = 0

        for kind, obj in strokes:
            if kind == "curve":
                pts = obj
                if len(pts) < 2: continue

                left_side = []
                right_side = []
                n = len(pts)
                
                for i in range(n - 1):
                    x1, y1 = pts[i]
                    x2, y2 = pts[i+1]
                    
                    dx, dy = x2 - x1, y2 - y1
                    L = math.hypot(dx, dy)
                    if L == 0: continue

                    nx = -dy / L * (BASE_THICK / 2)
                    ny =  dx / L * (BASE_THICK / 2)

                    # 경로의 바깥쪽 윤곽선들만 정교하게 수집
                    left_side.append((tx(x1 + nx), ty(y1 + ny)))
                    right_side.append((tx(x1 - nx), ty(y1 - ny)))
                    
                    if i == n - 2:
                        left_side.append((tx(x2 + nx), ty(y2 + ny)))
                        right_side.append((tx(x2 - nx), ty(y2 - ny)))

                if left_side and right_side:
                    pen.moveTo(left_side[0])
                    for p in left_side[1:]:
                        pen.lineTo(p)
                    # 끝부분에서 반대편으로 넘어가기 전 아주 작은 직선을 그어 뭉툭함을 방지
                    for p in reversed(right_side):
                        pen.lineTo(p)
                    pen.closePath()

                    for p in left_side + right_side:
                        maxx_adv = max(maxx_adv, p[0])

            else:
                x, y, _ = obj
                cx, cy = tx(x), ty(y)
                r = DOT_R
                steps = 16
                pen.moveTo((cx + r, cy))
                for i in range(1, steps + 1):
                    a = 2 * math.pi * i / steps
                    pen.lineTo((cx + math.cos(a) * r, cy + math.sin(a) * r))
                pen.closePath()
                maxx_adv = max(maxx_adv, cx + r)

        name = f"uni{c:04X}"
        glyf[name] = pen.glyph()
        ADV_PAD = 80 # 자간 여백을 더 늘려 가독성 향상
        hmtx[name] = (maxx_adv + ADV_PAD, 0)

    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(hmtx)
    fb.setupHorizontalHeader(ascent=int(UNITS_PER_EM * 0.9), descent=-int(UNITS_PER_EM * 0.1))
    fb.setupOS2(sTypoAscender=int(UNITS_PER_EM * 0.9), sTypoDescender=-int(UNITS_PER_EM * 0.1))
    fb.setupNameTable({
        "familyName": "UltraConlangPUA",
        "styleName": "Regular",
        "uniqueFontIdentifier": "UltraConlangPUA-2.5-UltraThin",
        "fullName": "UltraConlangPUA Regular"
    })
    fb.setupPost()
    fb.setupMaxp()
    fb.setupHead()
    fb.save(path)
# Run
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
