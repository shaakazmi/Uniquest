import csv
import os
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QButtonGroup,
    QRadioButton, QGroupBox, QMessageBox
)

from database.db import get_text_similarities, get_image_similarities, get_connection


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_csv(project_id: int, project_name: str, out_dir: str) -> list[str]:
    files_written = []
    ts = _timestamp()
    safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-").strip()

    text_sims  = get_text_similarities(project_id)
    image_sims = get_image_similarities(project_id)

    # text matches CSV
    if text_sims:
        path = os.path.join(out_dir, f"uniquest_{safe_name}_text_{ts}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Score", "File A", "File B",
                "Page A", "Page B", "Type A", "Type B",
                "Content A", "Content B", "Reviewed"
            ])
            for r in text_sims:
                writer.writerow([
                    r["id"], f"{r['similarity_score']:.2%}",
                    r["file_name_a"], r["file_name_b"],
                    r["page_a"], r["page_b"],
                    r["type_a"], r["type_b"],
                    r["content_a"][:500], r["content_b"][:500],
                    "Yes" if r["reviewed"] else "No"
                ])
        files_written.append(path)

    # image matches CSV
    if image_sims:
        path = os.path.join(out_dir, f"uniquest_{safe_name}_images_{ts}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Score", "Distance",
                "File A", "File B",
                "Path A", "Path B", "Reviewed"
            ])
            for r in image_sims:
                writer.writerow([
                    r["id"], f"{r['similarity_score']:.2%}",
                    r["hash_distance"],
                    r["file_name_a"], r["file_name_b"],
                    r["path_a"], r["path_b"],
                    "Yes" if r["reviewed"] else "No"
                ])
        files_written.append(path)

    return files_written


def export_pdf_report(project_id: int, project_name: str, out_dir: str) -> str:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable
        )
    except ImportError:
        return ""

    ts        = _timestamp()
    safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-").strip()
    path      = os.path.join(out_dir, f"uniquest_{safe_name}_report_{ts}.pdf")

    text_sims  = get_text_similarities(project_id)
    image_sims = get_image_similarities(project_id)

    doc    = SimpleDocTemplate(path, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # title
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"],
        fontSize=18, spaceAfter=6
    )
    story.append(Paragraph(f"Uniquest — Duplicate Analysis Report", title_style))
    story.append(Paragraph(f"Project: {project_name}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%"))
    story.append(Spacer(1, 0.5*cm))

    # summary
    story.append(Paragraph("Summary", styles["Heading2"]))
    summary_data = [
        ["Metric", "Count"],
        ["Text Similarity Pairs", str(len(text_sims))],
        ["Image Similarity Pairs", str(len(image_sims))],
    ]
    t = Table(summary_data, colWidths=[10*cm, 5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0078D4")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F0F0")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # text matches
    if text_sims:
        story.append(Paragraph("Text Similarity Matches", styles["Heading2"]))
        for r in text_sims[:50]:
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(
                f"Score: {r['similarity_score']:.2%} | "
                f"{r['file_name_a']} (p.{r['page_a']}) vs "
                f"{r['file_name_b']} (p.{r['page_b']})",
                styles["Normal"]
            ))
            a_text = str(r["content_a"])[:300]
            b_text = str(r["content_b"])[:300]
            story.append(Paragraph(f"A: {a_text}", styles["Normal"]))
            story.append(Paragraph(f"B: {b_text}", styles["Normal"]))
            story.append(HRFlowable(width="100%", thickness=0.5))

    doc.build(story)
    return path


def show_export_dialog(parent, project_id: int, project_name: str, default_dir: str = ""):
    dialog = QDialog(parent)
    dialog.setWindowTitle("Export Results")
    dialog.setFixedWidth(420)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(12)

    # format group
    fmt_group = QGroupBox("Export Format")
    fmt_layout = QVBoxLayout(fmt_group)
    rb_csv  = QRadioButton("CSV only")
    rb_pdf  = QRadioButton("PDF Report only")
    rb_both = QRadioButton("Both CSV and PDF")
    rb_csv.setChecked(True)
    fmt_layout.addWidget(rb_csv)
    fmt_layout.addWidget(rb_pdf)
    fmt_layout.addWidget(rb_both)
    layout.addWidget(fmt_group)

    # folder
    folder_group  = QGroupBox("Output Folder")
    folder_layout = QHBoxLayout(folder_group)
    folder_label  = QLabel(default_dir or str(Path.home() / "Documents"))
    folder_label.setWordWrap(True)
    folder_btn    = QPushButton("Browse...")
    folder_btn.setFixedWidth(90)
    folder_layout.addWidget(folder_label, 1)
    folder_layout.addWidget(folder_btn)
    layout.addWidget(folder_group)

    chosen_dir = [default_dir or str(Path.home() / "Documents")]

    def pick_folder():
        d = QFileDialog.getExistingDirectory(dialog, "Select Output Folder", chosen_dir[0])
        if d:
            chosen_dir[0] = d
            folder_label.setText(d)

    folder_btn.clicked.connect(pick_folder)

    # buttons
    btn_row    = QHBoxLayout()
    btn_export = QPushButton("Export")
    btn_cancel = QPushButton("Cancel")
    btn_export.setObjectName("primary_btn")
    btn_row.addStretch()
    btn_row.addWidget(btn_cancel)
    btn_row.addWidget(btn_export)
    layout.addLayout(btn_row)

    def do_export():
        out   = chosen_dir[0]
        files = []
        try:
            if rb_csv.isChecked() or rb_both.isChecked():
                files.extend(export_csv(project_id, project_name, out))
            if rb_pdf.isChecked() or rb_both.isChecked():
                p = export_pdf_report(project_id, project_name, out)
                if p:
                    files.append(p)

            if files:
                QMessageBox.information(
                    dialog, "Export Complete",
                    "Files saved:\n" + "\n".join(files)
                )
            else:
                QMessageBox.warning(dialog, "Export", "No data to export.")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(dialog, "Export Error", str(e))

    btn_export.clicked.connect(do_export)
    btn_cancel.clicked.connect(dialog.reject)

    dialog.exec()