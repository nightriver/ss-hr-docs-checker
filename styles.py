CARD_CSS = """
<style>
/* Document card container styling targeting stVerticalBlock via direct child element container */
div[data-testid="stVerticalBlock"]:has(> .stElementContainer .doc-card-marker) {
    border: 1px solid #E2E8F0 !important;
    border-left: 6px solid #FFD100 !important;
    background-color: #FFFFFF !important;
    border-radius: 10px !important;
    padding: 20px 22px !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06) !important;
    margin-bottom: 20px !important;
}

/* Document card for physical non-uploadable originals */
div[data-testid="stVerticalBlock"]:has(> .stElementContainer .doc-physical-marker) {
    border: 1px solid #E2E8F0 !important;
    border-left: 6px solid #718096 !important;
    background-color: #F7FAFC !important;
    border-radius: 10px !important;
    padding: 20px 22px !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    margin-bottom: 20px !important;
}

/* EXPLICIT RESET for the main page root block container */
.stMainBlockContainer > div[data-testid="stVerticalBlock"],
.block-container > div[data-testid="stVerticalBlock"] {
    border: none !important;
    border-left: none !important;
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin-bottom: 0 !important;
}

.doc-title {
    color: #1A1A1A;
    font-weight: 700;
    font-size: 17px;
    margin-bottom: 6px;
}
.doc-details {
    color: #333333;
    font-size: 14px;
    margin-bottom: 4px;
}
.doc-format {
    color: #888888;
    font-size: 13px;
    margin-bottom: 12px;
}
div[data-testid="stProgress"] > div > div {
    background-color: #FFD100 !important;
}
div[data-testid="stButton"] button[kind="primary"] {
    background-color: #E8312A !important;
    border: none;
    color: white;
    font-weight: 600;
}
</style>
"""
