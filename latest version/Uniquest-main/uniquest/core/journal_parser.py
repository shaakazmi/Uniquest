"""
Pakistan IPO Trade Marks Journal Parser for IPOGenie.
Extracts trademark applications from official journal PDFs.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    import fitz  # PyMuPDF
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False


@dataclass
class ParsedTrademark:
    application_number: str = ""
    trademark_name:     str = ""
    nice_class:         Optional[int] = None
    goods_services:     str = ""
    applicant_name:     str = ""
    filing_date:        str = ""
    logo_path:          Optional[str] = None
    country:            str = "Pakistan"
    source_page:        int = 0
    raw_text:           str = ""

    def is_complete(self) -> bool:
        return bool(self.application_number and self.trademark_name)


PATTERNS = {
    "app_number":  re.compile(r"Application\s*No\.?\s*[:.]?\s*(\d{4,})", re.IGNORECASE),
    "title":       re.compile(r"Title\s*[:.]?\s*([A-Z0-9][^\n]{1,200})", re.IGNORECASE),
    "class":       re.compile(r"\bClass\s*[:.]?\s*(\d{1,2})\b", re.IGNORECASE),
    "goods":       re.compile(
        r"Goods\s+or\s+services\s*[:.]?\s*(.+?)"
        r"(?=(Name\s+and\s+address|Date\s+of\s+filing|Description|Advertised|$))",
        re.IGNORECASE | re.DOTALL
    ),
    "applicant":   re.compile(
        r"Name\s+and\s+address\s+of\s+Applicant\s*[:.]?\s*(.+?)"
        r"(?=(Date\s+of\s+filing|Agent|Description|Advertised|$))",
        re.IGNORECASE | re.DOTALL
    ),
    "filing_date": re.compile(
        r"Date\s+of\s+filing\s*[:.]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
        re.IGNORECASE
    ),
    "advertised":  re.compile(r"Advertised\s+under\s+section", re.IGNORECASE),
}


def parse_journal_pdf(pdf_path, output_dir, progress_cb=None, cancel_check=None):
    if not PYMUPDF_OK:
        raise ImportError("PyMuPDF (fitz) is required")

    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    all_sections = []

    for page_idx in range(total_pages):
        if cancel_check and cancel_check():
            break
        if progress_cb:
            progress_cb(page_idx + 1, total_pages, f"Reading page {page_idx + 1}/{total_pages}")

        page = doc[page_idx]
        sections = _extract_page_sections(page, page_idx + 1, output_dir_path)
        all_sections.extend(sections)

    doc.close()

    # Parse + handle multi-page continuation
    trademarks = []
    i = 0
    while i < len(all_sections):
        sec = all_sections[i]
        tm = _parse_section(sec)

        # Continuation: if incomplete AND next section doesn't start with "Advertised"
        while (
            not tm.is_complete()
            and i + 1 < len(all_sections)
            and not PATTERNS["advertised"].search(all_sections[i + 1]["text"][:200])
        ):
            i += 1
            sec["text"] += "\n" + all_sections[i]["text"]
            tm = _parse_section(sec)

        if tm.is_complete():
            trademarks.append(tm)
        i += 1

    return trademarks


def _extract_page_sections(page, page_number, output_dir):
    page_height = page.rect.height

    # Text blocks with positions
    text_dict = page.get_text("dict")
    text_blocks = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        bbox = block.get("bbox", [0, 0, 0, 0])
        parts = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                parts.append(span.get("text", ""))
        text = " ".join(parts).strip()
        if text:
            text_blocks.append({"y": bbox[1], "text": text})

    # Images with positions
    images_info = []
    for img_idx, img in enumerate(page.get_images(full=True)):
        try:
            xref = img[0]
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            rect = rects[0]
            if rect.width < 30 or rect.height < 30:
                continue

            pix = fitz.Pixmap(page.parent, xref)
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            img_filename = f"page{page_number:04d}_img{img_idx:03d}.png"
            img_path = output_dir / img_filename
            pix.save(str(img_path))
            pix = None

            images_info.append({
                "y": rect.y0,
                "path": str(img_path),
                "width": rect.width,
                "height": rect.height,
            })
        except Exception:
            continue

    # Find "Advertised under section" positions — these delimit sections
    advertised_ys = sorted(
        tb["y"] for tb in text_blocks
        if PATTERNS["advertised"].search(tb["text"])
    )

    if not advertised_ys:
        # Whole page = one section
        boundaries = [(0, page_height)]
    else:
        boundaries = []
        for i, y in enumerate(advertised_ys):
            start_y = 0 if i == 0 else advertised_ys[i - 1]
            end_y = advertised_ys[i + 1] if i + 1 < len(advertised_ys) else page_height
            boundaries.append((start_y, end_y))

    sections = []
    for (y_start, y_end) in boundaries:
        section_text = "\n".join(
            tb["text"] for tb in text_blocks
            if y_start <= tb["y"] < y_end
        )
        section_imgs = sorted(
            [img for img in images_info if y_start <= img["y"] < y_end],
            key=lambda x: x["y"]
        )
        logo_path = section_imgs[0]["path"] if section_imgs else None

        sections.append({
            "text": section_text,
            "logo_path": logo_path,
            "page": page_number,
        })

    return sections


def _parse_section(sec):
    text = sec["text"]
    tm = ParsedTrademark(
        logo_path=sec.get("logo_path"),
        source_page=sec.get("page", 0),
        raw_text=text[:2000],
    )

    m = PATTERNS["app_number"].search(text)
    if m:
        tm.application_number = m.group(1).strip()

    m = PATTERNS["title"].search(text)
    if m:
        title = m.group(1).strip()
        title = re.split(r"\s+Class\s*[:.]", title, flags=re.IGNORECASE)[0]
        tm.trademark_name = title.strip(" .:")

    m = PATTERNS["class"].search(text)
    if m:
        try:
            cls = int(m.group(1))
            if 1 <= cls <= 45:
                tm.nice_class = cls
        except ValueError:
            pass

    m = PATTERNS["goods"].search(text)
    if m:
        goods = re.sub(r"\s+", " ", m.group(1).strip())
        tm.goods_services = goods[:500]

    m = PATTERNS["applicant"].search(text)
    if m:
        applicant = re.sub(r"\s+", " ", m.group(1).strip())
        tm.applicant_name = applicant[:400]

    m = PATTERNS["filing_date"].search(text)
    if m:
        tm.filing_date = m.group(1).strip()

    return tm