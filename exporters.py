from fpdf import FPDF
import os
import urllib.request
import shutil
from text_utils import transliterate

FONTS_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")

FONT_URLS = {
    "DejaVuSans.ttf":      "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans.ttf",
    "DejaVuSans-Bold.ttf": "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf",
}


def _translit(text: str) -> str:
    return transliterate(text)


def _download_font(url: str, dest: str) -> bool:
    """Скачує шрифт атомарно: спочатку у тимчасовий файл, потім перейменовує.
    Захищає від пошкодженого файлу при обриві з'єднання."""
    tmp_path = dest + ".tmp"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(response, f)
        shutil.move(tmp_path, dest)
        return True
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return False


def _ensure_fonts() -> bool:
    """Перевіряє наявність шрифтів і скачує відсутні. Повертає True якщо обидва є."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    for filename, url in FONT_URLS.items():
        path = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(path):
            if not _download_font(url, path):
                return False
    return True


def build_txt(docs: list, instructions: dict = None) -> str:
    lines = ["Перелік документів для працевлаштування", "=" * 44, ""]
    for i, doc in enumerate(docs, start=1):
        lines.append(f"{i}. {doc['title']}")
        lines.append(f"   Що надати: {doc['details']}")
        lines.append(f"   Формат: {doc['format']}")
        if doc.get("hr_note"):
            lines.append(f"   Примітка: {doc['hr_note']}")
        lines.append("")

    # Інструкції в кінці TXT
    if instructions:
        for doc in docs:
            key = doc.get("instruction_key")
            if key and key in instructions:
                lines.append("=" * 44)
                lines.append(f"Як отримати: {doc['title']}")
                lines.append("=" * 44)
                for step_i, step_text in enumerate(instructions[key], start=1):
                    lines.append(f"  {step_i}. {step_text}")
                lines.append("")

    return "\n".join(lines)


def build_pdf(docs: list, instructions: dict = None) -> bytes:
    fonts_ok = _ensure_fonts()

    pdf = FPDF()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_top_margin(15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    regular_path = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    bold_path    = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
    use_dejavu   = fonts_ok and os.path.exists(regular_path) and os.path.exists(bold_path)

    if use_dejavu:
        pdf.add_font("DejaVu", "",  regular_path)
        pdf.add_font("DejaVu", "B", bold_path)
        font_name = "DejaVu"
        def t(text): return text
    else:
        font_name = "Helvetica"
        def t(text): return _translit(text)

    W = pdf.w - pdf.l_margin - pdf.r_margin
    NX, NY = "LMARGIN", "NEXT"

    # ── Заголовок ──
    pdf.set_font(font_name, "B", 14)
    pdf.multi_cell(W, 10, t("Перелік документів для працевлаштування"), new_x=NX, new_y=NY)
    pdf.ln(4)

    # ── Список документів ──
    for i, doc in enumerate(docs, start=1):
        pdf.set_font(font_name, "B", 11)
        pdf.multi_cell(W, 8, t(f"{i}. {doc['title']}"), new_x=NX, new_y=NY)

        pdf.set_font(font_name, "", 10)
        pdf.multi_cell(W, 7, t(f"Що надати: {doc['details']}"), new_x=NX, new_y=NY)
        pdf.multi_cell(W, 7, t(f"Формат: {doc['format']}"), new_x=NX, new_y=NY)

        if doc.get("hr_note"):
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(W, 7, t(f"Примітка: {doc['hr_note']}"), new_x=NX, new_y=NY)
            pdf.set_text_color(0, 0, 0)

        pdf.ln(3)

    # ── Розділ з інструкціями ──
    if instructions:
        docs_with_instructions = [d for d in docs if d.get("instruction_key") and d["instruction_key"] in instructions]
        if docs_with_instructions:
            pdf.add_page()
            pdf.set_font(font_name, "B", 13)
            pdf.multi_cell(W, 10, t("Інструкції для отримання документів"), new_x=NX, new_y=NY)
            pdf.ln(2)

            # Горизонтальна лінія
            pdf.set_draw_color(255, 209, 0)  # #FFD100
            pdf.set_line_width(0.8)
            pdf.line(pdf.l_margin, pdf.y, pdf.w - pdf.r_margin, pdf.y)
            pdf.ln(6)

            for doc in docs_with_instructions:
                key = doc["instruction_key"]
                steps = instructions[key]

                pdf.set_font(font_name, "B", 11)
                pdf.multi_cell(W, 8, t(f"Як отримати: {doc['title']}"), new_x=NX, new_y=NY)
                pdf.ln(2)

                pdf.set_font(font_name, "", 10)
                for step_i, step_text in enumerate(steps, start=1):
                    pdf.set_font(font_name, "B", 10)
                    num_w = 8
                    pdf.cell(num_w, 7, t(f"{step_i}."))
                    pdf.set_font(font_name, "", 10)
                    pdf.multi_cell(W - num_w, 7, t(step_text), new_x=NX, new_y=NY)

                pdf.ln(5)

    return bytes(pdf.output())
