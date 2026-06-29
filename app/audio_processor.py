import os
import math
import sqlite3
import subprocess
import json
from database import DB_FILE, save_chunk_transcript

WINGET_FFMPEG_BIN = r"C:\Users\muham\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"


def get_ffmpeg_cmd(binary_name):
    """Ensures subprocess can resolve the binary path inside isolated Streamlit loops."""
    if subprocess.run(["where", binary_name], capture_output=True).returncode == 0:
        return binary_name
    absolute_path = os.path.join(WINGET_FFMPEG_BIN, f"{binary_name}.exe")
    if os.path.exists(absolute_path):
        return absolute_path
    return binary_name


def get_audio_duration_and_convert(file_path, target_wav):
    ffmpeg_exe = get_ffmpeg_cmd("ffmpeg")
    ffprobe_exe = get_ffmpeg_cmd("ffprobe")

    cmd_convert = [
        ffmpeg_exe,
        "-y",
        "-i",
        file_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        target_wav,
    ]
    subprocess.run(
        cmd_convert, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    cmd_probe = [
        ffprobe_exe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        target_wav,
    ]
    result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
    metadata = json.loads(result.stdout)
    return float(metadata["format"]["duration"])


def chunk_audio_file(file_path, lecture_id, chunk_length_sec=120):
    os.makedirs(f"./chunks/{lecture_id}", exist_ok=True)
    target_wav = f"./chunks/{lecture_id}/normalized_full.wav"

    total_duration = get_audio_duration_and_convert(file_path, target_wav)
    num_chunks = math.ceil(total_duration / chunk_length_sec)

    ffmpeg_exe = get_ffmpeg_cmd("ffmpeg")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for i in range(num_chunks):
            cursor.execute(
                "SELECT status FROM chunk_cache WHERE lecture_id = ? AND chunk_index = ?",
                (lecture_id, i),
            )
            if cursor.fetchone():
                continue

            start_time = i * chunk_length_sec
            chunk_path = f"./chunks/{lecture_id}/chunk_{i}.wav"

            cmd_slice = [
                ffmpeg_exe,
                "-y",
                "-ss",
                str(start_time),
                "-t",
                str(chunk_length_sec),
                "-i",
                target_wav,
                "-c",
                "copy",
                chunk_path,
            ]
            subprocess.run(
                cmd_slice,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

            cursor.execute(
                """
                INSERT INTO chunk_cache (lecture_id, chunk_index, file_path, status, transcript)
                VALUES (?, ?, ?, ?, ?)
                """,
                (lecture_id, i, chunk_path, "pending", ""),
            )
        conn.commit()


def transcribe_lecture(lecture_id):
    """Fires a clean, isolated background Python subprocess to avoid Python 3.14 import jams."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chunk_index, file_path, status FROM chunk_cache WHERE lecture_id = ? ORDER BY chunk_index ASC",
            (lecture_id,),
        )
        chunks = cursor.fetchall()

    for idx, path, status in chunks:
        if status == "completed":
            continue

        with sqlite3.connect(DB_FILE) as conn:
            conn.cursor().execute(
                "UPDATE chunk_cache SET status = 'processing' WHERE lecture_id = ? AND chunk_index = ?",
                (lecture_id, idx),
            )
            conn.commit()

        # Run transcription inside an external script process context
        # This prevents Python 3.14 namespace crashing in Streamlit
        worker_script = f"""
from pywhispercpp.model import Model
model = Model('base.en', n_threads=4, print_progress=False)
segments = model.transcribe(r'{path}')
print('|||'.join([s.text for s in segments]))
"""
        try:
            result = subprocess.run(
                ["python", "-c", worker_script],
                capture_output=True,
                text=True,
                check=True,
            )
            chunk_text = result.stdout.replace("|||", " ").strip()
        except Exception:
            chunk_text = "[Transcription processing anomaly]"

        save_chunk_transcript(lecture_id, idx, chunk_text)
