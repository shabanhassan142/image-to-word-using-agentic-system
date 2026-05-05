"""
Image to Word Converter — Phase 2: Agentic System
Perceive → Decide → Act → Learn
"""

import streamlit as st
from PIL import Image
import uuid

from agent.perception import analyze_image
from agent.decision import select_strategy, get_strategy_config, STRATEGIES
from agent.action import preprocess, run_ocr
from agent.formatter import build_document
from agent.memory import update_preference, get_history_summary
from agent.logger import log_event

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Image to Word — Agentic",
    page_icon="🤖",
    layout="wide",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "ocr_result" not in st.session_state:
    st.session_state.ocr_result = None
if "perception" not in st.session_state:
    st.session_state.perception = None
if "strategy_name" not in st.session_state:
    st.session_state.strategy_name = None
if "strategy_reason" not in st.session_state:
    st.session_state.strategy_reason = None
if "doc_buffer" not in st.session_state:
    st.session_state.doc_buffer = None
if "feedback_given" not in st.session_state:
    st.session_state.feedback_given = False

SID = st.session_state.session_id

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🤖 Image to Word Converter — Agentic System")
st.caption(f"Phase 2 | Session `{SID}` | Perceive → Decide → Act → Learn")
st.markdown("---")

# ── Layout ────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 1])

