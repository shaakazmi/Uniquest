import os
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from database.db import get_connection, get_setting
from core.similarity import (
    build_text_clusters,
    build_image_clusters,
    get_similarity_stats,
)
from core.processor import get_project


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def get_export_path() -> Path:
    """Get default export folder from settings"""
    saved = get_setting(
        "export_path",
        str(Path.home() / "Documents"),
    )
    path = Path(saved)
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamp_str() -> str:
    """Return current timestamp for file names"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_filename(name: str) -> str:
    """Remove illegal characters from file name"""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


# ─────────────────────────────────────────────
#  RAW DATA LOADERS
# ─────────────────────────────────────────────
def load_text_pairs(project_id: int) -> List[Dict]:
    """Load all text similarity pairs with full details"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ts.id                   AS pair_id,
            ts.similarity_score,
            ts.reviewed,
            ts.created_at,
            fa.file_name            AS file_a,
            fa.file_type            AS type_a,
            fa.original_path        AS path_a,
            fb.file_name            AS file_b,
            fb.file_type            AS type_b,
            fb.original_path        AS path_b,
            ca.content              AS text_a,
            cb.content              AS text_b,
            ca.page_number          AS page_a,
            cb.page_number          AS page_b,
            ca.word_count           AS words_a,
            cb.word_count           AS words_b
        FROM text_similarities ts
        JOIN files       fa ON fa.id = ts.file_id_a
        JOIN files       fb ON fb.id = ts.file_id_b
        JOIN text_chunks ca ON ca.id = ts.chunk_id_a
        JOIN text_chunks cb ON cb.id = ts.chunk_id_b
        WHERE ts.project_id = ?
        ORDER BY ts.similarity_score DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_image_pairs(project_id: int) -> List[Dict]:
    """Load all image similarity pairs with full details"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ims.id                  AS pair_id,
            ims.similarity_score,
            ims.hash_distance,
            ims.reviewed,
            ims.created_at,
            fa.file_name            AS file_a,
            fa.file_type            AS type_a,
            fa.original_path        AS path_a,
            fb.file_name            AS file_b,
            fb.file_type            AS type_b,
            fb.original_path        AS path_b,
            ia.stored_path          AS img_path_a,
            ib.stored_path          AS img_path_b,
            ia.width                AS width_a,
            ia.height               AS height_a,
            ib.width                AS width_b,
            ib.height               AS height_b,
            ia.page_number          AS page_a,
            ib.page_number          AS page_b
        FROM image_similarities ims
        JOIN files          fa ON fa.id = ims.file_id_a
        JOIN files          fb ON fb.id = ims.file_id_b
        JOIN extracted_images ia ON ia.id = ims.image_id_a
        JOIN extracted_images ib ON ib.id = ims.image_id_b
        WHERE ims.project_id = ?
        ORDER BY ims.similarity_score DESC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_project_files(project_id: int) -> List[Dict]:
    """Load all files in a project"""
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            file_name,
            file_type,
            file_size,
            status,
            text_extracted,
            images_extracted,
            added_at,
            processed_at,
            original_path,
            storage_mode
        FROM files
        WHERE project_id = ?
        ORDER BY added_at ASC
    """, (project_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
#  CSV EXPORTER
# ─────────────────────────────────────────────
class CSVExporter:
    """Export results to CSV files"""

    def __init__(self, project_id: int, export_dir: str = None):
        self.project_id = project_id
        self.project    = get_project(project_id)
        self.export_dir = Path(export_dir) \
            if export_dir else get_export_path()
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_text_matches(self) -> str:
        """Export text similarity pairs to CSV"""
        pairs = load_text_pairs(self.project_id)
        if not pairs:
            return ""

        proj_name = safe_filename(
            self.project.get("name", f"project_{self.project_id}")
        )
        fname = (
            f"uniquest_{proj_name}_text_matches"
            f"_{timestamp_str()}.csv"
        )
        fpath = self.export_dir / fname

        fieldnames = [
            "pair_id",
            "similarity_score_%",
            "reviewed",
            "file_a",
            "type_a",
            "page_a",
            "words_a",
            "file_b",
            "type_b",
            "page_b",
            "words_b",
            "text_a_preview",
            "text_b_preview",
            "path_a",
            "path_b",
            "detected_at",
        ]

        with open(fpath, "w", newline="",
                  encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for pair in pairs:
                text_a = pair.get("text_a", "") or ""
                text_b = pair.get("text_b", "") or ""
                writer.writerow({
                    "pair_id":
                        pair.get("pair_id", ""),
                    "similarity_score_%":
                        f"{pair.get('similarity_score',0)*100:.1f}",
                    "reviewed":
                        "Yes" if pair.get("reviewed") else "No",
                    "file_a":
                        pair.get("file_a", ""),
                    "type_a":
                        pair.get("type_a", "").upper(),
                    "page_a":
                        pair.get("page_a", 0),
                    "words_a":
                        pair.get("words_a", 0),
                    "file_b":
                        pair.get("file_b", ""),
                    "type_b":
                        pair.get("type_b", "").upper(),
                    "page_b":
                        pair.get("page_b", 0),
                    "words_b":
                        pair.get("words_b", 0),
                    "text_a_preview":
                        text_a[:200].replace("\n", " "),
                    "text_b_preview":
                        text_b[:200].replace("\n", " "),
                    "path_a":
                        pair.get("path_a", ""),
                    "path_b":
                        pair.get("path_b", ""),
                    "detected_at":
                        pair.get("created_at", ""),
                })

        print(f"✅ Text CSV exported: {fpath}")
        return str(fpath)

    def export_image_matches(self) -> str:
        """Export image similarity pairs to CSV"""
        pairs = load_image_pairs(self.project_id)
        if not pairs:
            return ""

        proj_name = safe_filename(
            self.project.get("name", f"project_{self.project_id}")
        )
        fname = (
            f"uniquest_{proj_name}_image_matches"
            f"_{timestamp_str()}.csv"
        )
        fpath = self.export_dir / fname

        fieldnames = [
            "pair_id",
            "similarity_score_%",
            "hash_distance",
            "reviewed",
            "file_a",
            "type_a",
            "dimensions_a",
            "file_b",
            "type_b",
            "dimensions_b",
            "image_path_a",
            "image_path_b",
            "source_path_a",
            "source_path_b",
            "detected_at",
        ]

        with open(fpath, "w", newline="",
                  encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for pair in pairs:
                w_a = pair.get("width_a", 0)
                h_a = pair.get("height_a", 0)
                w_b = pair.get("width_b", 0)
                h_b = pair.get("height_b", 0)
                writer.writerow({
                    "pair_id":
                        pair.get("pair_id", ""),
                    "similarity_score_%":
                        f"{pair.get('similarity_score',0)*100:.1f}",
                    "hash_distance":
                        pair.get("hash_distance", 0),
                    "reviewed":
                        "Yes" if pair.get("reviewed") else "No",
                    "file_a":
                        pair.get("file_a", ""),
                    "type_a":
                        pair.get("type_a", "").upper(),
                    "dimensions_a":
                        f"{w_a}x{h_a}",
                    "file_b":
                        pair.get("file_b", ""),
                    "type_b":
                        pair.get("type_b", "").upper(),
                    "dimensions_b":
                        f"{w_b}x{h_b}",
                    "image_path_a":
                        pair.get("img_path_a", ""),
                    "image_path_b":
                        pair.get("img_path_b", ""),
                    "source_path_a":
                        pair.get("path_a", ""),
                    "source_path_b":
                        pair.get("path_b", ""),
                    "detected_at":
                        pair.get("created_at", ""),
                })

        print(f"✅ Image CSV exported: {fpath}")
        return str(fpath)

    def export_file_list(self) -> str:
        """Export project file list to CSV"""
        files = load_project_files(self.project_id)
        if not files:
            return ""

        proj_name = safe_filename(
            self.project.get("name", f"project_{self.project_id}")
        )
        fname = (
            f"uniquest_{proj_name}_files"
            f"_{timestamp_str()}.csv"
        )
        fpath = self.export_dir / fname

        fieldnames = [
            "file_name",
            "file_type",
            "file_size_kb",
            "status",
            "text_chunks",
            "images_extracted",
            "storage_mode",
            "added_at",
            "processed_at",
            "original_path",
        ]

        with open(fpath, "w", newline="",
                  encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for file in files:
                size_kb = round(
                    file.get("file_size", 0) / 1024, 1
                )
                writer.writerow({
                    "file_name":
                        file.get("file_name", ""),
                    "file_type":
                        file.get("file_type", "").upper(),
                    "file_size_kb":
                        size_kb,
                    "status":
                        file.get("status", ""),
                    "text_chunks":
                        file.get("text_extracted", 0),
                    "images_extracted":
                        file.get("images_extracted", 0),
                    "storage_mode":
                        file.get("storage_mode", ""),
                    "added_at":
                        file.get("added_at", ""),
                    "processed_at":
                        file.get("processed_at", ""),
                    "original_path":
                        file.get("original_path", ""),
                })

        print(f"✅ File list CSV exported: {fpath}")
        return str(fpath)

    def export_all(self) -> List[str]:
        """Export all CSVs and return list of file paths"""
        paths = []
        for fn in [
            self.export_text_matches,
            self.export_image_matches,
            self.export_file_list,
        ]:
            try:
                p = fn()
                if p:
                    paths.append(p)
            except Exception as e:
                print(f"CSV export error: {e}")
        return paths


# ─────────────────────────────────────────────
#  PDF EXPORTER
# ─────────────────────────────────────────────
class PDFExporter:
    """Export results to a PDF report"""

    def __init__(self, project_id: int, export_dir: str = None):
        self.project_id = project_id
        self.project    = get_project(project_id)
        self.export_dir = Path(export_dir) \
            if export_dir else get_export_path()
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export(self) -> str:
        """Generate full PDF report. Returns file path."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import (
                getSampleStyleSheet, ParagraphStyle
            )
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer,
                Table, TableStyle, HRFlowable,
                PageBreak,
            )
            from reportlab.lib.enums import TA_LEFT, TA_CENTER
        except ImportError:
            print("reportlab not installed.")
            return ""

        proj_name = safe_filename(
            self.project.get("name", f"project_{self.project_id}")
        )
        fname = (
            f"uniquest_{proj_name}_report"
            f"_{timestamp_str()}.pdf"
        )
        fpath = self.export_dir / fname

        # ── Page setup ──
        doc = SimpleDocTemplate(
            str(fpath),
            pagesize      = A4,
            rightMargin   = 2 * cm,
            leftMargin    = 2 * cm,
            topMargin     = 2 * cm,
            bottomMargin  = 2 * cm,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "UniTitle",
            parent    = styles["Heading1"],
            fontSize  = 22,
            textColor = colors.HexColor("#4A9EFF"),
            spaceAfter = 6,
        )
        h2_style = ParagraphStyle(
            "UniH2",
            parent    = styles["Heading2"],
            fontSize  = 14,
            textColor = colors.HexColor("#1a1a2e"),
            spaceAfter = 4,
        )
        h3_style = ParagraphStyle(
            "UniH3",
            parent    = styles["Heading3"],
            fontSize  = 12,
            textColor = colors.HexColor("#0f3460"),
            spaceAfter = 3,
        )
        body_style = ParagraphStyle(
            "UniBody",
            parent    = styles["Normal"],
            fontSize  = 10,
            leading   = 14,
            textColor = colors.HexColor("#333333"),
        )
        muted_style = ParagraphStyle(
            "UniMuted",
            parent    = styles["Normal"],
            fontSize  = 9,
            textColor = colors.HexColor("#666666"),
        )
        code_style = ParagraphStyle(
            "UniCode",
            parent      = styles["Normal"],
            fontSize    = 9,
            fontName    = "Courier",
            backColor   = colors.HexColor("#f5f5f5"),
            textColor   = colors.HexColor("#333333"),
            leading     = 13,
            leftIndent  = 8,
            rightIndent = 8,
        )

        elements = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # ── Cover ──
        elements.append(Spacer(1, 1.5 * cm))
        elements.append(
            Paragraph("Uniquest", title_style)
        )
        elements.append(
            Paragraph("Similarity Analysis Report", h2_style)
        )
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(
            HRFlowable(
                width="100%", thickness=1,
                color=colors.HexColor("#4A9EFF"),
            )
        )
        elements.append(Spacer(1, 0.4 * cm))

        # Project meta table
        proj = self.project or {}
        stats = get_similarity_stats(self.project_id)
        files = load_project_files(self.project_id)

        meta_data = [
            ["Project",    proj.get("name", "—")],
            ["Generated",  now],
            ["Status",     proj.get("status", "—").capitalize()],
            ["Files",      str(len(files))],
            ["Threshold",  f"{int(proj.get('similarity_threshold',0.70)*100)}%"],
            ["Text Matches",  str(stats.get("text_total", 0))],
            ["Image Matches", str(stats.get("img_total",  0))],
            ["Total Matches", str(stats.get("grand_total",0))],
        ]

        meta_table = Table(
            meta_data,
            colWidths=[4 * cm, 12 * cm],
        )
        meta_table.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 0), (-1, -1), 10),
            ("FONTNAME",    (0, 0), (0, -1),  "Helvetica-Bold"),
            ("TEXTCOLOR",   (0, 0), (0, -1),
             colors.HexColor("#0f3460")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#f8f9ff"),
              colors.white]),
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0,0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("GRID",        (0, 0), (-1, -1), 0.5,
             colors.HexColor("#dddddd")),
            ("ROUNDEDCORNERS", (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 0.6 * cm))

        # ── File List ──
        elements.append(PageBreak())
        elements.append(
            Paragraph("📄 Imported Files", h2_style)
        )
        elements.append(
            HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"),
            )
        )
        elements.append(Spacer(1, 0.3 * cm))

        if files:
            file_data = [[
                "File Name", "Type", "Size (KB)",
                "Status", "Chunks", "Images",
            ]]
            for f in files:
                size_kb = round(
                    f.get("file_size", 0) / 1024, 1
                )
                file_data.append([
                    f.get("file_name", "")[:40],
                    f.get("file_type", "").upper(),
                    str(size_kb),
                    f.get("status", "").capitalize(),
                    str(f.get("text_extracted", 0)),
                    str(f.get("images_extracted", 0)),
                ])

            file_table = Table(
                file_data,
                colWidths=[
                    6.5*cm, 1.5*cm, 2*cm,
                    2*cm, 2*cm, 2*cm,
                ],
                repeatRows=1,
            )
            file_table.setStyle(TableStyle([
                ("FONTNAME",  (0,0), (-1, 0),  "Helvetica-Bold"),
                ("FONTSIZE",  (0,0), (-1,-1),  9),
                ("BACKGROUND",(0,0), (-1, 0),
                 colors.HexColor("#4A9EFF")),
                ("TEXTCOLOR", (0,0), (-1, 0),  colors.white),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),
                 [colors.HexColor("#f8f9ff"), colors.white]),
                ("GRID",      (0,0), (-1,-1), 0.3,
                 colors.HexColor("#dddddd")),
                ("TOPPADDING",(0,0), (-1,-1), 5),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("LEFTPADDING",(0,0),(-1,-1), 6),
            ]))
            elements.append(file_table)
        else:
            elements.append(
                Paragraph("No files found.", muted_style)
            )

        # ── Text Matches ──
        elements.append(PageBreak())
        elements.append(
            Paragraph("📝 Text Similarity Matches", h2_style)
        )
        elements.append(
            HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"),
            )
        )
        elements.append(Spacer(1, 0.3 * cm))

        text_pairs = load_text_pairs(self.project_id)

        if text_pairs:
            for i, pair in enumerate(text_pairs[:50], 1):
                score = pair.get("similarity_score", 0) * 100
                score_color = (
                    "#FF4C4C" if score >= 90 else
                    "#FFA500" if score >= 80 else
                    "#FFD700" if score >= 70 else
                    "#4A9EFF"
                )

                elements.append(
                    Paragraph(
                        f"<font color='{score_color}'>"
                        f"Match #{i} — {score:.1f}% similar"
                        f"</font>",
                        h3_style,
                    )
                )

                pair_data = [
                    [
                        f"📄 {pair.get('file_a','')}"
                        f" (p.{pair.get('page_a',0)})",
                        f"📄 {pair.get('file_b','')}"
                        f" (p.{pair.get('page_b',0)})",
                    ],
                    [
                        (pair.get("text_a","") or "")[:300],
                        (pair.get("text_b","") or "")[:300],
                    ],
                ]

                pair_table = Table(
                    pair_data,
                    colWidths=[8*cm, 8*cm],
                )
                pair_table.setStyle(TableStyle([
                    ("FONTNAME",  (0,0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE",  (0,0), (-1,-1), 9),
                    ("TEXTCOLOR", (0,0), (-1, 0),
                     colors.HexColor("#0f3460")),
                    ("BACKGROUND",(0,1), (0,1),
                     colors.HexColor("#e8f0ff")),
                    ("BACKGROUND",(1,1), (1,1),
                     colors.HexColor("#e8ffe8")),
                    ("GRID",      (0,0), (-1,-1), 0.3,
                     colors.HexColor("#dddddd")),
                    ("TOPPADDING",(0,0), (-1,-1), 5),
                    ("BOTTOMPADDING",(0,0),(-1,-1),5),
                    ("LEFTPADDING",(0,0),(-1,-1), 6),
                    ("VALIGN",    (0,0), (-1,-1), "TOP"),
                    ("WORDWRAP",  (0,0), (-1,-1), "WORD"),
                ]))
                elements.append(pair_table)
                elements.append(Spacer(1, 0.4 * cm))

            if len(text_pairs) > 50:
                elements.append(
                    Paragraph(
                        f"... and {len(text_pairs)-50} more matches. "
                        "Export CSV for full list.",
                        muted_style,
                    )
                )
        else:
            elements.append(
                Paragraph(
                    "No text similarity matches found.",
                    muted_style,
                )
            )

        # ── Image Matches ──
        elements.append(PageBreak())
        elements.append(
            Paragraph("🖼️ Image Similarity Matches", h2_style)
        )
        elements.append(
            HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"),
            )
        )
        elements.append(Spacer(1, 0.3 * cm))

        img_pairs = load_image_pairs(self.project_id)

        if img_pairs:
            img_data = [[
                "#", "Score %", "Dist",
                "File A", "Dims A",
                "File B", "Dims B",
                "Reviewed",
            ]]
            for i, pair in enumerate(img_pairs[:100], 1):
                score = pair.get("similarity_score", 0) * 100
                w_a   = pair.get("width_a",  0)
                h_a   = pair.get("height_a", 0)
                w_b   = pair.get("width_b",  0)
                h_b   = pair.get("height_b", 0)
                img_data.append([
                    str(i),
                    f"{score:.1f}%",
                    str(pair.get("hash_distance", 0)),
                    pair.get("file_a", "")[:20],
                    f"{w_a}×{h_a}",
                    pair.get("file_b", "")[:20],
                    f"{w_b}×{h_b}",
                    "Yes" if pair.get("reviewed") else "No",
                ])

            img_table = Table(
                img_data,
                colWidths=[
                    0.8*cm, 1.5*cm, 1*cm,
                    4*cm, 1.8*cm,
                    4*cm, 1.8*cm,
                    1.8*cm,
                ],
                repeatRows=1,
            )
            img_table.setStyle(TableStyle([
                ("FONTNAME",  (0,0), (-1,0),  "Helvetica-Bold"),
                ("FONTSIZE",  (0,0), (-1,-1), 8),
                ("BACKGROUND",(0,0), (-1,0),
                 colors.HexColor("#4A9EFF")),
                ("TEXTCOLOR", (0,0), (-1,0),  colors.white),
                ("ROWBACKGROUNDS", (0,1), (-1,-1),
                 [colors.HexColor("#f8f9ff"), colors.white]),
                ("GRID",      (0,0), (-1,-1), 0.3,
                 colors.HexColor("#dddddd")),
                ("TOPPADDING",(0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1), 4),
                ("ALIGN",     (0,0), (-1,-1), "CENTER"),
                ("ALIGN",     (3,0), (3,-1),  "LEFT"),
                ("ALIGN",     (5,0), (5,-1),  "LEFT"),
            ]))
            elements.append(img_table)

            if len(img_pairs) > 100:
                elements.append(Spacer(1, 0.2*cm))
                elements.append(
                    Paragraph(
                        f"... and {len(img_pairs)-100} more. "
                        "Export CSV for full list.",
                        muted_style,
                    )
                )
        else:
            elements.append(
                Paragraph(
                    "No image similarity matches found.",
                    muted_style,
                )
            )

        # ── Footer note ──
        elements.append(Spacer(1, 1 * cm))
        elements.append(
            HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"),
            )
        )
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(
            Paragraph(
                f"Generated by Uniquest v1.0.0  •  {now}  •  "
                f"Local SQLite database",
                muted_style,
            )
        )

        # ── Build PDF ──
        try:
            doc.build(elements)
            print(f"✅ PDF exported: {fpath}")
            return str(fpath)
        except Exception as e:
            print(f"❌ PDF build error: {e}")
            return ""


# ─────────────────────────────────────────────
#  UNIFIED EXPORT DIALOG HELPER
# ─────────────────────────────────────────────
def export_project(
    project_id: int,
    mode: str = "both",
    export_dir: str = None,
) -> List[str]:
    """
    Export results for a project.
    mode: 'csv' | 'pdf' | 'both'
    Returns list of exported file paths.
    """
    exported = []

    if mode in ("csv", "both"):
        try:
            csv_exp = CSVExporter(project_id, export_dir)
            paths   = csv_exp.export_all()
            exported.extend(paths)
        except Exception as e:
            print(f"CSV export failed: {e}")

    if mode in ("pdf", "both"):
        try:
            pdf_exp = PDFExporter(project_id, export_dir)
            path    = pdf_exp.export()
            if path:
                exported.append(path)
        except Exception as e:
            print(f"PDF export failed: {e}")

    return exported


# ─────────────────────────────────────────────
#  EXPORT DIALOG  (PyQt6 widget)
# ─────────────────────────────────────────────
def show_export_dialog(
    project_id: int,
    parent=None,
):
    """
    Show export options dialog and run export.
    Call this from Results page export button.
    """
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QRadioButton,
        QButtonGroup, QFileDialog, QLineEdit,
        QMessageBox, QProgressDialog,
    )
    from PyQt6.QtCore import Qt
    from utils.theme import ThemeManager

    proj = get_project(project_id)
    if not proj:
        return

    dlg = QDialog(parent)
    dlg.setWindowTitle("Export Results")
    dlg.setFixedWidth(460)
    dlg.setModal(True)

    c = ThemeManager.colors()
    dlg.setStyleSheet(f"""
        QDialog {{
            background-color: {c['bg_primary']};
            color: {c['text_primary']};
        }}
        QLabel {{
            background: transparent;
            color: {c['text_primary']};
        }}
        QRadioButton {{
            background: transparent;
            color: {c['text_primary']};
            font-size: 13px;
        }}
    """)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(16)

    # Title
    title = QLabel(
        f"📤 Export — {proj.get('name','Project')}"
    )
    title.setStyleSheet(
        "font-size: 16px; font-weight: 700;"
        "background: transparent;"
    )
    layout.addWidget(title)

    # Format selection
    fmt_lbl = QLabel("Export Format:")
    fmt_lbl.setStyleSheet(
        "font-size: 12px; font-weight: 600;"
        "background: transparent;"
    )
    layout.addWidget(fmt_lbl)

    btn_group  = QButtonGroup(dlg)
    radio_both = QRadioButton("📊 Both CSV + PDF Report")
    radio_csv  = QRadioButton("📊 CSV only")
    radio_pdf  = QRadioButton("📄 PDF Report only")
    radio_both.setChecked(True)

    btn_group.addButton(radio_both, 0)
    btn_group.addButton(radio_csv,  1)
    btn_group.addButton(radio_pdf,  2)

    layout.addWidget(radio_both)
    layout.addWidget(radio_csv)
    layout.addWidget(radio_pdf)

    # Export path
    path_lbl = QLabel("Save to Folder:")
    path_lbl.setStyleSheet(
        "font-size: 12px; font-weight: 600;"
        "background: transparent;"
    )
    layout.addWidget(path_lbl)

    path_row   = QHBoxLayout()
    default_p  = get_setting(
        "export_path", str(Path.home() / "Documents")
    )
    path_input = QLineEdit(default_p)
    path_input.setFixedHeight(34)

    browse_btn = QPushButton("📂")
    browse_btn.setFixedSize(34, 34)
    browse_btn.setProperty("class", "ghost")

    def on_browse():
        folder = QFileDialog.getExistingDirectory(
            dlg, "Select Folder", path_input.text()
        )
        if folder:
            path_input.setText(folder)

    browse_btn.clicked.connect(on_browse)
    path_row.addWidget(path_input)
    path_row.addWidget(browse_btn)
    layout.addLayout(path_row)

    # Buttons
    btn_row    = QHBoxLayout()
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setProperty("class", "ghost")
    cancel_btn.setFixedHeight(36)
    cancel_btn.clicked.connect(dlg.reject)

    export_btn = QPushButton("📤 Export Now")
    export_btn.setFixedHeight(36)

    def on_export():
        mode_map = {0: "both", 1: "csv", 2: "pdf"}
        mode     = mode_map.get(
            btn_group.checkedId(), "both"
        )
        out_dir  = path_input.text().strip()

        export_btn.setEnabled(False)
        export_btn.setText("Exporting...")

        try:
            paths = export_project(
                project_id, mode, out_dir
            )
            dlg.accept()

            if paths:
                files_str = "\n".join(
                    f"  • {Path(p).name}" for p in paths
                )
                QMessageBox.information(
                    parent,
                    "✅ Export Complete",
                    f"Exported {len(paths)} file(s):\n\n"
                    f"{files_str}\n\n"
                    f"Saved to:\n{out_dir}",
                )
            else:
                QMessageBox.warning(
                    parent,
                    "Export Warning",
                    "No data was exported. "
                    "Run an analysis first.",
                )
        except Exception as e:
            export_btn.setEnabled(True)
            export_btn.setText("📤 Export Now")
            QMessageBox.critical(
                parent,
                "Export Error",
                f"Export failed:\n{e}",
            )

    export_btn.clicked.connect(on_export)

    btn_row.addStretch()
    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(export_btn)
    layout.addLayout(btn_row)

    dlg.exec()