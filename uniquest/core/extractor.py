import os
import re
import csv
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

from database.db import get_connection, get_db_path
from database.models import (
    TextChunk, ExtractedImage,
    IMAGE_EXTENSIONS, DOCUMENT_EXTENSIONS
)


# ─────────────────────────────────────────────
#  IMAGES STORAGE FOLDER
# ─────────────────────────────────────────────
def get_images_dir(project_id: int) -> Path:
    """Where extracted images are saved locally"""
    base = Path(get_db_path()).parent / "extracted_images" / str(project_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


# ─────────────────────────────────────────────
#  TEXT CLEANING
# ─────────────────────────────────────────────
def clean_text(text: str) -> str:
    """Normalize whitespace and remove junk characters"""
    if not text:
        return ""
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def chunk_text(text: str, min_words: int = 8) -> List[str]:
    """
    Split text into meaningful chunks (paragraphs).
    Filters out chunks that are too short to be meaningful.
    """
    if not text:
        return []
    paragraphs = text.split('\n\n')
    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        words = para.split()
        if len(words) < min_words:
            continue
        chunks.append(para)
    return chunks


# ─────────────────────────────────────────────
#  PDF EXTRACTOR
# ─────────────────────────────────────────────
def extract_from_pdf(file_id, project_id, file_path):
    text_chunks = []
    image_paths = []

    try:
        import fitz
    except ImportError:
        print("PyMuPDF not installed.")
        return text_chunks, image_paths

    try:
        doc = fitz.open(file_path)
        images_dir = get_images_dir(project_id)

        for page_num, page in enumerate(doc, start=1):
            raw_text = page.get_text("text")
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned)
            for idx, chunk in enumerate(chunks):
                text_chunks.append(TextChunk(
                    file_id=file_id,
                    project_id=project_id,
                    chunk_index=idx,
                    content=chunk,
                    page_number=page_num,
                    chunk_type="paragraph",
                    word_count=len(chunk.split()),
                ))

            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    img_name = f"f{file_id}_p{page_num}_i{img_idx}.{ext}"
                    img_path = images_dir / img_name
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    image_paths.append(str(img_path))
                except Exception as e:
                    print(f"  Image extract error: {e}")

        doc.close()
    except Exception as e:
        print(f"PDF extraction error [{file_path}]: {e}")

    return text_chunks, image_paths


# ─────────────────────────────────────────────
#  DOCX EXTRACTOR
# ─────────────────────────────────────────────
def extract_from_docx(file_id, project_id, file_path):
    text_chunks = []
    image_paths = []

    try:
        from docx import Document
    except ImportError:
        print("python-docx not installed.")
        return text_chunks, image_paths

    try:
        doc = Document(file_path)
        images_dir = get_images_dir(project_id)
        full_text = "\n\n".join(
            p.text for p in doc.paragraphs if p.text.strip()
        )
        cleaned = clean_text(full_text)
        chunks = chunk_text(cleaned)
        for idx, chunk in enumerate(chunks):
            text_chunks.append(TextChunk(
                file_id=file_id,
                project_id=project_id,
                chunk_index=idx,
                content=chunk,
                page_number=0,
                chunk_type="paragraph",
                word_count=len(chunk.split()),
            ))

        import zipfile
        with zipfile.ZipFile(file_path, 'r') as z:
            media_files = [
                f for f in z.namelist()
                if f.startswith("word/media/")
            ]
            for mf in media_files:
                img_name = f"f{file_id}_{Path(mf).name}"
                img_path = images_dir / img_name
                with z.open(mf) as src, open(img_path, "wb") as dst:
                    dst.write(src.read())
                image_paths.append(str(img_path))

    except Exception as e:
        print(f"DOCX extraction error [{file_path}]: {e}")

    return text_chunks, image_paths


