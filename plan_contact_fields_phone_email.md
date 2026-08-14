# План реалізації v2: Поля Телефон та Email, валідація, передача менеджеру

Додавання обов'язкових полів «Номер телефону» та «Електронна пошта» на Кроці 1 опитувальника, базова валідація введених даних, включення контактів у тіло листа HR-менеджеру та встановлення `Reply-To` з email кандидата.

> Позначка ✳ — правки відносно первинної версії плану (за результатами рев'ю коду).

## 1. Загальний огляд змін

1. **Крок 1 опитувальника** (`app.py`)
   * Оновлення заголовка та опису кроку з фокусом на контактні дані.
   * Поле `input_phone` з плейсхолдером `+380501234567`.
   * Поле `input_email` з плейсхолдером `candidate@example.com`.
   * Збереження **нормалізованих** значень у `st.session_state.answers["phone"]` / `["email"]`.

2. ✳ **Валідація — у `app.py`, поруч із `validate_pib`** (не у `validators.py`)
   * `validators.py` — це модуль потокової валідації файлів (працює з `bytes`, `pypdf`, повертає `ValidationResult`). Валідація текстових полів форми туди не належить.
   * `validate_pib` вже живе в `app.py:29`, і тести імпортують його як `from app import validate_pib` (у `test_app_logic.py`, `test_challenger_m3_2_pipeline.py`, `test_empirical_ui.py`).

3. ✳ **Сигнатури валідаторів повертають нормалізоване значення**

   ```python
   def validate_phone(phone_text: str) -> tuple[bool, str, str]:  # (ok, error_msg, normalized)
   def validate_email(email_text: str) -> tuple[bool, str, str]:  # (ok, error_msg, normalized)
   ```

   Відхилення від форми `validate_pib` свідоме: інакше нормалізацію доведеться викликати окремою функцією, яку легко забути.

4. **Обробка переходу «Далі →»** (Крок 1 → Крок 2)
   * Одночасна валідація ПІБ, телефону та email.
   * Усі помилки виводяться через `st.error(err)`, перехід блокується.
   * Якщо все валідне — у сесію пишуться нормалізовані значення, `step = 2`.

5. **Фінальний екран (Step 8)**
   * `st.caption(f"Кандидат: **{pib_disp}** | Телефон: **{phone_disp}** | Email: **{email_disp}**")`

6. **Лист менеджеру**
   * Рядки `Телефон:` та `Email:` у блоці метаданих на початку тіла листа, перед маніфестом вкладень.
   * ✳ `Reply-To: <email кандидата>` у заголовках листа — менеджер відповідає кандидату прямо з поштового клієнта.

7. **Дефолти та тести**
   * `DEFAULT_ANSWERS` у `documents.py`: `"phone": ""`, `"email": ""`.
   * Юніт-тести валідаторів + оновлення перевірок структури відповідей.

## 2. Зміни по файлах

### [MODIFY] `app.py` — валідатори

✳ Додати поруч із `validate_pib`:

**`validate_phone(phone_text) -> (ok, err, normalized)`**

Нормалізація: видалити пробіли (включно з ` `), `-`, `(`, `)`, `.`. Далі — явні гілки замість загального правила «10–15 цифр» (воно пропускає сміття на кшталт `1234567890`):

| Ввід починається з | Умова | Нормалізований результат |
|---|---|---|
| `0` | рівно 10 цифр | `+38` + цифри → `+380501234567` |
| `380` / `+380` | рівно 12 цифр | `+380501234567` |
| `+` (інша країна) | 10–15 цифр | `+` + цифри |
| інше | — | помилка |

* Порожній ввід → `"Будь ласка, вкажіть контактний номер телефону."`
* Некоректний формат → `"Вкажіть коректний номер телефону, наприклад +380501234567 або 0501234567."`

Тест-кейси з початкового плану проходять усі: `+380501234567`, `0501234567`, `+38 (050) 123-45-67`, `+14155552671`.

**`validate_email(email_text) -> (ok, err, normalized)`**

* Нормалізація: `.strip().lower()`; внутрішні пробіли не вирізаємо (пробіл усередині = помилка).
* Регулярний вираз: `r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$"`, TLD ≥ 2 символи, довжина ≤ 254.
* Порожній → `"Будь ласка, вкажіть вашу електронну пошту."`
* Некоректний → `"Вкажіть коректну електронну пошту, наприклад candidate@example.com."`

### [MODIFY] `app.py` — UI Кроку 1

* Заголовок: `st.subheader("Введіть ваші контактні дані")`
* Підзаголовок: `st.caption("Вкажіть ваші ПІБ кирилицею (як у паспорті), контактний номер телефону та email. Вони необхідні для зв'язку HR-фахівця з вами.")`
* Три поля: `input_pib`, `input_phone`, `input_email` — кожне з `value=st.session_state.answers.get(...)`.

✳ Відомий нюанс Streamlit: при поверненні на Крок 1 поле покаже сирий ввід користувача, а не нормалізоване значення — ключ віджета переживає rerun і перебиває `value=`. Це та сама поведінка, що вже є в `input_pib`; не регресія, окремо не лікуємо.

### [MODIFY] `app.py` — навігація (`app.py:483`)

```python
if step == 1:
    ok_pib, err_pib = validate_pib(st.session_state.get("input_pib", ""))
    ok_phone, err_phone, phone_norm = validate_phone(st.session_state.get("input_phone", ""))
    ok_email, err_email, email_norm = validate_email(st.session_state.get("input_email", ""))
    errors = [e for ok, e in ((ok_pib, err_pib), (ok_phone, err_phone), (ok_email, err_email)) if not ok]
    if errors:
        for e in errors:
            st.error(e)
    else:
        st.session_state.answers["pib"] = st.session_state["input_pib"].strip()
        st.session_state.answers["phone"] = phone_norm
        st.session_state.answers["email"] = email_norm
        st.session_state.step += 1
        st.rerun()
```

### [MODIFY] `app.py` — тіло листа (`app.py:385`)

```python
body_lines = [
    f"Кандидат: {pib_str}",
    f"Телефон: {st.session_state.answers.get('phone', '-')}",
    f"Email: {st.session_state.answers.get('email', '-')}",
    f"Військовозобов'язаний: {st.session_state.answers.get('military_liable', '-')}",
    ...
]
```

✳ І передача `reply_to` у `build_email_message`:

```python
msg = emailer.build_email_message(
    from_addr=mailer.from_addr,
    to_addr=hr_to,
    subject=subject,
    body_text=body_text,
    attachments=attachments,
    reply_to=st.session_state.answers.get("email") or None,
)
```

### ✳ [MODIFY] `emailer.py`

* `build_email_message` (`emailer.py:164`): додати необов'язковий параметр `reply_to: Optional[str] = None`; якщо переданий і непорожній — `msg["Reply-To"] = reply_to`. Дефолт `None` зберігає зворотну сумісність з наявними тестами `test_emailer.py`.

### [MODIFY] `documents.py`

```python
DEFAULT_ANSWERS = {
    "pib": "",
    "phone": "",
    "email": "",
    "military_liable": "Так",
    "labor_book": "Є трудова книжка",
    "education": "Шкільний атестат",
    "student_day_form": "Ні",
    "children_u18": "Ні",
    "disability_status": "Ні",
    "extra_statuses": [],
}
```

### [MODIFY] `app.py` — фінальний екран (`app.py:259`)

Вивід ПІБ + телефон + email одним caption.

## 3. Тестування

✳ **[MODIFY] `tests/test_app_logic.py`** (не `test_validators.py` — валідатори тепер у `app.py`)

* `TestValidatePhone`: валідні (`+380501234567`, `0501234567`, `+38 (050) 123-45-67`, `+14155552671`) з перевіркою нормалізованого результату; невалідні (порожньо, літери, `123`, `+380`, `05012345678`, `1234567890` без `+`).
* `TestValidateEmail`: валідні (`user@example.com`, `Name.Surname@Smart-Solutions.UA` → нормалізація в нижній регістр, `test+label@domain.co`); невалідні (порожньо, без `@`, без TLD, пробіл усередині).
* Оновити `test_default_answers` — додати `phone` / `email`.

✳ **[MODIFY] `tests/test_emailer.py`**

* Тест: `build_email_message(..., reply_to="a@b.com")` виставляє заголовок `Reply-To`; без параметра — заголовок відсутній.

**[MODIFY] `tests/test_documents.py`**

* Додати `assertIn("phone", DEFAULT_ANSWERS)` / `assertIn("email", DEFAULT_ANSWERS)`.

✳ **Сумісність наявних тестів**: `DEFAULT_ANSWERS` також імпортують `test_challenger_m3_2_pipeline.py` та `test_empirical_ui.py`. Перевірено — точного набору ключів жоден тест не асертить (`assertIn` / доступ за ключем), тож додавання двох ключів їх не ламає.

## 4. План верифікації

**Автоматично** — ✳ повний набір, а не вибіркові файли:

```bash
python -m pytest
```

**Вручну** (Streamlit):

1. Крок 1 — три поля з плейсхолдерами.
2. «Далі →» з порожніми полями → три повідомлення про помилки, переходу немає.
3. Некоректний телефон (`123`, `abc`, `+380`) та email (`test@`, `@domain.com`, `user name@mail.com`) → перехід заблоковано.
4. Коректні дані → перехід; повернення «← Назад» зберігає введене.
5. Повне проходження до Кроку 8 → контакти в підсумковій картці.
6. Відправка в mock-режимі → у тілі листа є `Телефон:` / `Email:`, у заголовках — `Reply-To` з адресою кандидата.