# ════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Upload + Agent Perception & Decision
# ════════════════════════════════════════════════════════════════════════════
with left:
    st.subheader("📤 Upload Image")
    uploaded = st.file_uploader(
        "Choose a JPG or PNG file",
        type=["jpg", "jpeg", "png"],
        help="Upload a scanned document or handwritten notes",
    )

    if uploaded:
        image = Image.open(uploaded)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        st.caption(f"Size: {image.size[0]} × {image.size[1]} px")

        # ── STEP 1: PERCEIVE ──────────────────────────────────────────────
        st.markdown("---")
        st.subheader("👁️ Step 1 — Perception")

        with st.spinner("Analyzing image..."):
            perception = analyze_image(image)
            st.session_state.perception = perception

        log_event("perception", {"session_id": SID, "result": perception})

        q_color = {"high": "🟢", "medium": "🟡", "low": "🔴"}
        st.markdown(
            f"**Document Type:** `{perception['doc_type']}`  \n"
            f"**Quality:** {q_color.get(perception['quality'], '⚪')} `{perception['quality']}`"
        )

        m = perception["metrics"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sharpness", m["sharpness"])
        c2.metric("Brightness", m["brightness"])
        c3.metric("Contrast", m["contrast"])
        c4.metric("Noise", m["noise"])

        if perception["issues"]:
            for issue in perception["issues"]:
                st.warning(f"⚠️ {issue}")

        # ── STEP 2: DECIDE ────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🧠 Step 2 — Decision")

        strategy_name, reason = select_strategy(perception)
        st.session_state.strategy_name = strategy_name
        st.session_state.strategy_reason = reason

        log_event("decision", {"session_id": SID, "strategy": strategy_name, "reason": reason})

        st.info(f"**Selected Strategy:** `{strategy_name}`")
        st.caption(reason)

        # Allow user to override
        override = st.selectbox(
            "Override strategy (optional):",
            options=["— use agent decision —"] + list(STRATEGIES.keys()),
        )
        if override != "— use agent decision —":
            strategy_name = override
            st.session_state.strategy_name = strategy_name
            log_event("override", {"session_id": SID, "strategy": strategy_name})

        with st.expander("Strategy details"):
            cfg = get_strategy_config(strategy_name)
            st.json({k: v for k, v in cfg.items() if k != "description"})

# ════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Action + Output + Feedback
# ════════════════════════════════════════════════════════════════════════════
with right:
    st.subheader("⚙️ Step 3 — Action & Output")

    if uploaded:
        if st.button("🚀 Run Agent", type="primary", use_container_width=True):
            st.session_state.feedback_given = False
            strategy_name = st.session_state.strategy_name
            config = get_strategy_config(strategy_name)

            with st.spinner("Preprocessing image..."):
                processed = preprocess(image, config)

            with st.spinner("Running OCR..."):
                try:
                    result = run_ocr(processed, config)
                    st.session_state.ocr_result = result
                    log_event("ocr_complete", {
                        "session_id": SID,
                        "avg_confidence": result["avg_confidence"],
                        "low_conf_count": len(result["low_confidence_words"]),
                    })
                except RuntimeError as e:
                    if "TESSERACT_NOT_FOUND" in str(e):
                        st.error("❌ Tesseract OCR is not installed on your machine.")
                        st.markdown("""
**Fix — install Tesseract (one time only):**

1. Download the installer:  
   👉 https://github.com/UB-Mannheim/tesseract/wiki  
   *(click the latest Windows `.exe` link)*

2. Run the installer — keep the default install path:  
   `C:\\Program Files\\Tesseract-OCR\\tesseract.exe`

3. After installing, **restart this Streamlit app** and try again.
""")
                    else:
                        st.error(str(e))
                    st.stop()

            with st.spinner("Building document..."):
                buf = build_document(result["word_data"], result["plain_text"])
                st.session_state.doc_buffer = buf

        # ── Show results if available ──────────────────────────────────────
        if st.session_state.ocr_result:
            result = st.session_state.ocr_result
            avg_conf = result["avg_confidence"]
            low_conf = result["low_confidence_words"]

            # Confidence gate — human-in-the-loop
            if avg_conf < 60:
                st.error(
                    f"🔴 Low OCR confidence: **{avg_conf}%** — "
                    "Agent flagged this for human review before download."
                )
            elif avg_conf < 80:
                st.warning(f"🟡 Moderate confidence: **{avg_conf}%** — review recommended.")
            else:
                st.success(f"🟢 High confidence: **{avg_conf}%**")

            # Metrics
            ca, cb, cc = st.columns(3)
            ca.metric("Avg Confidence", f"{avg_conf}%")
            cb.metric("Words Extracted", len(result["word_data"]))
            cc.metric("Low-Conf Words", len(low_conf))

            # Low confidence word list
            if low_conf:
                with st.expander(f"⚠️ {len(low_conf)} uncertain words — click to review"):
                    for w in low_conf:
                        st.markdown(f"- `{w['text']}` — confidence: **{w['conf']}%**")

            # Text preview
            with st.expander("📖 Extracted Text Preview"):
                st.text_area("", result["plain_text"], height=200, label_visibility="collapsed")

            # Download
            if st.session_state.doc_buffer:
                fname = uploaded.name.rsplit(".", 1)[0]
                st.download_button(
                    label="📥 Download Word Document",
                    data=st.session_state.doc_buffer.getvalue(),
                    file_name=f"{fname}_agentic.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

            # ── STEP 4: LEARN — Feedback ──────────────────────────────────
            st.markdown("---")
            st.subheader("🔁 Step 4 — Feedback & Learning")
            st.caption("Your feedback trains the agent for future similar documents.")

            if not st.session_state.feedback_given:
                col_good, col_bad = st.columns(2)
                with col_good:
                    if st.button("✅ Output looks good", use_container_width=True):
                        update_preference(
                            st.session_state.perception["doc_type"],
                            st.session_state.strategy_name,
                            success=True,
                        )
                        log_event("feedback", {"session_id": SID, "success": True})
                        st.session_state.feedback_given = True
                        st.rerun()
                with col_bad:
                    if st.button("❌ Output needs improvement", use_container_width=True):
                        update_preference(
                            st.session_state.perception["doc_type"],
                            st.session_state.strategy_name,
                            success=False,
                        )
                        log_event("feedback", {"session_id": SID, "success": False})
                        st.session_state.feedback_given = True
                        st.rerun()
            else:
                st.success("Thanks! Agent memory updated.")

    else:
        st.info("Upload an image on the left to begin.")

# ── Transparency Panel ────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🔍 Agent Transparency Panel — Audit Log & Memory"):
    tab1, tab2 = st.tabs(["Recent Session Log", "Long-Term Memory"])

    with tab1:
        from agent.logger import get_session_log
        logs = get_session_log(SID)
        if logs:
            for entry in logs:
                st.json(entry)
        else:
            st.caption("No events logged this session yet.")

    with tab2:
        history = get_history_summary()
        if history:
            for h in history:
                st.json(h)
        else:
            st.caption("No long-term memory yet. Process some documents and give feedback.")
