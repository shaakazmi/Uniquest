from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


# ─────────────────────────────────────────────
#  PROJECT
# ─────────────────────────────────────────────
@dataclass
class Project:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    file_count: int = 0
    status: str = "idle"          # idle | scanning | done | error
    similarity_threshold: float = 0.70
    storage_mode: str = "reference"  # reference | copy

    @staticmethod
    def from_row(row) -> "Project":
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            file_count=row["file_count"] or 0,
            status=row["status"] or "idle",
            similarity_threshold=row["similarity_threshold"] or 0.70,
            storage_mode=row["storage_mode"] or "reference",
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "file_count": self.file_count,
            "status": self.status,
            "similarity_threshold": self.similarity_threshold,
            "storage_mode": self.storage_mode,
        }


# ─────────────────────────────────────────────
#  FILE
# ─────────────────────────────────────────────
@dataclass
class File:
    id: Optional[int] = None
    project_id: int = 0
    original_path: str = ""
    stored_path: Optional[str] = None
    file_name: str = ""
    file_type: str = ""
    file_size: int = 0
    storage_mode: str = "reference"
    status: str = "pending"       # pending | processing | done | error
    added_at: str = ""
    processed_at: Optional[str] = None
    text_extracted: int = 0
    images_extracted: int = 0
    error_message: Optional[str] = None

    @staticmethod
    def from_row(row) -> "File":
        return File(
            id=row["id"],
            project_id=row["project_id"],
            original_path=row["original_path"] or "",
            stored_path=row["stored_path"],
            file_name=row["file_name"] or "",
            file_type=row["file_type"] or "",
            file_size=row["file_size"] or 0,
            storage_mode=row["storage_mode"] or "reference",
            status=row["status"] or "pending",
            added_at=row["added_at"] or "",
            processed_at=row["processed_at"],
            text_extracted=row["text_extracted"] or 0,
            images_extracted=row["images_extracted"] or 0,
            error_message=row["error_message"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "original_path": self.original_path,
            "stored_path": self.stored_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "storage_mode": self.storage_mode,
            "status": self.status,
            "added_at": self.added_at,
            "processed_at": self.processed_at,
            "text_extracted": self.text_extracted,
            "images_extracted": self.images_extracted,
            "error_message": self.error_message,
        }

    def friendly_size(self) -> str:
        """Return human-readable file size"""
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def icon_name(self) -> str:
        """Return icon key based on file type"""
        ext = self.file_type.lower()
        if ext in ["pdf"]:
            return "pdf"
        elif ext in ["docx", "doc", "rtf", "txt"]:
            return "doc"
        elif ext in ["xlsx", "xls", "csv"]:
            return "sheet"
        elif ext in ["pptx", "ppt"]:
            return "slide"
        elif ext in ["jpg", "jpeg", "png", "bmp",
                     "tiff", "webp", "gif", "svg"]:
            return "image"
        return "file"


# ─────────────────────────────────────────────
#  TEXT CHUNK
# ─────────────────────────────────────────────
@dataclass
class TextChunk:
    id: Optional[int] = None
    file_id: int = 0
    project_id: int = 0
    chunk_index: int = 0
    content: str = ""
    page_number: int = 0
    chunk_type: str = "paragraph"
    word_count: int = 0
    created_at: str = ""

    @staticmethod
    def from_row(row) -> "TextChunk":
        return TextChunk(
            id=row["id"],
            file_id=row["file_id"],
            project_id=row["project_id"],
            chunk_index=row["chunk_index"] or 0,
            content=row["content"] or "",
            page_number=row["page_number"] or 0,
            chunk_type=row["chunk_type"] or "paragraph",
            word_count=row["word_count"] or 0,
            created_at=row["created_at"] or "",
        )

    def preview(self, max_chars: int = 120) -> str:
        """Short preview of chunk content"""
        text = self.content.strip()
        if len(text) > max_chars:
            return text[:max_chars] + "..."
        return text


# ─────────────────────────────────────────────
#  EXTRACTED IMAGE
# ─────────────────────────────────────────────
@dataclass
class ExtractedImage:
    id: Optional[int] = None
    file_id: int = 0
    project_id: int = 0
    image_index: int = 0
    stored_path: str = ""
    page_number: int = 0
    width: int = 0
    height: int = 0
    phash: Optional[str] = None
    ahash: Optional[str] = None
    dhash: Optional[str] = None
    file_size: int = 0
    created_at: str = ""

    @staticmethod
    def from_row(row) -> "ExtractedImage":
        return ExtractedImage(
            id=row["id"],
            file_id=row["file_id"],
            project_id=row["project_id"],
            image_index=row["image_index"] or 0,
            stored_path=row["stored_path"] or "",
            page_number=row["page_number"] or 0,
            width=row["width"] or 0,
            height=row["height"] or 0,
            phash=row["phash"],
            ahash=row["ahash"],
            dhash=row["dhash"],
            file_size=row["file_size"] or 0,
            created_at=row["created_at"] or "",
        )

    def dimensions(self) -> str:
        return f"{self.width}×{self.height}"


# ─────────────────────────────────────────────
#  TEXT SIMILARITY RESULT
# ─────────────────────────────────────────────
@dataclass
class TextSimilarity:
    id: Optional[int] = None
    project_id: int = 0
    chunk_id_a: int = 0
    chunk_id_b: int = 0
    file_id_a: int = 0
    file_id_b: int = 0
    similarity_score: float = 0.0
    reviewed: int = 0
    created_at: str = ""

    # Joined fields (not in DB, populated by queries)
    file_name_a: str = ""
    file_name_b: str = ""
    content_a: str = ""
    content_b: str = ""
    page_a: int = 0
    page_b: int = 0

    @staticmethod
    def from_row(row) -> "TextSimilarity":
        obj = TextSimilarity(
            id=row["id"],
            project_id=row["project_id"],
            chunk_id_a=row["chunk_id_a"],
            chunk_id_b=row["chunk_id_b"],
            file_id_a=row["file_id_a"],
            file_id_b=row["file_id_b"],
            similarity_score=row["similarity_score"] or 0.0,
            reviewed=row["reviewed"] or 0,
            created_at=row["created_at"] or "",
        )
        # Optional joined fields
        try:
            obj.file_name_a = row["file_name_a"] or ""
            obj.file_name_b = row["file_name_b"] or ""
            obj.content_a   = row["content_a"] or ""
            obj.content_b   = row["content_b"] or ""
            obj.page_a      = row["page_a"] or 0
            obj.page_b      = row["page_b"] or 0
        except (IndexError, KeyError):
            pass
        return obj

    def score_percent(self) -> str:
        return f"{self.similarity_score * 100:.1f}%"

    def score_color(self) -> str:
        """Color based on similarity score"""
        if self.similarity_score >= 0.90:
            return "#FF4C4C"   # red   - very high
        elif self.similarity_score >= 0.80:
            return "#FFA500"   # orange - high
        elif self.similarity_score >= 0.70:
            return "#FFD700"   # yellow - medium
        return "#4A9EFF"       # blue   - low


# ─────────────────────────────────────────────
#  IMAGE SIMILARITY RESULT
# ─────────────────────────────────────────────
@dataclass
class ImageSimilarity:
    id: Optional[int] = None
    project_id: int = 0
    image_id_a: int = 0
    image_id_b: int = 0
    file_id_a: int = 0
    file_id_b: int = 0
    similarity_score: float = 0.0
    hash_distance: int = 0
    reviewed: int = 0
    created_at: str = ""

    # Joined fields
    file_name_a: str = ""
    file_name_b: str = ""
    image_path_a: str = ""
    image_path_b: str = ""

    @staticmethod
    def from_row(row) -> "ImageSimilarity":
        obj = ImageSimilarity(
            id=row["id"],
            project_id=row["project_id"],
            image_id_a=row["image_id_a"],
            image_id_b=row["image_id_b"],
            file_id_a=row["file_id_a"],
            file_id_b=row["file_id_b"],
            similarity_score=row["similarity_score"] or 0.0,
            hash_distance=row["hash_distance"] or 0,
            reviewed=row["reviewed"] or 0,
            created_at=row["created_at"] or "",
        )
        try:
            obj.file_name_a  = row["file_name_a"] or ""
            obj.file_name_b  = row["file_name_b"] or ""
            obj.image_path_a = row["image_path_a"] or ""
            obj.image_path_b = row["image_path_b"] or ""
        except (IndexError, KeyError):
            pass
        return obj

    def score_percent(self) -> str:
        return f"{self.similarity_score * 100:.1f}%"

    def score_color(self) -> str:
        if self.similarity_score >= 0.90:
            return "#FF4C4C"
        elif self.similarity_score >= 0.80:
            return "#FFA500"
        elif self.similarity_score >= 0.70:
            return "#FFD700"
        return "#4A9EFF"


# ─────────────────────────────────────────────
#  TAG
# ─────────────────────────────────────────────
@dataclass
class Tag:
    id: Optional[int] = None
    project_id: int = 0
    name: str = ""
    color: str = "#4A9EFF"
    created_at: str = ""

    @staticmethod
    def from_row(row) -> "Tag":
        return Tag(
            id=row["id"],
            project_id=row["project_id"],
            name=row["name"] or "",
            color=row["color"] or "#4A9EFF",
            created_at=row["created_at"] or "",
        )


# ─────────────────────────────────────────────
#  ANALYSIS RUN
# ─────────────────────────────────────────────
@dataclass
class AnalysisRun:
    id: Optional[int] = None
    project_id: int = 0
    started_at: str = ""
    completed_at: Optional[str] = None
    status: str = "running"       # running | done | error | cancelled
    files_processed: int = 0
    text_similarities_found: int = 0
    image_similarities_found: int = 0
    error_message: Optional[str] = None

    @staticmethod
    def from_row(row) -> "AnalysisRun":
        return AnalysisRun(
            id=row["id"],
            project_id=row["project_id"],
            started_at=row["started_at"] or "",
            completed_at=row["completed_at"],
            status=row["status"] or "running",
            files_processed=row["files_processed"] or 0,
            text_similarities_found=row["text_similarities_found"] or 0,
            image_similarities_found=row["image_similarities_found"] or 0,
            error_message=row["error_message"],
        )

    def total_found(self) -> int:
        return self.text_similarities_found + self.image_similarities_found


# ─────────────────────────────────────────────
#  SUPPORTED FILE EXTENSIONS
# ─────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    # Documents
    "pdf":  "PDF Document",
    "docx": "Word Document",
    "doc":  "Word Document (Legacy)",
    "txt":  "Plain Text",
    "rtf":  "Rich Text Format",
    # Spreadsheets
    "xlsx": "Excel Spreadsheet",
    "xls":  "Excel Spreadsheet (Legacy)",
    "csv":  "CSV File",
    # Presentations
    "pptx": "PowerPoint Presentation",
    "ppt":  "PowerPoint (Legacy)",
    # Images
    "jpg":  "JPEG Image",
    "jpeg": "JPEG Image",
    "png":  "PNG Image",
    "bmp":  "Bitmap Image",
    "tiff": "TIFF Image",
    "tif":  "TIFF Image",
    "webp": "WebP Image",
    "gif":  "GIF Image",
    "svg":  "SVG Image",
}

IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "png", "bmp",
    "tiff", "tif", "webp", "gif", "svg",
}

DOCUMENT_EXTENSIONS = {
    "pdf", "docx", "doc", "txt", "rtf",
    "xlsx", "xls", "csv", "pptx", "ppt",
}


def is_supported(file_path: str) -> bool:
    ext = file_path.rsplit(".", 1)[-1].lower()
    return ext in SUPPORTED_EXTENSIONS


def get_file_type(file_path: str) -> str:
    return file_path.rsplit(".", 1)[-1].lower()