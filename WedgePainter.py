import sys
import math
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel
)
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

PUA_START = 0xE000
PHONEME_LIST = [
    # 모음
    "a","i","u","e","o",
    "w", "y",

    # 자음
    "n","m","h","s","c","k","f",
    "j","v","t","r","l","g", "d"
]

# =========================
# Bezier stroke
# =========================
class CurveStroke:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.cp = QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)

# =========================
# Canvas
# =========================
class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(600, 600)
        self.curves = []
        self.selected = None
        self.target = None
        self.setStyleSheet("background:white;border:2px solid black;")

    def bezier(self, c, t):
        x = (1-t)**2*c.p1.x() + 2*(1-t)*t*c.cp.x() + t**2*c.p2.x()
        y = (1-t)**2*c.p1.y() + 2*(1-t)*t*c.cp.y() + t**2*c.p2.y()
        return QPointF(x, y)

    def mousePressEvent(self, e):
        pos = e.position()
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
        pos = e.position()
        if self.target == "p1": self.selected.p1 = pos
        elif self.target == "p2": self.selected.p2 = pos
        elif self.target == "cp": self.selected.cp = pos
        self.update()

    def mouseReleaseEvent(self, e):
        self.target = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(240,240,240),1))
        p.drawLine(0,300,600,300)

        for c in self.curves:
            for i in range(20):
                t1 = i/20
                t2 = (i+1)/20
                a = self.bezier(c,t1)
                b = self.bezier(c,t2)
                w = 2 + 8*math.sin(math.pi*t1)
                p.setPen(QPen(
                    Qt.GlobalColor.black,
                    w,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap
                ))
                p.drawLine(a,b)

            p.setPen(QPen(QColor(200,0,0,120),1))
            p.drawEllipse(c.p1,5,5)
            p.drawEllipse(c.p2,5,5)
            p.setBrush(QColor(0,0,255,80))
            p.drawEllipse(c.cp,7,7)

    def undo(self):
        if self.curves:
            self.curves.pop()
            self.update()

    def clear(self):
        self.curves.clear()
        self.update()

# =========================
# Main window
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.glyphs = {}
        self.idx = 0
        self.setWindowTitle("Bezier PUA Font Maker")

        w = QWidget()
        v = QVBoxLayout(w)

        self.info = QLabel(f"현재 문자: {PHONEME_LIST[0]}")
        v.addWidget(self.info)

        self.canvas = Canvas()
        v.addWidget(self.canvas)

        h = QHBoxLayout()
        b1 = QPushButton("취소")
        b2 = QPushButton("저장")
        b1.clicked.connect(self.canvas.undo)
        b2.clicked.connect(self.save_glyph)
        h.addWidget(b1)
        h.addWidget(b2)
        v.addLayout(h)

        b3 = QPushButton("Export TTF")
        b3.clicked.connect(self.export)
        v.addWidget(b3)

        self.setCentralWidget(w)

    def save_glyph(self):
        if not self.canvas.curves:
            return

        pts = []
        for c in self.canvas.curves:
            for i in range(51):
                pts.append(self.canvas.bezier(c,i/50))

        minx = min(p.x() for p in pts)
        maxx = max(p.x() for p in pts)
        miny = min(p.y() for p in pts)
        maxy = max(p.y() for p in pts)

        w = maxx-minx
        h = maxy-miny
        scale = 980/max(w,h,1)

        strokes = []
        for c in self.canvas.curves:
            line = []
            for i in range(21):
                p = self.canvas.bezier(c,i/20)
                x = int(round((p.x()-minx)*scale + (1024-w*scale)/2))
                y = int(round((maxy-p.y())*scale + 50))
                line.append((x,y))
            strokes.append(line)

        cp = PUA_START + self.idx
        self.glyphs[cp] = strokes
        self.idx += 1

        if self.idx < len(PHONEME_LIST):
            self.info.setText(f"다음 문자: {PHONEME_LIST[self.idx]}")
            self.canvas.clear()
        else:
            self.info.setText("모두 완료")

    def export(self):
        try:
            save_font("conlang_PUA.ttf", self.glyphs)
            self.info.setText("TTF 생성 완료")
        except:
            traceback.print_exc()

# =========================
# Font generation (VALID TTF)
# =========================
def save_font(path, data):
    fb = FontBuilder(1024, isTTF=True)

    glyph_order = [".notdef"] + [f"uni{c:04X}" for c in sorted(data)]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({c:f"uni{c:04X}" for c in data})

    glyf = {".notdef": TTGlyphPen(None).glyph()}
    hmtx = {".notdef": (512, 0)}

    for c, strokes in data.items():
        pen = TTGlyphPen(None)
        maxx = 0

        for s in strokes:
            for i in range(len(s)-1):
                (x1,y1),(x2,y2) = s[i], s[i+1]
                t = i/len(s)
                thick = 40 + 80*math.sin(math.pi*t)
                dx,dy = x2-x1, y2-y1
                L = math.hypot(dx,dy)
                if L == 0:
                    continue
                nx = -dy/L*(thick/2)
                ny =  dx/L*(thick/2)

                p1 = (int(round(x1+nx)), int(round(y1+ny)))
                p2 = (int(round(x2+nx)), int(round(y2+ny)))
                p3 = (int(round(x2-nx)), int(round(y2-ny)))
                p4 = (int(round(x1-nx)), int(round(y1-ny)))

                pen.moveTo(p1)
                pen.lineTo(p2)
                pen.lineTo(p3)
                pen.lineTo(p4)
                pen.closePath()


                maxx = max(maxx, x1, x2)

        name = f"uni{c:04X}"
        glyf[name] = pen.glyph()
        hmtx[name] = (int(maxx+80), 0)

    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(hmtx)
    fb.setupHorizontalHeader(ascent=1000, descent=-200)
    fb.setupOS2(
        sTypoAscender=1000,
        sTypoDescender=-200,
        usWinAscent=1000,
        usWinDescent=200
    )
    fb.setupNameTable({
        "familyName": "UltraConlangPUA",
        "styleName": "Regular",
        "uniqueFontIdentifier": "UltraConlangPUA-1.0",
        "fullName": "UltraConlangPUA Regular"
    })
    fb.setupPost()
    fb.setupMaxp()
    fb.setupHead()
    fb.save(path)

# =========================
# Run
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
