"""
chunking.py — Document grouping, size calculation, single document oversize check,
greedy bin-packing, and email manifest text generation for HR Docs Checker v2.2.
"""

from dataclasses import dataclass, field
from typing import Optional

HARD_LIMIT_BYTES = 18 * 1024 * 1024  # 18 MB (18,874,368 bytes) raw binary size limit per email


@dataclass
class ProcessedFile:
    """
    Represents an uploaded and processed file ready for attachment.
    """
    doc_id: str
    file_label: str
    filename: str
    content: bytes
    size: int = field(init=False)
    doc_title: str = ""

    def __post_init__(self):
        self.size = len(self.content)


@dataclass
class EmailPart:
    """
    Represents a single discrete email package part containing attachments.
    """
    part_number: int
    total_parts: int
    files: list[ProcessedFile]
    total_bytes: int
    doc_ids: list[str]
    manifest_text: str


@dataclass
class ChunkResult:
    """
    Result of chunking/bin-packing operation.
    """
    ok: bool
    parts: list[EmailPart] = field(default_factory=list)
    oversized_doc_id: Optional[str] = None
    oversized_doc_title: Optional[str] = None
    error_message: Optional[str] = None


def group_by_document(files: list[ProcessedFile]) -> dict[str, list[ProcessedFile]]:
    """
    Groups ProcessedFile objects by doc_id while preserving original insertion order.
    """
    grouped: dict[str, list[ProcessedFile]] = {}
    for f in files:
        if f.doc_id not in grouped:
            grouped[f.doc_id] = []
        grouped[f.doc_id].append(f)
    return grouped


def calculate_group_size(group: list[ProcessedFile]) -> int:
    """
    Calculates total byte size of a document group.
    """
    return sum(f.size for f in group)


def _get_doc_title(group: list[ProcessedFile]) -> str:
    """
    Helper to extract human-readable title from a document group.
    """
    for f in group:
        if f.doc_title:
            return f.doc_title
    if group:
        return group[0].file_label
    return "Документ"


def _format_doc_item_summary(doc_id: str, group: list[ProcessedFile]) -> str:
    """
    Formats summary string for a document group in package-wide summary header.
    - 1 page/file: "ІПН"
    - 2+ pages/files: "Паспорт або ID-карта (2 стор.)"
    """
    title = _get_doc_title(group)
    count = len(group)
    if count > 1:
        return f"{title} ({count} стор.)"
    return title


def generate_manifest_text(
    part_number: int,
    total_parts: int,
    part_files: list[ProcessedFile],
    all_grouped_files: dict[str, list[ProcessedFile]],
) -> str:
    """
    Generates plain text manifest for insertion into email body.
    """
    part_grouped = group_by_document(part_files)

    lines: list[str] = []
    if total_parts > 1:
        lines.append(f"Вміст частини {part_number}/{total_parts}:")
    else:
        lines.append("Вміст поштового пакета:")

    for doc_id, grp in part_grouped.items():
        title = _get_doc_title(grp)
        cnt = len(grp)
        cnt_str = f"{cnt} файл(ів)" if cnt > 1 else "1 файл"
        lines.append(f" - {title} ({cnt_str})")

    all_doc_summaries = [
        _format_doc_item_summary(doc_id, grp)
        for doc_id, grp in all_grouped_files.items()
    ]

    lines.append("")
    lines.append(f"Усього документів у пакеті: {', '.join(all_doc_summaries)}")

    return "\n".join(lines)


def pack_into_email_parts(
    files: list[ProcessedFile],
    hard_limit_bytes: int = HARD_LIMIT_BYTES,
) -> ChunkResult:
    """
    Performs greedy bin-packing of ProcessedFile list into EmailPart containers.
    Document groups (by doc_id) are kept atomic and never split across parts.
    """
    if not files:
        return ChunkResult(ok=True, parts=[])

    grouped = group_by_document(files)

    # 1. Single document oversize check
    for doc_id, group in grouped.items():
        g_size = calculate_group_size(group)
        if g_size > hard_limit_bytes:
            doc_title = _get_doc_title(group)
            size_mb = g_size / (1024 * 1024)
            limit_mb = hard_limit_bytes / (1024 * 1024)
            msg = (
                f"Документ '{doc_title}' завеликий ({size_mb:.1f} MB) навіть після стиснення "
                f"(перевищує ліміт {limit_mb:.0f} MB). "
                f"Будь ласка, перескануйте або збережіть цей документ з меншим DPI (наприклад, 150 замість 300) "
                f"або у чорно-білому режимі."
            )
            return ChunkResult(
                ok=False,
                oversized_doc_id=doc_id,
                oversized_doc_title=doc_title,
                error_message=msg,
            )

    # 2. Bin packing by atomic document groups
    bins_files: list[list[ProcessedFile]] = []
    current_bin: list[ProcessedFile] = []
    current_size = 0

    for doc_id, group in grouped.items():
        g_size = calculate_group_size(group)
        if current_bin and (current_size + g_size > hard_limit_bytes):
            bins_files.append(current_bin)
            current_bin = list(group)
            current_size = g_size
        else:
            current_bin.extend(group)
            current_size += g_size

    if current_bin:
        bins_files.append(current_bin)

    total_parts = len(bins_files)
    parts: list[EmailPart] = []

    for idx, p_files in enumerate(bins_files, start=1):
        p_grouped = group_by_document(p_files)
        p_doc_ids = list(p_grouped.keys())
        p_bytes = sum(f.size for f in p_files)
        manifest = generate_manifest_text(
            part_number=idx,
            total_parts=total_parts,
            part_files=p_files,
            all_grouped_files=grouped,
        )
        part = EmailPart(
            part_number=idx,
            total_parts=total_parts,
            files=p_files,
            total_bytes=p_bytes,
            doc_ids=p_doc_ids,
            manifest_text=manifest,
        )
        parts.append(part)

    return ChunkResult(ok=True, parts=parts)
