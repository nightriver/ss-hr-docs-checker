"""
app.py — 8-Step Interactive HR Questionnaire & Document Upload Wizard for HR Docs Checker v2.2.
"""

import base64
import os
import re
import streamlit as st

import chunking
from documents import build_documents, DEFAULT_ANSWERS
import emailer
from exporters import build_pdf, build_txt
import image_tools
import file_naming
from instructions import INSTRUCTIONS
from styles import CARD_CSS
import uploads

st.set_page_config(
    page_title="Сервіс подачі та перевірки документів HR | Smart Solutions",
    page_icon="📋",
    layout="centered",
)

TOTAL_STEPS = 7


def validate_pib(pib_text: str) -> tuple[bool, str]:
    """
    Validates candidate ПІБ input.
    Requires non-empty string, minimum 2 words (Surname + Name), Cyrillic characters.
    """
    if not pib_text:
        return False, "Будь ласка, вкажіть ваші ПІБ."
    pib = pib_text.strip()
    if not pib:
        return False, "Будь ласка, вкажіть ваші ПІБ."
    words = pib.split()
    if len(words) < 2:
        return False, "Будь ласка, вкажіть принаймні прізвище та ім'я (мінімум 2 слова)."
    if not re.search(r"[А-ЩЬЮЯҐЄІЇа-щьюяґєії]", pib):
        return False, "Будь ласка, вкажіть коректне ПІБ кирилицею (наприклад, Іваненко Петро)."
    pattern = r"^[А-ЩЬЮЯҐЄІЇа-щьюяґєії '\-’ʼ`]+$"
    if not re.match(pattern, pib):
        return False, "Будь ласка, вкажіть коректне ПІБ кирилицею (наприклад, Іваненко Петро)."
    return True, ""


def check_mandatory_uploads(docs: list[dict], uploaded_docs: dict) -> bool:
    """
    Helper to check if all mandatory documents have at least one uploaded file.
    """
    for d in docs:
        if not d.get("upload_enabled", True):
            continue
        if d.get("important", True) and d.get("min_files", 1) >= 1:
            doc_files = uploaded_docs.get(d["doc_id"], [])
            if not doc_files:
                return False
    return True


if "step" not in st.session_state:
    st.session_state.step = 1
if "answers" not in st.session_state:
    st.session_state.answers = DEFAULT_ANSWERS.copy()
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = {}
if "sent_parts" not in st.session_state:
    st.session_state.sent_parts = set()

st.markdown(CARD_CSS, unsafe_allow_html=True)


# ─── Callbacks ────────────────────────────────────────────────
def prev_step():
    if st.session_state.step > 1:
        st.session_state.step -= 1


def reset_app():
    st.session_state.clear()


