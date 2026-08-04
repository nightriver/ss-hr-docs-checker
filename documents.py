"""
documents.py — Document schema definitions and generator for HR Docs Checker v2.2.
"""

DEFAULT_ANSWERS = {
    "pib": "",
    "military_liable": "Так",
    "labor_book": "Є трудова книжка",
    "education": "Шкільний атестат",
    "student_day_form": "Ні",
    "children_u18": "Ні",
    "disability_status": "Ні",
    "extra_statuses": [],
}


def build_documents(answers: dict = None) -> list[dict]:
    """
    Generates list of document requirement specifications based on candidate survey answers.

    Every document dictionary strictly contains the 13 required schema keys:
    - doc_id (str): Unique technical key
    - title (str): Display title
    - file_label (str): Clean ASCII label for attachment filenames
    - details (str): Full document details/description
    - format (str): Human-readable format indicator
    - instruction_key (Optional[str]): Key for INSTRUCTIONS lookup
    - important (bool): True if standard/mandatory, False if conditional
    - hr_note (Optional[str]): Special HR/candidate guidance note
    - accept (list[str]): Allowed file extensions (e.g. ['pdf', 'jpg', 'jpeg', 'png'] or ['pdf'])
    - multiple (bool): True if candidate may upload multiple pages/files
    - min_files (int): Minimum required uploaded files (1 for uploadable, 0 for non-uploadable)
    - upload_enabled (bool): True if st.file_uploader should render, False for physical items
    - special_validation (Optional[str]): Validation identifier string or None
    """
    if answers is None:
        answers = {}

    docs = [
        {
            "doc_id": "pasport",
            "title": "Паспорт або ID-карта",
            "file_label": "Pasport",
            "details": "Копії всіх сторінок паспорта з записами або копія ID-картки + витяг про місце реєстрації.",
            "format": "Копія",
            "instruction_key": None,
            "important": True,
            "hr_note": None,
            "accept": ["jpg", "jpeg", "png", "pdf"],
            "multiple": True,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
        {
            "doc_id": "ipn",
            "title": "ІПН",
            "file_label": "IPN",
            "details": "Копія ІПН.",
            "format": "Копія",
            "instruction_key": None,
            "important": True,
            "hr_note": None,
            "accept": ["jpg", "jpeg", "png", "pdf"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
    ]

    labor = answers.get("labor_book")
    if labor == "Є трудова книжка":
        docs.append({
            "doc_id": "trudova",
            "title": "Витяг з ЕТК",
            "file_label": "Trudova",
            "details": "Надати витяг з електронної трудової книжки у форматі PDF. Якщо паперова трудова книжка є на руках — надати також її.",
            "format": "PDF (+ паперова за наявності)",
            "instruction_key": "etk",
            "important": True,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": True,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        })
    elif labor == "Це моє перше офіційне працевлаштування":
        docs.append({
            "doc_id": "pfu_dovidka",
            "title": "Довідка з ПФУ",
            "file_label": "Dovidka_PFU",
            "details": "Надати довідку про відсутність індивідуальних відомостей про особу за формою ПФУ. Замовити можна на вебпорталі ПФУ.",
            "format": "PDF / Копія",
            "instruction_key": None,
            "important": True,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        })

    education = answers.get("education", "")
    edu_map = {
        "Шкільний атестат": "Атестат про повну загальну середню освіту",
        "Диплом училища або коледжу (ПТУ, фахова передвища)": "Диплом училища або коледжу",
        "Диплом університету або інституту (вища освіта)": "Диплом університету або інституту",
    }
    edu_label = edu_map.get(education, education if education else "документ про освіту")
    docs.append({
        "doc_id": "education",
        "title": "Документ про освіту",
        "file_label": "Osvita",
        "details": f"Надати: {edu_label}. Без додатків.",
        "format": "Копія",
        "instruction_key": None,
        "important": True,
        "hr_note": None,
        "accept": ["pdf", "jpg", "jpeg", "png"],
        "multiple": True,
        "min_files": 1,
        "upload_enabled": True,
        "special_validation": None,
    })

    if answers.get("student_day_form") == "Так":
        docs.append({
            "doc_id": "student_certificate",
            "title": "Довідка з ВНЗ (про денну форму навчання)",
            "file_label": "Dovidka_VNZ",
            "details": "Актуальна довідка на поточний семестр.",
            "format": "PDF / Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": "Потрібно для коректного нарахування ЄСВ/пільг.",
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        })

    docs.append({
        "doc_id": "photo",
        "title": "Фото 3×4",
        "file_label": "Photo",
        "details": "2 екземпляри у паперовому вигляді (при оформленні) АБО електронне фото 3×4 у форматі JPG/PNG.",
        "format": "Оригінал (2 шт.) або Електронне фото",
        "instruction_key": None,
        "important": True,
        "hr_note": "Якщо ви завантажите цифрове фото сюди, надавати паперові оригінали 3×4 не потрібно.",
        "accept": ["jpg", "jpeg", "png"],
        "multiple": False,
        "min_files": 0,
        "upload_enabled": True,
        "special_validation": None,
    })

    if answers.get("military_liable") == "Так":
        docs.append({
            "doc_id": "reserve_plus",
            "title": "Витяг з Резерв+",
            "file_label": "Reserve_plus",
            "details": (
                "Електронний PDF-витяг з застосунку Резерв+ на поточну дату. "
                "З грудня 2025 року електронний ВОД у Резерв+ є основним та єдиним "
                "офіційним військово-обліковим документом (постанова КМУ № 559)."
            ),
            "format": "PDF",
            "instruction_key": None,
            "important": True,
            "hr_note": "Завантажити Резерв+: https://reserveplus.mod.gov.ua",
            "accept": ["pdf"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": "reserve_plus_pdf",
        })

    if answers.get("children_u18") == "Так":
        docs.append({
            "doc_id": "children_cert",
            "title": "Свідоцтво про народження дітей",
            "file_label": "Dity_Svidotstvo",
            "details": "Копії свідоцтв про народження дітей до 18 років.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": True,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        })

    disability = answers.get("disability_status")
    if disability == "Так, інвалідність встановлено до 2025 року":
        docs += [
            {
                "doc_id": "msek",
                "title": "Довідка МСЕК",
                "file_label": "Dovidka_MSEK",
                "details": "Документ, що підтверджує групу інвалідності.",
                "format": "Копія",
                "instruction_key": None,
                "important": False,
                "hr_note": None,
                "accept": ["pdf", "jpg", "jpeg", "png"],
                "multiple": False,
                "min_files": 1,
                "upload_enabled": True,
                "special_validation": None,
            },
            {
                "doc_id": "ipr",
                "title": "Індивідуальна програма реабілітації (ІПР)",
                "file_label": "IPR",
                "details": "Надати ІПР для врахування умов та облаштування робочого місця.",
                "format": "Копія",
                "instruction_key": None,
                "important": False,
                "hr_note": None,
                "accept": ["pdf", "jpg", "jpeg", "png"],
                "multiple": True,
                "min_files": 1,
                "upload_enabled": True,
                "special_validation": None,
            },
        ]
    elif disability == "Так, інвалідність встановлено з 2025 року":
        docs += [
            {
                "doc_id": "expert_decision",
                "title": "Витяг з рішення експертної команди",
                "file_label": "Vytyah_Ekspertna_Komanda",
                "details": "Витяг з рішення експертної команди з оцінювання повсякденного функціонування особи.",
                "format": "PDF / Копія",
                "instruction_key": None,
                "important": False,
                "hr_note": None,
                "accept": ["pdf", "jpg", "jpeg", "png"],
                "multiple": False,
                "min_files": 1,
                "upload_enabled": True,
                "special_validation": None,
            },
            {
                "doc_id": "disability_recommendations",
                "title": "Рекомендації",
                "file_label": "Rekomendatsii_Reabilitatsia",
                "details": "Рекомендації як частина індивідуальної програми реабілітації особи з інвалідністю.",
                "format": "PDF / Копія",
                "instruction_key": None,
                "important": False,
                "hr_note": None,
                "accept": ["pdf", "jpg", "jpeg", "png"],
                "multiple": False,
                "min_files": 1,
                "upload_enabled": True,
                "special_validation": None,
            },
        ]

    statuses = set(answers.get("extra_statuses", []))
    STATUS_DOCS = {
        "Пенсіонер": {
            "doc_id": "pensioner",
            "title": "Пенсійне посвідчення",
            "file_label": "Pensiyne_Posvidchennya",
            "details": "Копія пенсійного посвідчення.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
        "Постраждалий від ЧАЕС": {
            "doc_id": "chaes",
            "title": "Посвідчення постраждалого від ЧАЕС",
            "file_label": "Posvidchennya_ChAES",
            "details": "Копія відповідного посвідчення.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
        "ВПО (внутрішньо переміщена особа)": {
            "doc_id": "vpo",
            "title": "Довідка ВПО",
            "file_label": "Dovidka_VPO",
            "details": "Копія довідки про взяття на облік внутрішньо переміщеної особи.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": False,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
        "Змінювали прізвище": {
            "doc_id": "surname_change",
            "title": "Свідоцтво про шлюб або документ про зміну прізвища",
            "file_label": "Zmina_Prizvyshcha",
            "details": "Копія свідоцтва про шлюб або іншого документа, що підтверджує зміну прізвища.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": None,
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": True,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
        "Одинока мати або батько": {
            "doc_id": "single_parent",
            "title": "Документи для статусу одинокої матері / батька",
            "file_label": "Odynoka_Maty_Batko",
            "details": "Підготуйте підтвердні документи. HR уточнить точний перелік.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": "HR може додатково запросити витяг з РАЦСу або інші підтвердні документи.",
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": True,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
        "Маю дитину з інвалідністю": {
            "doc_id": "disabled_child",
            "title": "Документи щодо дитини з інвалідністю",
            "file_label": "Dytyna_z_Invalidnistyu",
            "details": "Підготуйте підтвердні документи для кадрового та податкового обліку. HR уточнить деталі.",
            "format": "Копія",
            "instruction_key": None,
            "important": False,
            "hr_note": "HR може окремо уточнити довідку МСЕК або аналогічний актуальний документ.",
            "accept": ["pdf", "jpg", "jpeg", "png"],
            "multiple": True,
            "min_files": 1,
            "upload_enabled": True,
            "special_validation": None,
        },
    }

    for status, doc in STATUS_DOCS.items():
        if status in statuses:
            docs.append(doc)

    return docs
