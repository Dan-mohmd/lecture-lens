# 📜 LectureLens Core System Constitution

### 1. Architectural Boundaries
* **Pure-Edge Operations:** The application must remain 100% operational in air-gapped conditions. Cloud API hooks (OpenAI, Anthropic) are strictly forbidden.
* **Process Isolation:** Heavy background machine learning pipelines (like audio transcription) must be executed in isolated subprocess workers (`python -c`) rather than directly inside the Streamlit user interface loop to prevent thread deadlock.
* **Pure Python Tooling:** Avoid external C++ library compilation on Python 3.14. Lean heavily on pre-built local binaries (`ffmpeg`) or pure-python modules (`pypdf`, `ollama`).

### 2. Data Governance
* **Atomic SQLite Persistence:** All intermediate states, chunks, and final artifacts must resolve inside `lecture_lens.db`. 
* **State Verification:** Before executing heavy computing pipelines, the engine must look up existing indices to ensure zero duplication of compute cycles.