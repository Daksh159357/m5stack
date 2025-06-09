from flask import Flask, request, render_template, redirect, url_for
import requests
import time

app = Flask(__name__)
ASSEMBLYAI_API_KEY = "fb2974857cdf45fb979feb8f33d26801"

upload_endpoint = "https://api.assemblyai.com/v2/upload"
transcribe_endpoint = "https://api.assemblyai.com/v2/transcript"

headers = {
    "authorization": ASSEMBLYAI_API_KEY,
    "content-type": "application/json"
}


def upload_audio(file_path):
    with open(file_path, "rb") as f:
        response = requests.post(upload_endpoint, headers={"authorization": ASSEMBLYAI_API_KEY}, data=f)
    return response.json()["upload_url"]


def transcribe_audio(audio_url):
    response = requests.post(transcribe_endpoint, json={"audio_url": audio_url}, headers=headers)
    transcript_id = response.json()['id']

    while True:
        poll_response = requests.get(f"{transcribe_endpoint}/{transcript_id}", headers=headers).json()
        if poll_response['status'] == 'completed':
            return poll_response['text']
        elif poll_response['status'] == 'error':
            return "Error transcribing audio"
        time.sleep(2)


@app.route('/', methods=['GET', 'POST'])
def index():
    transcript_text = None

    if request.method == 'POST':
        file = request.files['audio']
        if file and file.filename.endswith('.wav'):
            file_path = f"temp.wav"
            file.save(file_path)

            audio_url = upload_audio(file_path)
            transcript_text = transcribe_audio(audio_url)

    return render_template('index.html', transcript=transcript_text)
