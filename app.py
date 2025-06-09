from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

ASSEMBLYAI_API_KEY = 'fb2974857cdf45fb979feb8f33d26801'  # ✅ Replace if needed

@app.route('/', methods=['POST'])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    audio_file = request.files['file']
    if audio_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # Save uploaded file temporarily
    file_path = os.path.join("/tmp", audio_file.filename)
    audio_file.save(file_path)

    # Upload to AssemblyAI
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    with open(file_path, 'rb') as f:
        upload_response = requests.post(
            'https://api.assemblyai.com/v2/upload',
            headers=headers,
            files={'file': f}
        )

    if upload_response.status_code != 200:
        return jsonify({"error": "Upload failed", "details": upload_response.text}), 500

    audio_url = upload_response.json()['upload_url']

    # Transcribe request
    json_data = {
        "audio_url": audio_url
    }
    transcript_response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers={**headers, "content-type": "application/json"},
        json=json_data
    )

    if transcript_response.status_code != 200:
        return jsonify({"error": "Transcription request failed", "details": transcript_response.text}), 500

    transcript_id = transcript_response.json()["id"]

    # Poll until transcription is complete
    while True:
        polling_response = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers
        )
        result = polling_response.json()
        if result["status"] == "completed":
            return jsonify({"transcription": result["text"]})
        elif result["status"] == "error":
            return jsonify({"error": "Transcription failed", "details": result["error"]}), 500

# Optional: show homepage
@app.route('/', methods=['GET'])
def index():
    return "Send a POST request with a .wav file."

