"""
text_utils.py — Text transliteration and filename sanitization for HR Docs Checker v2.2
"""

import re

# Official Ukrainian Transliteration Table (KMU #55 aligned)
CYRILLIC_TRANSLIT = {
    'А': 'A', 'а': 'a',
    'Б': 'B', 'б': 'b',
    'В': 'V', 'в': 'v',
    'Г': 'H', 'г': 'h',
    'Ґ': 'G', 'ґ': 'g',
    'Д': 'D', 'д': 'd',
    'Е': 'E', 'е': 'e',
    'Є': 'Ye', 'є': 'ye',
    'Ж': 'Zh', 'ж': 'zh',
    'З': 'Z', 'з': 'z',
    'И': 'Y', 'и': 'y',
    'І': 'I', 'і': 'i',
    'Ї': 'Yi', 'ї': 'yi',
    'Й': 'Y', 'й': 'y',
    'К': 'K', 'к': 'k',
    'Л': 'L', 'л': 'l',
    'М': 'M', 'м': 'm',
    'Н': 'N', 'н': 'n',
    'О': 'O', 'о': 'o',
    'П': 'P', 'п': 'p',
    'Р': 'R', 'р': 'r',
    'С': 'S', 'с': 's',
    'Т': 'T', 'т': 't',
    'У': 'U', 'у': 'u',
    'Ф': 'F', 'ф': 'f',
    'Х': 'Kh', 'х': 'kh',
    'Ц': 'Ts', 'ц': 'ts',
    'Ч': 'Ch', 'ч': 'ch',
    'Ш': 'Sh', 'ш': 'sh',
    'Щ': 'Shch', 'щ': 'shch',
    'Ь': '', 'ь': '',
    'Ю': 'Yu', 'ю': 'yu',
    'Я': 'Ya', 'я': 'ya',
    # Russian compatibility fallbacks
    'Ъ': '', 'ъ': '',
    'Ы': 'Y', 'ы': 'y',
    'Э': 'E', 'э': 'e',
    'Ё': 'Yo', 'ё': 'yo',
    # Apostrophe removal
    "'": '', '’': '', 'ʼ': '', '`': '', '‘': '',
}


def transliterate(text: str) -> str:
    """Converts Cyrillic string to ASCII equivalent using official rules."""
    if not text:
        return ""
    return "".join(CYRILLIC_TRANSLIT.get(c, c) for c in text)


def sanitize_filename(text: str) -> str:
    """
    Cleans a string to be a safe ASCII filename component:
    - Transliterates Cyrillic
    - Replaces spaces/hyphens/special chars with single underscores
    - Keeps only safe ASCII alphanumeric characters and underscores
    - Collapses duplicate underscores and trims
    """
    if not text:
        return "Doc"

    transliterated = transliterate(text)
    # Replace whitespace and hyphens with single underscore
    res = re.sub(r'[\s\-]+', '_', transliterated)
    # Strip any characters that are not ASCII alphanumeric or underscore
    res = re.sub(r'[^a-zA-Z0-9_]', '', res)
    # Collapse multiple underscores
    res = re.sub(r'_+', '_', res)
    # Strip leading and trailing underscores
    res = res.strip('_')

    return res if res else "Doc"
