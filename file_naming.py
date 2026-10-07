"""
file_naming.py — Standardized attachment filename and email subject generation for HR Docs Checker v2.2
Attachment format: {Prizvyshche_Imya}_{file_label}[_p{N}].{ext}
Subject format: [{Short company}] - {ПІБ}[ (частина N з M)]
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


# Legal entity forms stripped from the company name in email subjects.
# Sorted longest-first so "Приватне акціонерне товариство" wins over "Акціонерне товариство".
LEGAL_FORMS: list[str] = sorted(
    [
        "Товариство з обмеженою відповідальністю",
        "Товариство з додатковою відповідальністю",
        "Приватне акціонерне товариство",
        "Публічне акціонерне товариство",
        "Акціонерне товариство",
        "Приватне підприємство",
        "Державне підприємство",
        "Комунальне підприємство",
        "Дочірнє підприємство",
        "Фізична особа-підприємець",
        "Общество с ограниченной ответственностью",
        "ТОВ", "ТДВ", "ПрАТ", "ПАТ", "АТ", "ПП", "ФОП", "ДП", "КП",
        "ООО", "LLC", "Ltd",
    ],
    key=len,
    reverse=True,
)

# Spaces and hyphens inside a legal form match flexibly ("особа-підприємець" / "особа - підприємець")
_LEGAL_FORMS_ALT = "|".join(
    r"[\s\-]+".join(re.escape(tok) for tok in re.split(r"[\s\-]+", form))
    for form in LEGAL_FORMS
)
_LEGAL_FORM_PREFIX_RE = re.compile(rf"^(?:{_LEGAL_FORMS_ALT})(?!\w)", re.IGNORECASE)
_LEGAL_FORM_SUFFIX_RE = re.compile(rf"(?<!\w)(?:{_LEGAL_FORMS_ALT})\.?$", re.IGNORECASE)

_QUOTES_RE = re.compile(r"[«»\"“”„]")
# Apostrophes used as quotes (at word edges); apostrophes inside words like "Слов'янська" are kept
_EDGE_APOSTROPHE_RE = re.compile(r"(?<!\w)['’ʼ`‘]|['’ʼ`‘](?!\w)")
# Characters forbidden in Windows filenames (mail clients derive saved-file names from the subject)
_FORBIDDEN_RE = re.compile(r"[\\/:*?<>|]")

COMPANY_SUBJECT_MAX_LEN = 50
_EDGE_PUNCT = " ,.-"


def short_company_name(company: str) -> str:
    """
    Shortens a client company name for the email subject:
    strips quotes, legal entity form (at start or end) and filename-unsafe characters,
    caps length at a word boundary.

    Examples:
    - 'Товариство з обмеженою відповідальністю «Флагман Трейдинг»' -> 'Флагман Трейдинг'
    - 'Флагман Трейдинг, ТОВ' -> 'Флагман Трейдинг'
    - 'ТОВ' -> ''
    - '' -> ''
    """
    if not company:
        return ""

    name = _QUOTES_RE.sub(" ", company)
    name = _EDGE_APOSTROPHE_RE.sub(" ", name)
    name = _FORBIDDEN_RE.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip(_EDGE_PUNCT)

    name = _LEGAL_FORM_PREFIX_RE.sub("", name).strip(_EDGE_PUNCT)
    name = _LEGAL_FORM_SUFFIX_RE.sub("", name).strip(_EDGE_PUNCT)

    if len(name) > COMPANY_SUBJECT_MAX_LEN:
        cut = name[:COMPANY_SUBJECT_MAX_LEN]
        if name[COMPANY_SUBJECT_MAX_LEN] != " " and " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        name = cut.strip(_EDGE_PUNCT)

    return name


def build_email_subject(
    pib: str,
    company: str = "",
    part_number: int = 1,
    total_parts: int = 1,
) -> str:
    """
    Builds a short HR email subject: '[{Short company}] - {ПІБ}[ (частина N з M)]'.
    Company is optional (subject is then just ПІБ); empty ПІБ falls back to 'Кандидат'.

    Examples:
    - ('Затишний Євгеній Михайлович', 'ТОВ «Флагман Трейдинг»')
        -> '[Флагман Трейдинг] - Затишний Євгеній Михайлович'
    - ('Затишний Євгеній Михайлович', '') -> 'Затишний Євгеній Михайлович'
    - (..., part_number=1, total_parts=2) -> '... (частина 1 з 2)'
    """
    pib_clean = re.sub(r"\s+", " ", pib or "").strip() or "Кандидат"
    company_short = short_company_name(company)
    subject = f"[{company_short}] - {pib_clean}" if company_short else pib_clean
    if total_parts > 1:
        subject += f" (частина {part_number} з {total_parts})"
    return subject
