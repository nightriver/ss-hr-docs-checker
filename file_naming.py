"""
file_naming.py — Standardized attachment filename generation for HR Docs Checker v2.2
Format: {Prizvyshche_Imya}_{file_label}[_p{N}].{ext}
"""

import os
import re
from text_utils import sanitize_filename


def _capitalize_token(token: str) -> str:
    """
    Sanitizes a token and capitalizes each sub-part separated by '_' or '-'.
    E.g. 'Hulak-Artemovskyi' -> 'Hulak_Artemovskyi'
    """
    if not token:
        return ""
    clean = sanitize_filename(token)
    if not clean or clean == "Doc":
        return ""
    parts = [part.capitalize() for part in re.split(r'[_]+', clean) if part]
    return "_".join(parts)


def format_candidate_name(pib: str) -> str:
    """
    Extracts Surname and Firstname from candidate full name and formats as Prizvyshche_Imya.
    Transliterates, capitalizes, and joins with underscore. Handles compound/hyphenated names.

    Examples:
    - "Іваненко Петро Олексійович" -> "Ivanenko_Petro"
    - "петренко ганна" -> "Petrenko_Hanna"
    - "Гулак-Артемовський Петро" -> "Hulak_Artemovskyi_Petro"
    - "Шевченко" -> "Shevchenko"
    - "" -> "Kandydat"
    """
    if not pib or not pib.strip():
        return "Kandydat"

    tokens = pib.strip().split()
    if len(tokens) >= 2:
        surname = _capitalize_token(tokens[0])
        name = _capitalize_token(tokens[1])
        if surname and name:
            return f"{surname}_{name}"
        elif surname:
            return surname
        elif name:
            return name
        return "Kandydat"
    elif len(tokens) == 1:
        surname = _capitalize_token(tokens[0])
        return surname if surname else "Kandydat"

    return "Kandydat"


def generate_attachment_filename(
    pib: str,
    file_label: str,
    doc_index: int = 0,
    total_files_for_doc: int = 1,
    multiple: bool = False,
    original_filename: str = "",
    converted_ext: str = None,
) -> str:
    """
    Generates standardized attachment filename:
    {Prizvyshche_Imya}_{file_label}[_p{N}].{ext}

    Args:
        pib: Candidate full name string.
        file_label: Technical label of document (e.g. "Pasport", "IPN").
        doc_index: 0-based index of file within document group.
        total_files_for_doc: Total uploaded files for this document type.
        multiple: Schema 'multiple' boolean flag for document type.
        original_filename: Original name of uploaded file.
        converted_ext: Optional override extension (e.g. 'jpg' if re-encoded).

    Returns:
        Clean ASCII filename string.
    """
    candidate_name = format_candidate_name(pib)
    clean_label = sanitize_filename(file_label)

    # Page suffix logic: if total_files_for_doc > 1
    suffix = ""
    if total_files_for_doc > 1:
        suffix = f"_p{doc_index + 1}"

    # Extension logic
    if converted_ext:
        ext = converted_ext.strip().lstrip(".").lower()
    elif original_filename:
        ext = os.path.splitext(original_filename)[1].strip().lstrip(".").lower()
        if not ext:
            ext = "jpg"
    else:
        ext = "jpg"

    # Normalize jpeg -> jpg
    if ext == "jpeg":
        ext = "jpg"

    return f"{candidate_name}_{clean_label}{suffix}.{ext}"
