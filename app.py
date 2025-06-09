import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
ASSEMBLY_API_KEY = "fb2974857cdf45fb979feb8f33d26801"  # Replace with your real key

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    audio = request.files.get("file")
    if not audio or not audio.filename.endswith('.wav'):
        return jsonify({"error": "Please upload a .wav file"}), 400

    path = os.path.join(UPLOAD_FOLDER, audio.filename)
    audio.save(path)

    transcript = send_to_assemblyai(path)
    return jsonify({"transcript": transcript})

def send_to_assemblyai(filepath):
    headers = {'authorization': ASSEMBLY_API_KEY}

    # Upload file to AssemblyAI
    with open(filepath, 'rb') as f:
        res = requests.post('https://api.assemblyai.com/v2/upload', headers=headers, files={'file': f})
        upload_url = res.json()['upload_url']

    # Start transcription
    json = {"audio_url": upload_url}
    res = requests.post("https://api.assemblyai.com/v2/transcript", json=json, headers=headers)
    transcript_id = res.json()['id']

    # Poll for result
    while True:
        polling = requests.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers).json()
        if polling['status'] == 'completed':
            return polling['text']
        elif polling['status'] == 'error':
            return f"Error: {polling['error']}"

if __name__ == '__main__':
    app.run()
