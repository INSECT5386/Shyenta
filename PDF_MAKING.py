import json
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.pagesizes import A4

def generate_pdf_from_pua_json(json_file, output_pdf, conlang_font_path):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSON 로드 실패: {e}")
        return

    c = canvas.Canvas(output_pdf, pagesize=A4)
    width, height = A4

    # === 폰트 등록 ===
    CONLANG_FONT = "ConlangPUA"
    KOREAN_FONT = "HYSMyeongJo-Medium"

    pdfmetrics.registerFont(TTFont(CONLANG_FONT, conlang_font_path))
    pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))

    margin = 50
    curr_y = height - margin

    def page_break(y, line_h=14):
        nonlocal curr_y
        if y < 60:
            c.showPage()
            curr_y = height - margin
            return curr_y
        return y

    def draw_wrapped(text, x, y, size=10):
        nonlocal curr_y
        y = page_break(y)
        cx = x

        for ch in text:
            # PUA 영역 → 콘랭 폰트
            if 0xE000 <= ord(ch) <= 0xF8FF:
                font = CONLANG_FONT
                out = ch
            else:
                font = KOREAN_FONT
                out = ch

            w = pdfmetrics.stringWidth(out, font, size)

            if cx + w > width - margin:
                y -= size * 1.5
                y = page_break(y)
                cx = x + 20

            c.setFont(font, size)
            c.drawString(cx, y, out)
            cx += w

        curr_y = y - size * 1.8
        return curr_y


    # === 타이틀 ===
    c.setFont(KOREAN_FONT, 18)
    c.drawCentredString(width / 2, curr_y, "인공어 전체 명세서 (PUA 기반)")
    curr_y -= 40

    # === 내용 출력 ===
    for section, content in data.items():
        curr_y = page_break(curr_y, 80)

        c.setLineWidth(1)
        c.line(margin, curr_y + 5, width - margin, curr_y + 5)
        curr_y = draw_wrapped(f"■ {section}", margin, curr_y, size=12)

        if isinstance(content, dict):
            for key, val in content.items():
                if isinstance(val, dict):
                    parts = []
                    for k, v in val.items():
                        if isinstance(v, dict):
                            sub = ", ".join(f"{sk}:{sv}" for sk, sv in v.items())
                            parts.append(f"[{k}: {sub}]")
                        else:
                            parts.append(f"{k}: {v}")
                    line = f"• {key}  →  " + " | ".join(parts)
                else:
                    line = f"• {key}: {val}"

                curr_y = draw_wrapped(line, margin + 10, curr_y)

        curr_y -= 10

    c.save()
    print(f"PDF 생성 완료: {output_pdf}")

if __name__ == "__main__":
    JSON_NAME = "conlang_pua.json"
    FONT_NAME = "conlang_PUA.ttf"
    OUT_PDF = "Conlang_PUA_Specs.pdf"

    if os.path.exists(JSON_NAME) and os.path.exists(FONT_NAME):
        generate_pdf_from_pua_json(JSON_NAME, OUT_PDF, FONT_NAME)
    else:
        print("JSON 또는 폰트 파일 없음")