# ─── Логотип ──────────────────────────────────────────────────
_logo_svg = os.path.join(os.path.dirname(__file__), "assets", "logo.svg")
_logo_png = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
try:
    if os.path.exists(_logo_svg):
        with open(_logo_svg, "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode("utf-8")
        _logo_html = f'<img src="data:image/svg+xml;base64,{_logo_b64}" style="height:48px;object-fit:contain;">'
    elif os.path.exists(_logo_png):
        with open(_logo_png, "rb") as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode("utf-8")
        _logo_html = f'<img src="data:image/png;base64,{_logo_b64}" style="height:48px;object-fit:contain;">'
    else:
        _logo_html = '<span style="font-weight:800;font-size:22px;color:#1A1A1A;">Smart<span style="color:#E8312A;">Solutions</span></span>'
except Exception:
    _logo_html = '<span style="font-weight:800;font-size:22px;color:#1A1A1A;">Smart<span style="color:#E8312A;">Solutions</span></span>'

st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:8px;">
    {_logo_html}
    <div style="font-size:15px;color:#555;margin-left:4px;">Сервіс подачі та перевірки документів HR</div>
</div>
<hr style="border:none;border-top:2px solid #FFD100;margin-bottom:20px;">
""", unsafe_allow_html=True)


# ─── Кроки опитувальника ──────────────────────────────────────
step = st.session_state.step

if step <= TOTAL_STEPS:
    st.progress(step / (TOTAL_STEPS + 1))
    st.caption(f"Крок {step} з {TOTAL_STEPS}")
    st.markdown("---")

# ── Крок 1 ──
if step == 1:
    st.subheader("Введіть ваше ПІБ (Прізвище, Ім'я, По батькові)")
    st.caption("Вкажіть ваші повні дані кирилицею так, як у паспорті. Вони будуть використані для генерації назв вкладень та повідомлення HR.")
    pib_val = st.text_input(
        "ПІБ кандидата:",
        value=st.session_state.answers.get("pib", ""),
        placeholder="Іваненко Петро Олексійович",
        key="input_pib",
    )

# ── Крок 2 ──
elif step == 2:
    st.subheader("Чи є ви військовозобов'язаною особою?")
    st.caption(
        "Чоловіки 18–60 років підлягають обов'язковому військовому обліку. "
        "Жінки — якщо мають медичну або фармацевтичну освіту, або добровільно проходять / проходили службу."
    )
    options2 = ["Так", "Ні"]
    cur_val = st.session_state.answers.get("military_liable", "Ні")
    val = st.radio(
        "Оберіть варіант:",
        options2,
        index=options2.index(cur_val) if cur_val in options2 else 0,
        key="r_military",
        label_visibility="collapsed",
    )
    st.session_state.answers["military_liable"] = val

# ── Крок 3 ──
elif step == 3:
    st.subheader("Яка у вас ситуація з трудовою книжкою?")
    options3 = ["Є трудова книжка", "Це моє перше офіційне працевлаштування"]
    cur_val = st.session_state.answers.get("labor_book", "Є трудова книжка")
    val = st.radio(
        "Оберіть варіант:",
        options3,
        index=options3.index(cur_val) if cur_val in options3 else 0,
        key="r_labor",
        label_visibility="collapsed",
    )
    st.session_state.answers["labor_book"] = val

# ── Крок 4 ──
elif step == 4:
    st.subheader("Освіта та форма навчання")
    options4_edu = [
        "Шкільний атестат",
        "Диплом училища або коледжу (ПТУ, фахова передвища)",
        "Диплом університету або інституту (вища освіта)",
    ]
    cur_edu = st.session_state.answers.get("education", "Шкільний атестат")
    val_edu = st.radio(
        "Який у вас документ про освіту?",
        options4_edu,
        index=options4_edu.index(cur_edu) if cur_edu in options4_edu else 0,
        key="r_edu",
    )
    st.session_state.answers["education"] = val_edu

    st.markdown("---")
    st.markdown("**Чи навчаєтесь ви зараз на денній формі у ВНЗ?**")
    st.caption("Питання є обов'язковим для всіх кандидатів незалежно від обраного рівня освіти.")
    options4_student = ["Так", "Ні"]
    cur_student = st.session_state.answers.get("student_day_form", "Ні")
    val_student = st.radio(
        "Форма навчання:",
        options4_student,
        index=options4_student.index(cur_student) if cur_student in options4_student else 1,
        key="r_student_day_form",
        label_visibility="collapsed",
    )
    st.session_state.answers["student_day_form"] = val_student

# ── Крок 5 ──
elif step == 5:
    st.subheader("Чи є у вас діти до 18 років?")
    options5 = ["Так", "Ні"]
    cur_val = st.session_state.answers.get("children_u18", "Ні")
    val = st.radio(
        "Оберіть варіант:",
        options5,
        index=options5.index(cur_val) if cur_val in options5 else 1,
        key="r_children",
        label_visibility="collapsed",
    )
    st.session_state.answers["children_u18"] = val

# ── Крок 6 ──
elif step == 6:
    st.subheader("Чи маєте ви інвалідність або відстрочку у зв'язку з інвалідністю?")
    st.info(
        "З 2025 року замість довідки МСЕК та індивідуальної програми реабілітації (ІПР) "
        "використовується Витяг з рішення експертної команди та Рекомендації."
    )
    options6 = [
        "Ні",
        "Так, інвалідність встановлено до 2025 року",
        "Так, інвалідність встановлено з 2025 року",
    ]
    cur_val = st.session_state.answers.get("disability_status", "Ні")
    val = st.radio(
        "Оберіть варіант:",
        options6,
        index=options6.index(cur_val) if cur_val in options6 else 0,
        key="r_disability",
        label_visibility="collapsed",
    )
    st.session_state.answers["disability_status"] = val

# ── Крок 7 ──
elif step == 7:
    st.subheader("Чи маєте ви додаткові статуси?")
    st.caption("Позначте все, що стосується вас. Якщо жодне не підходить — просто натисніть «Сформувати перелік».")

    OPTIONS_7 = [
        "Пенсіонер",
        "Постраждалий від ЧАЕС",
        "ВПО (внутрішньо переміщена особа)",
        "Змінювали прізвище",
        "Одинока мати або батько",
        "Маю дитину з інвалідністю",
    ]

    current = set(st.session_state.answers.get("extra_statuses", []))
    selected = []
    for opt in OPTIONS_7:
        checked = st.checkbox(opt, value=(opt in current), key=f"cb_{opt}")
        if checked:
            selected.append(opt)
    st.session_state.answers["extra_statuses"] = selected

# ── Фінальний екран (Step 8) ──
elif step > TOTAL_STEPS:
    if st.session_state.get("send_success"):
        if not st.session_state.get("balloons_fired"):
            st.balloons()
            st.session_state["balloons_fired"] = True
        st.success("🎉 Всі документи успішно відправлені HR!")
        st.info("Ваші документи прийняті в обробку. HR-фахівець зв'яжеться з вами за потреби.")
        st.button("🔄 Почати спочатку", on_click=reset_app, use_container_width=True)
        st.stop()

    smtp_sec = st.secrets.get("smtp", {})
    if smtp_sec.get("use_mock", False):
        st.warning("⚠️ Увага: Увімкнено MOCK-режим пошти. Листи не надсилаються в реальну скриньку HR.")

    st.success("✅ Ваш персональний перелік документів сформовано!")
    pib_disp = st.session_state.answers.get("pib", "Не вказано")
    st.caption(f"Кандидат: **{pib_disp}**")

    docs = build_documents(st.session_state.answers)

    mandatory_docs = [d for d in docs if d.get("important", True)]
    conditional_docs = [d for d in docs if not d.get("important", True)]

    if mandatory_docs:
        st.markdown("### 🟢 Обов'язкові документи (для всіх)")
        for doc in mandatory_docs:
            uploads.render_upload_card(doc)

    if conditional_docs:
        st.markdown("### 🔵 Додаткові документи (за вашою ситуацією)")
        for doc in conditional_docs:
            uploads.render_upload_card(doc)

    st.markdown("---")

    # Validation summary & submit check
    is_valid, upload_errors = uploads.validate_all_uploads(docs)

    if not is_valid:
        st.warning("⚠️ Для надсилання HR необхідно завантажити всі обов'язкові документи без помилок:")
        for err in upload_errors:
            st.caption(f"• {err}")

    confirmed = st.checkbox(
        "Підтверджую, що надані документи належать мені, а дані вказані вірно",
        key="chk_confirm",
    )

    submit_btn = st.button(
        "Надіслати документи HR",
        type="primary",
        disabled=not (confirmed and is_valid),
        use_container_width=True,
    )

    if submit_btn:
        with st.status("Надсилання документів...", expanded=True) as status:
            # Step A: File Validation & Reserve+ Check
            st.write("🔍 Перевірка цілісності документів та валідація Резерв+...")
            val_ok, val_errs = uploads.validate_all_uploads(docs)
            if not val_ok:
                status.update(label="Помилка валідації файлів", state="error")
                for e in val_errs:
                    st.error(e)
                st.stop()

            reserve_plus_warnings = []
            for doc in docs:
                doc_id = doc["doc_id"]
                files = st.session_state.uploaded_docs.get(doc_id, [])
                for fdict in files:
                    if doc.get("special_validation") == "reserve_plus_pdf":
                        res_val = fdict.get("validation")
                        if res_val and res_val.ok and res_val.reason:
                            reserve_plus_warnings.append(res_val.reason)

            # Step B & C: Compression & File Naming
            st.write("⚡ Оптимізація та стискання зображень...")
            processed_files: list[chunking.ProcessedFile] = []
            pib_str = st.session_state.answers.get("pib", "")

            for doc in docs:
                doc_id = doc["doc_id"]
                raw_files = st.session_state.uploaded_docs.get(doc_id, [])
                total_count = len(raw_files)

                for idx, fdict in enumerate(raw_files):
                    comp_bytes, comp_ext = image_tools.compress_image(
                        fdict["bytes"],
                        original_filename=fdict["filename"],
                    )

                    gen_filename = file_naming.generate_attachment_filename(
                        pib=pib_str,
                        file_label=doc.get("file_label", doc_id),
                        doc_index=idx,
                        total_files_for_doc=total_count,
                        multiple=doc.get("multiple", False),
                        original_filename=fdict["filename"],
                        converted_ext=comp_ext,
                    )

                    pf = chunking.ProcessedFile(
                        doc_id=doc_id,
                        file_label=doc.get("file_label", doc_id),
                        filename=gen_filename,
                        content=comp_bytes,
                        doc_title=doc.get("title", ""),
                    )
                    processed_files.append(pf)

            # Step D: Grouping & Chunking
            st.write("📦 Пакування документів у поштові повідомлення...")
            chunk_res = chunking.pack_into_email_parts(processed_files)

            if not chunk_res.ok:
                status.update(label="Помилка пакування", state="error")
                st.toast("🚫 Документ завеликий для відправки електронною поштою", icon="🚫")
                st.error(chunk_res.error_message)
                st.stop()

            # Step E: Email Delivery via DocsMailer
            st.write("✉️ Формування та відправка email через SMTP...")
            try:
                mailer, hr_to = emailer.create_mailer_from_secrets(st.secrets)
            except Exception as exc:
                status.update(label="Помилка конфігурації пошти", state="error")
                st.toast("Не вдалося налаштувати поштовий сервер.", icon="❌")
                st.error(f"Помилка конфігурації: {exc}")
                st.stop()

            # Build EmailMessages
            email_messages = []
            total_parts = len(chunk_res.parts)

            for part in chunk_res.parts:
                if total_parts > 1:
                    subject = f"[Частина {part.part_number}/{total_parts}] Документи для працевлаштування — {pib_str}"
                else:
                    subject = f"Документи для працевлаштування — {pib_str}"

                body_lines = [
                    f"Кандидат: {pib_str}",
                    f"Військовозобов'язаний: {st.session_state.answers.get('military_liable', '-')}",
                    f"Трудова книжка: {st.session_state.answers.get('labor_book', '-')}",
                    f"Освіта: {st.session_state.answers.get('education', '-')}",
                    f"Денна форма ВНЗ: {st.session_state.answers.get('student_day_form', 'Ні')}",
                    f"Діти до 18: {st.session_state.answers.get('children_u18', '-')}",
                    f"Інвалідність: {st.session_state.answers.get('disability_status', '-')}",
                    f"Додаткові статуси: {', '.join(st.session_state.answers.get('extra_statuses', [])) or 'Немає'}",
                    "",
                    part.manifest_text,
                ]

                if reserve_plus_warnings:
                    body_lines.append("")
                    body_lines.extend(reserve_plus_warnings)

                body_text = "\n".join(body_lines)

                attachments = [
                    {
                        "filename": pf.filename,
                        "content": pf.content,
                        "mime_type": None,
                    }
                    for pf in part.files
                ]

                msg = emailer.build_email_message(
                    from_addr=mailer.from_addr,
                    to_addr=hr_to,
                    subject=subject,
                    body_text=body_text,
                    attachments=attachments,
                )
                email_messages.append(msg)

            # Execute sending with retry tracking set
            send_results = mailer.send_parts(
                hr_to=hr_to,
                parts=email_messages,
                sent_parts=st.session_state["sent_parts"],
            )

            all_success = len(send_results) == total_parts and all(r.ok for r in send_results)

            if all_success:
                status.update(label="Готово", state="complete")
                st.toast("Документи успішно відправлені HR!", icon="🎉")
                uploads.clear_upload_session_state()
                st.session_state["send_success"] = True
                st.rerun()
            else:
                status.update(label="Помилка відправки", state="error")
                st.toast("Не вдалося відправити пошту. Спробуйте ще раз.", icon="❌")
                st.error("Під час відправки листів виникла помилка. Ви можете повторно натиснути «Надіслати документи HR» — уже надіслані частини не дублюватимуться.")

    # Fallback buttons
    st.markdown("---")
    st.markdown("**Завантажити перелік:**")

    col_pdf, col_txt = st.columns(2)
    with col_pdf:
        try:
            pdf_bytes = build_pdf(docs, instructions=INSTRUCTIONS)
            st.download_button(
                label="📥 Завантажити PDF перелік",
                data=pdf_bytes,
                file_name="perelik_dokumentiv.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.warning(f"PDF недоступний: {e}")

    with col_txt:
        txt_data = build_txt(docs, instructions=INSTRUCTIONS)
        st.download_button(
            label="📄 Завантажити TXT перелік",
            data=txt_data.encode("utf-8"),
            file_name="perelik_dokumentiv.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown("")
    st.button("🔄 Почати спочатку", on_click=reset_app, use_container_width=True)
    st.stop()


# ─── Навігація ────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    if st.session_state.step > 1:
        st.button("← Назад", on_click=prev_step, use_container_width=True)
with col2:
    if st.session_state.step < TOTAL_STEPS:
        if st.button("Далі →", type="primary", use_container_width=True):
            if step == 1:
                pib_input = st.session_state.get("input_pib", "")
                is_pib_valid, pib_err = validate_pib(pib_input)
                if not is_pib_valid:
                    st.error(pib_err)
                else:
                    st.session_state.answers["pib"] = pib_input.strip()
                    st.session_state.step += 1
                    st.rerun()
            else:
                st.session_state.step += 1
                st.rerun()
    elif st.session_state.step == TOTAL_STEPS:
        if st.button("✅ Сформувати перелік", type="primary", use_container_width=True):
            st.session_state.step += 1
            st.rerun()