# ─────────────────────────────────────────────
#  TXT / RTF EXTRACTOR
# ─────────────────────────────────────────────
def extract_from_txt(file_id, project_id, file_path):
    text_chunks = []

    try:
        ext = file_path.rsplit(".", 1)[-1].lower()

        if ext == "rtf":
            try:
                from striprtf.striprtf import rtf_to_text
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw = rtf_to_text(f.read())
            except ImportError:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()

        cleaned = clean_text(raw)
        chunks = chunk_text(cleaned)
        for idx, chunk in enumerate(chunks):
            text_chunks.append(TextChunk(
                file_id=file_id,
                project_id=project_id,
                chunk_index=idx,
                content=chunk,
                page_number=0,
                chunk_type="paragraph",
                word_count=len(chunk.split()),
            ))

    except Exception as e:
        print(f"TXT/RTF extraction error [{file_path}]: {e}")

    return text_chunks, []


# ─────────────────────────────────────────────
#  XLSX / XLS / CSV EXTRACTOR
# ─────────────────────────────────────────────
def extract_from_spreadsheet(file_id, project_id, file_path):
    text_chunks = []
    ext = file_path.rsplit(".", 1)[-1].lower()

    try:
        if ext == "csv":
            rows = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    line = " | ".join(
                        cell.strip() for cell in row if cell.strip()
                    )
                    if line:
                        rows.append(line)
            full_text = "\n".join(rows)
        else:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            rows = []
            for sheet in wb.worksheets:
                rows.append(f"[Sheet: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    line = " | ".join(
                        str(cell).strip()
                        for cell in row
                        if cell is not None and str(cell).strip()
                    )
                    if line:
                        rows.append(line)
            wb.close()
            full_text = "\n".join(rows)

        cleaned = clean_text(full_text)
        lines = [l for l in cleaned.split('\n') if l.strip()]
        group_size = 10
        for i in range(0, len(lines), group_size):
            group = "\n".join(lines[i:i + group_size])
            if len(group.split()) < 4:
                continue
            text_chunks.append(TextChunk(
                file_id=file_id,
                project_id=project_id,
                chunk_index=i // group_size,
                content=group,
                page_number=0,
                chunk_type="row_group",
                word_count=len(group.split()),
            ))

    except Exception as e:
        print(f"Spreadsheet extraction error [{file_path}]: {e}")

    return text_chunks, []


# ─────────────────────────────────────────────
#  PPTX EXTRACTOR
# ─────────────────────────────────────────────
def extract_from_pptx(file_id, project_id, file_path):
    text_chunks = []
    image_paths = []

    try:
        from pptx import Presentation
    except ImportError:
        print("python-pptx not installed.")
        return text_chunks, image_paths

    try:
        prs = Presentation(file_path)
        images_dir = get_images_dir(project_id)

        for slide_num, slide in enumerate(prs.slides, start=1):
            slide_text = []

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        line = " ".join(run.text for run in para.runs).strip()
                        if line:
                            slide_text.append(line)

                if shape.shape_type == 13:
                    try:
                        img_blob = shape.image.blob
                        ext = shape.image.ext
                        img_name = f"f{file_id}_s{slide_num}_sh{shape.shape_id}.{ext}"
                        img_path = images_dir / img_name
                        with open(img_path, "wb") as f:
                            f.write(img_blob)
                        image_paths.append(str(img_path))
                    except Exception as e:
                        print(f"  PPTX image error: {e}")

            if slide_text:
                combined = "\n".join(slide_text)
                cleaned = clean_text(combined)
                if len(cleaned.split()) >= 8:
                    text_chunks.append(TextChunk(
                        file_id=file_id,
                        project_id=project_id,
                        chunk_index=slide_num - 1,
                        content=cleaned,
                        page_number=slide_num,
                        chunk_type="slide",
                        word_count=len(cleaned.split()),
                    ))

    except Exception as e:
        print(f"PPTX extraction error [{file_path}]: {e}")

    return text_chunks, image_paths


