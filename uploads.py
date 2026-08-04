"""
uploads.py — Streamlit document upload card rendering and state management for HR Docs Checker v2.2.
"""

import streamlit as st
import validators
from validators import ValidationResult
from instructions import INSTRUCTIONS


def init_upload_session_state() -> None:
    """
    Initializes required session state structures for uploaded documents,
    toast error tracking, and sent email parts tracking.
    Must be called before rendering upload cards or accessing upload state.
    """
    if "uploaded_docs" not in st.session_state:
        st.session_state["uploaded_docs"] = {}
    if "toasted_errors" not in st.session_state:
        st.session_state["toasted_errors"] = set()
    if "sent_parts" not in st.session_state:
        st.session_state["sent_parts"] = set()


def render_upload_card(doc_spec: dict) -> None:
    """
    Renders an interactive Streamlit card for a document specification.

    Handles:
    - Non-uploadable documents (upload_enabled=False)
    - Card header, instructions expander, and HR warnings
    - File uploader widget with key sync
    - Immediate raw bytes conversion (f.getvalue())
    - Live stream validation via validators.py
    - Toast feedback for blocking errors
    - Card status summary (files count, total MB, warnings/errors)

    :param doc_spec: Document specification dictionary from build_documents()
    """
    doc_id = doc_spec["doc_id"]
    title = doc_spec["title"]
    details = doc_spec.get("details", "")
    fmt = doc_spec.get("format", "")
    important = doc_spec.get("important", True)
    min_files = doc_spec.get("min_files", 1)
    upload_enabled = doc_spec.get("upload_enabled", True)
    hr_note = doc_spec.get("hr_note")
    instruction_key = doc_spec.get("instruction_key")
    accept_exts = doc_spec.get("accept", ["jpg", "jpeg", "png", "pdf"])
    multiple = doc_spec.get("multiple", False)
    special_val = doc_spec.get("special_validation")

    init_upload_session_state()

    # 1. Non-uploadable document handling (e.g. Photo 3x4)
    if not upload_enabled:
        icon = "🟢" if important else "🔵"
        with st.container():
            st.markdown(f"""
                <div class="doc-physical-marker doc-header">
                    <div class="doc-title">{icon} {title} <span style="font-size: 12px; color: #4A5568; background: #EDF2F7; padding: 2px 8px; border-radius: 4px;">Фізичний оригінал</span></div>
                    <div class="doc-details">{details}</div>
                    <div class="doc-format">📄 Формат: {fmt}</div>
                </div>
            """, unsafe_allow_html=True)
            if hr_note:
                st.caption(f"ℹ️ {hr_note}")
            st.caption("📷 Оригінал надається особисто/поштою в кадровий відділ. Завантаження через форму не потрібне.")
        return

    # 2. Process uploaded files from Streamlit session state BEFORE rendering header badge
    uploader_key = f"uploader_{doc_id}"
    uploaded_raw = st.session_state.get(uploader_key)

    new_file_entries: list[dict] = []
    if uploaded_raw:
        raw_list = uploaded_raw if isinstance(uploaded_raw, list) else [uploaded_raw]

        for file_obj in raw_list:
            file_bytes = file_obj.getvalue()
            fname = file_obj.name
            fsize = len(file_bytes)

            if special_val == "reserve_plus_pdf":
                val_res = validators.validate_reserve_plus_pdf(file_bytes)
            else:
                val_res = validators.validate_mime_type(file_bytes, fname, accept_exts)

            if val_res.blocking and val_res.reason:
                err_sig = f"{doc_id}_{fname}_{val_res.reason}"
                if err_sig not in st.session_state["toasted_errors"]:
                    st.toast(f"🚫 {title}: {val_res.reason}", icon="🚫")
                    st.session_state["toasted_errors"].add(err_sig)

            new_file_entries.append({
                "bytes": file_bytes,
                "filename": fname,
                "size": fsize,
                "validation": val_res,
            })

    # Reset sent_parts if file state changed to prevent partial retry corruption
    old_entries = st.session_state["uploaded_docs"].get(doc_id, [])
    if len(old_entries) != len(new_file_entries) or any(
        o["filename"] != n["filename"] or o["size"] != n["size"]
        for o, n in zip(old_entries, new_file_entries)
    ):
        if "sent_parts" in st.session_state:
            st.session_state["sent_parts"].clear()

    st.session_state["uploaded_docs"][doc_id] = new_file_entries

    # Determine status icon for header badge synchronously
    has_blocking = any(f["validation"].blocking for f in new_file_entries)
    has_warning = any(f["validation"].ok and f["validation"].reason for f in new_file_entries)
    has_uploaded = len(new_file_entries) > 0

    if has_blocking:
        badge_icon = "🚫"
    elif has_warning:
        badge_icon = "⚠️"
    elif has_uploaded:
        badge_icon = "✅"
    else:
        badge_icon = "🟢" if important else "🔵"

    # Render card container wrapping all document elements
    with st.container():
        st.markdown(f"""
            <div class="doc-card-marker doc-header">
                <div class="doc-title">{badge_icon} {title}</div>
                <div class="doc-details">{details}</div>
                <div class="doc-format">📄 Формат: {fmt}</div>
            </div>
        """, unsafe_allow_html=True)

        if hr_note:
            st.caption(f"ℹ️ {hr_note}")

        if instruction_key and instruction_key in INSTRUCTIONS:
            with st.expander("📋 Як отримати цей документ", expanded=False):
                for i, step_text in enumerate(INSTRUCTIONS[instruction_key], start=1):
                    st.markdown(f"{i}. {step_text}")

        # 3. File Uploader Widget (inside card container)
        st.file_uploader(
            label=f"Оберіть файл ({', '.join(accept_exts).upper()})",
            type=accept_exts,
            accept_multiple_files=multiple,
            key=uploader_key,
            help="Максимальний розмір одного файлу: 15 MB",
        )

        # 4. Status Feedback Box on Card (inside card container)
        if new_file_entries:
            total_bytes = sum(f["size"] for f in new_file_entries)
            total_mb = total_bytes / (1024 * 1024)
            file_count = len(new_file_entries)

            # Check for blocking errors
            blocking_errors = [f["validation"].reason for f in new_file_entries if f["validation"].blocking]
            warnings = [f["validation"].reason for f in new_file_entries if f["validation"].ok and f["validation"].reason]

            if blocking_errors:
                for err in blocking_errors:
                    st.error(f"❌ {err}")
            elif warnings:
                st.warning(f"⚠️ {warnings[0]}")
                st.info(f"📎 Завантажено: {file_count} файл(ів) ({total_mb:.2f} MB)")
            else:
                st.success(f"✅ Завантажено {file_count} файл(ів) ({total_mb:.2f} MB)")
        else:
            if min_files > 0:
                st.caption("⏳ Файл ще не завантажено (обов'язковий документ)")
            else:
                st.caption("ℹ️ Файл не завантажено (необов'язкове завантаження)")


