# HR-опитувальник документів — Smart Solutions

Інтерактивний застосунок для формування персонального переліку документів при прийомі на роботу.

## Запуск локально

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Структура проєкту

```
ss-hr-docs-checker/
├── app.py              # Головний файл, кроки, навігація, рендер
├── documents.py        # build_documents(answers) → list[dict]
├── instructions.py     # Інструкції (ЕТК тощо)
├── exporters.py        # build_txt(), build_pdf()
├── styles.py           # CSS карток та бренд Smart Solutions
├── assets/
│   └── fonts/
│       ├── DejaVuSans.ttf          # Шрифт для PDF з кирилицею
│       └── DejaVuSans-Bold.ttf     # Жирний шрифт для PDF
├── requirements.txt
└── README.md
```

## Деплой на Streamlit Community Cloud

1. Завантажте шрифти DejaVuSans.ttf та DejaVuSans-Bold.ttf до `assets/fonts/`
2. Створіть публічний репозиторій на GitHub з назвою `ss-hr-docs-checker`
3. Підключіть репозиторій на https://share.streamlit.io, вкажіть `app.py`
4. Отримайте публічное посилання виду `https://ss-hr-docs-checker.streamlit.app`

> ⚠️ Шрифти DejaVu **обов'язково** мають бути у репозиторії — Streamlit Cloud не надає системних шрифтів з кирилицею.

## Отримання шрифтів DejaVu

```bash
# Linux / macOS
sudo apt-get install fonts-dejavu-core
# Файли: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
#         /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf

# Або завантажити з https://dejavu-fonts.github.io/
```

## Технології

- Python 3.10+
- Streamlit >= 1.35.0
- fpdf2 >= 2.7.9