# ─────────────────────────────────────────────
#  IMAGE FILE EXTRACTOR
# ─────────────────────────────────────────────
def extract_from_image(file_id, project_id, file_path):
    image_paths = []

    try:
        images_dir = get_images_dir(project_id)
        ext = file_path.rsplit(".", 1)[-1].lower()
        img_name = f"f{file_id}_standalone.{ext}"
        dest = images_dir / img_name

        if ext == "svg":
            return [], []

        shutil.copy2(file_path, dest)
        image_paths.append(str(dest))

    except Exception as e:
        print(f"Image copy error [{file_path}]: {e}")

    return [], image_paths


# ─────────────────────────────────────────────
#  MASTER EXTRACTOR
# ─────────────────────────────────────────────
def extract_file(file_id, project_id, file_path, file_type):
    ext = file_type.lower()

    if ext == "pdf":
        return extract_from_pdf(file_id, project_id, file_path)
    elif ext in ("docx", "doc"):
        return extract_from_docx(file_id, project_id, file_path)
    elif ext in ("txt", "rtf"):
        return extract_from_txt(file_id, project_id, file_path)
    elif ext in ("xlsx", "xls", "csv"):
        return extract_from_spreadsheet(file_id, project_id, file_path)
    elif ext in ("pptx", "ppt"):
        return extract_from_pptx(file_id, project_id, file_path)
    elif ext in ("jpg", "jpeg", "png", "bmp", "tiff", "tif", "webp", "gif"):
        return extract_from_image(file_id, project_id, file_path)
    else:
        print(f"Unsupported file type: {ext}")
        return [], []


# ─────────────────────────────────────────────
#  SAVE TO DATABASE
# ─────────────────────────────────────────────
def save_text_chunks(chunks):
    if not chunks:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    saved = 0
    for chunk in chunks:
        try:
            cursor.execute("""
                INSERT INTO text_chunks
                    (file_id, project_id, chunk_index,
                     content, page_number, chunk_type, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.file_id,
                chunk.project_id,
                chunk.chunk_index,
                chunk.content,
                chunk.page_number,
                chunk.chunk_type,
                chunk.word_count,
            ))
            saved += 1
        except Exception as e:
            print(f"  Chunk save error: {e}")
    conn.commit()
    conn.close()
    return saved


def save_extracted_images(file_id, project_id, image_paths):
    if not image_paths:
        return 0

    try:
        from PIL import Image
        import imagehash
    except ImportError:
        print("Pillow / imagehash not installed.")
        return 0

    conn = get_connection()
    cursor = conn.cursor()
    saved = 0

    for idx, img_path in enumerate(image_paths):
        try:
            img = Image.open(img_path).convert("RGB")
            ph = str(imagehash.phash(img))
            ah = str(imagehash.average_hash(img))
            dh = str(imagehash.dhash(img))
            w, h = img.size
            fsize = os.path.getsize(img_path)

            cursor.execute("""
                INSERT INTO extracted_images
                    (file_id, project_id, image_index,
                     stored_path, page_number,
                     width, height, phash, ahash, dhash, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, project_id, idx,
                img_path, 0,
                w, h, ph, ah, dh, fsize,
            ))
            saved += 1
        except Exception as e:
            print(f"  Image hash error [{img_path}]: {e}")

    conn.commit()
    conn.close()
    return saved


def update_file_status(file_id, status, text_count=0, image_count=0, error=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE files SET
            status = ?,
            text_extracted = ?,
            images_extracted = ?,
            error_message = ?,
            processed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, text_count, image_count, error, file_id))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  FULL EXTRACTION PIPELINE FOR ONE FILE
# ─────────────────────────────────────────────
def process_file_extraction(file_id, project_id, file_path, file_type):
    print(f"  Extracting: {Path(file_path).name}")

    try:
        text_chunks, image_paths = extract_file(
            file_id, project_id, file_path, file_type
        )
        text_saved = save_text_chunks(text_chunks)
        image_saved = save_extracted_images(file_id, project_id, image_paths)
        update_file_status(file_id, "done", text_saved, image_saved)
        print(f"    OK: {text_saved} chunks, {image_saved} images")
        return text_saved, image_saved

    except Exception as e:
        error_msg = str(e)
        print(f"    ERROR: {error_msg}")
        update_file_status(file_id, "error", error=error_msg)
        return 0, 0