def get_upload_summary(docs: list[dict]) -> dict:
    """
    Computes upload metrics across all document specs.

    Returns:
        dict with keys:
            uploaded_docs_count: int
            missing_mandatory_count: int
            blocking_errors_count: int
            total_size_bytes: int
            total_size_mb: float
            is_ready_for_submission: bool
    """
    init_upload_session_state()
    uploaded_docs = st.session_state["uploaded_docs"]

    missing_mandatory = 0
    blocking_errors = 0
    uploaded_count = 0
    total_bytes = 0

    for doc in docs:
        if not doc.get("upload_enabled", True):
            continue

        doc_id = doc["doc_id"]
        files = uploaded_docs.get(doc_id, [])

        if files:
            uploaded_count += 1
            for f in files:
                total_bytes += f["size"]
                if f["validation"].blocking:
                    blocking_errors += 1
        elif doc.get("important", True) and doc.get("min_files", 1) > 0:
            missing_mandatory += 1

    total_mb = total_bytes / (1024 * 1024)
    is_ready = (missing_mandatory == 0) and (blocking_errors == 0)

    return {
        "uploaded_docs_count": uploaded_count,
        "missing_mandatory_count": missing_mandatory,
        "blocking_errors_count": blocking_errors,
        "total_size_bytes": total_bytes,
        "total_size_mb": round(total_mb, 2),
        "is_ready_for_submission": is_ready,
    }


def validate_all_uploads(docs: list[dict]) -> tuple[bool, list[str]]:
    """
    Verifies that all mandatory document uploads are present and valid.

    :param docs: List of document spec dicts from build_documents(answers)
    :return: (is_valid: bool, error_messages: list[str])
    """
    init_upload_session_state()
    uploaded = st.session_state["uploaded_docs"]
    errors = []

    for doc in docs:
        if not doc.get("upload_enabled", True):
            continue

        doc_id = doc["doc_id"]
        title = doc["title"]
        important = doc.get("important", True)
        min_files = doc.get("min_files", 1)
        doc_files = uploaded.get(doc_id, [])

        if important and len(doc_files) < min_files:
            errors.append(f"Не завантажено обов'язковий документ: '{title}'")
            continue

        for f in doc_files:
            if f["validation"].blocking:
                errors.append(f"Документ '{title}' ({f['filename']}): {f['validation'].reason}")

    return len(errors) == 0, errors


def clear_upload_session_state() -> None:
    """
    Clears all uploaded file byte buffers and error tracking sets from session state.
    Executed immediately after successful HR email transmission.
    """
    st.session_state["uploaded_docs"] = {}
    st.session_state["toasted_errors"] = set()
    if "sent_parts" in st.session_state:
        del st.session_state["sent_parts"]
