from dataclasses import dataclass, field
from typing import Optional

SUPPORTED_TYPES = {
    "pdf":  "PDF Document",
    "docx": "Word Document",
    "xlsx": "Excel Spreadsheet",
    "csv":  "CSV File",
    "pptx": "PowerPoint",
    "txt":  "Text File",
    "rtf":  "Rich Text",
    "png":  "PNG Image",
    "jpg":  "JPEG Image",
    "jpeg": "JPEG Image",
    "bmp":  "BMP Image",
    "tiff": "TIFF Image",
    "gif":  "GIF Image",
    "webp": "WebP Image",
}


@dataclass
class Project:
    id:                   int = 0
    name:                 str = ""
    description:          str = ""
    created_at:           str = ""
    updated_at:           str = ""
    file_count:           int = 0
    status:               str = "active"
    similarity_threshold: float = 0.75
    storage_mode:         str = "reference"


@dataclass
class FileRecord:
    id:               int = 0
    project_id:       int = 0
    original_path:    str = ""
    stored_path:      str = ""
    file_name:        str = ""
    file_type:        str = ""
    file_size:        int = 0
    storage_mode:     str = "reference"
    status:           str = "pending"
    added_at:         str = ""
    processed_at:     str = ""
    text_extracted:   int = 0
    images_extracted: int = 0
    error_message:    str = ""


@dataclass
class TextChunkRecord:
    id:          int = 0
    file_id:     int = 0
    project_id:  int = 0
    chunk_index: int = 0
    content:     str = ""
    page_number: int = 1
    chunk_type:  str = "paragraph"
    word_count:  int = 0
    created_at:  str = ""


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024*1024):.1f} MB"
    else:
        return f"{size_bytes / (1024*1024*1024):.1f} GB"


def get_file_type_label(ext: str) -> str:
    return SUPPORTED_TYPES.get(ext.lower().lstrip("."), ext.upper())