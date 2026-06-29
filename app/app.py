import json
import os
import sqlite3
import sys
import uuid
import streamlit as st

# Force Python to find modules in the exact directory where this file lives
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import directly using standard absolute names (bypassing PEP 8 check for path forcing)
from audio_processor import chunk_audio_file, transcribe_lecture  # noqa: E402
from database import DB_FILE, get_lecture_progress, init_db  # noqa: E402
from document_processor import extract_text_from_pdf  # noqa: E402
from llm_interface import analyze_transcript  # noqa: E402

init_db()

st.set_page_config(
    page_title="LectureLens - Multi-Modal Offline Analyzer",
    page_icon="📚",
    layout="wide",
)
st.title("📚 LectureLens Multi-Modal Analyzer")

# Unified File Uploader supporting Audio & Textbook PDF
uploaded_file = st.file_uploader(
    "Upload Lecture Audio (.wav, .mp3) OR Textbook/Notes (.pdf, .txt)",
    type=["wav", "mp3", "pdf", "txt"],
)

if uploaded_file and "active_lecture" not in st.session_state:
    file_name = uploaded_file.name
    lecture_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_name))

    os.makedirs("./uploads", exist_ok=True)
    input_path = os.path.join("./uploads", file_name)
    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.info(f"Asset Registered! Unique ID: `{lecture_id}`")

    if st.button("🚀 Let's go..."):
        full_document_text = ""

        # --- PATH A: DOCUMENT TYPE DISPATCH ---
        if file_name.endswith((".pdf", ".txt")):
            with st.spinner("Extracting layout strings from messy document context..."):
                if file_name.endswith(".pdf"):
                    full_document_text = extract_text_from_pdf(input_path)
                else:  # Raw text file
                    with open(input_path, "r", encoding="utf-8") as txt_file:
                        full_document_text = txt_file.read()

            st.success("🎉 Document parsing complete!")

        # --- PATH B: AUDIO WORKFLOW TYPE DISPATCH ---
        elif file_name.endswith((".wav", ".mp3")):
            with st.spinner("Slicing audio into processing matrix chunks..."):
                chunk_audio_file(input_path, lecture_id)

            progress_bar = st.progress(0)
            status_text = st.empty()

            # Run the Whisper engine loop until completely parsed
            while True:
                # REMOVED THE NESTED 'from app.database import...' LINE HERE
                from database import (
                    get_lecture_progress,
                )  # If you want to keep it local, use the clean name

                current_pct = get_lecture_progress(lecture_id)
                progress_bar.progress(int(current_pct))
                status_text.text(
                    f"Whisper.cpp transcribing audio: {current_pct:.1f}% complete"
                )
                if current_pct >= 100.0:
                    break
                transcribe_lecture(lecture_id)

            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT transcript FROM chunk_cache WHERE lecture_id = ? ORDER BY chunk_index ASC",
                    (lecture_id,),
                )
                full_document_text = " ".join([r[0] for r in cursor.fetchall()])

        # --- UNIFIED STRATEGIC SLM CONVERSION LAYER ---
        if full_document_text.strip():
            with st.spinner("Local SLM generating structured JSON Study Graphs..."):
                try:
                    structured_json_str = analyze_transcript(full_document_text)

                    with sqlite3.connect(DB_FILE) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO lecture_results (lecture_id, lecture_name, full_transcript, structured_json)
                            VALUES (?, ?, ?, ?)
                        """,
                            (
                                lecture_id,
                                file_name,
                                full_document_text,
                                structured_json_str,
                            ),
                        )
                        conn.commit()

                    st.session_state["active_lecture"] = lecture_id
                    st.rerun()
                except Exception:
                    st.error(
                        "❌ **Inference Engine Offline!** Please verify `ollama run phi3:mini` is running."
                    )

# 💡 NEW SECTION: RENDER RESULTS WHEN STATE IS ACTIVE
if "active_lecture" in st.session_state:
    current_id = st.session_state["active_lecture"]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lecture_name, structured_json FROM lecture_results WHERE lecture_id = ?",
            (current_id,),
        )
        row = cursor.fetchone()

    if row:
        lecture_name, json_str = row
        st.write("---")
        st.subheader(f"📊 Analysis Results: {lecture_name}")

        try:
            data = json.loads(json_str)

            # Create interactive presentation layout tabs
            tab1, tab2, tab3 = st.tabs(
                ["💡 Core Concepts", "📖 Glossary Definitions", "🗂️ Quiz Flashcards"]
            )

            with tab1:
                for concept in data.get("concepts", []):
                    st.markdown(f"### 🔹 {concept.get('name')}")
                    st.write(concept.get("summary"))

            with tab2:
                for definition in data.get("definitions", []):
                    st.markdown(
                        f"**📚 {definition.get('term')}** : {definition.get('meaning')}"
                    )

            with tab3:
                for idx, card in enumerate(data.get("flashcards", [])):
                    with st.expander(f"❓ Flashcard {idx + 1}: {card.get('question')}"):
                        st.success(f"🎯 Answer: {card.get('answer')}")

        except Exception:
            st.error("Could not parse generated study graphs.")
            st.code(json_str)

    if st.button("🔄 Analyze Another File"):
        del st.session_state["active_lecture"]
        st.rerun()
