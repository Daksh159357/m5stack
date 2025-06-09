import os
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Put your AssemblyAI API key here
ASSEMBLYAI_API_KEY = "fb2974857cdf45fb979feb8f33d26801"

HEADERS = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def upload_file_to_assemblyai(file_path):
    """Uploads file to AssemblyAI upload endpoint and returns upload URL"""
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": ASSEMBLYAI_API_KEY},
            data=f
        )
    response.raise_for_status()
    return response.json()["upload_url"]


def request_transcription(upload_url):
    """Requests transcription on AssemblyAI and returns transcript ID"""
    json_data = {
        "audio_url": upload_url
    }
    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        json=json_data,
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()["id"]


def get_transcription_result(transcript_id):
    """Polls AssemblyAI for transcription result until complete"""
    polling_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    while True:
        response = requests.get(polling_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        status = data["status"]
        if status == "completed":
            return data["text"]
        elif status == "error":
            raise RuntimeError(f"Transcription failed: {data['error']}")
        time.sleep(2)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.lower().endswith(".wav"):
        return jsonify({"error": "Only .wav files are accepted"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    try:
        # Upload .wav file to AssemblyAI
        upload_url = upload_file_to_assemblyai(save_path)
        # Request transcription
        transcript_id = request_transcription(upload_url)
        # Get transcription result (blocking, waits until done)
        transcript_text = get_transcription_result(transcript_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"transcript": transcript_text})


@app.route("/", methods=["GET"])
def home():
    return "M5Stack Voice to Text Server Running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
