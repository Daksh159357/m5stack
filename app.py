from flask import Flask, render_template_string, request, jsonify
import requests
import os
import time

app = Flask(__name__)

ASSEMBLYAI_API_KEY = "fb2974857cdf45fb979feb8f33d26801"  # Replace with your key

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Voice to Text - Drag & Drop</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
        .drop-area {
            border: 3px dashed #aaa;
            border-radius: 10px;
            width: 80%;
            max-width: 600px;
            margin: auto;
            padding: 50px;
            cursor: pointer;
            color: #555;
        }
        .drop-area.hover { background-color: #f0f0f0; }
        #transcription { margin-top: 30px; font-size: 1.2em; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h2>🎙️ Drag & Drop your .wav file</h2>
    <div class="drop-area" id="drop-area">
        Drop your .wav file here or click to upload
        <input type="file" id="fileInput" accept=".wav" style="display:none" />
    </div>
    <div id="transcription"></div>

    <script>
        const dropArea = document.getElementById('drop-area');
        const fileInput = document.getElementById('fileInput');

        dropArea.addEventListener('click', () => fileInput.click());

        dropArea.addEventListener('dragover', e => {
            e.preventDefault();
            dropArea.classList.add('hover');
        });

        dropArea.addEventListener('dragleave', () => {
            dropArea.classList.remove('hover');
        });

        dropArea.addEventListener('drop', e => {
            e.preventDefault();
            dropArea.classList.remove('hover');
            const file = e.dataTransfer.files[0];
            uploadFile(file);
        });

        fileInput.addEventListener('change', () => {
            const file = fileInput.files[0];
            uploadFile(file);
        });

        async function uploadFile(file) {
            if (!file || file.type !== 'audio/wav') {
                alert('Please upload a valid .wav file');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            document.getElementById('transcription').innerText = 'Uploading and transcribing...';

            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (data.transcription) {
                document.getElementById('transcription').innerText = '📝 Transcription:\n\n' + data.transcription;
            } else {
                document.getElementById('transcription').innerText = '❌ Error:\n' + (data.error || 'Unknown error');
            }
        }
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_PAGE)

@app.route('/', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    audio_file = request.files['file']
    if audio_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    # Save temporarily
    file_path = os.path.join("/tmp", audio_file.filename)
    audio_file.save(file_path)

    # Upload to AssemblyAI
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    with open(file_path, 'rb') as f:
        upload_res = requests.post('https://api.assemblyai.com/v2/upload', headers=headers, files={'file': f})
    if upload_res.status_code != 200:
        return jsonify({"error": "Upload failed", "details": upload_res.text}), 500
    audio_url = upload_res.json()['upload_url']

    # Request transcription
    transcript_res = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers={**headers, "content-type": "application/json"},
        json={"audio_url": audio_url}
    )
    if transcript_res.status_code != 200:
        return jsonify({"error": "Transcription failed", "details": transcript_res.text}), 500
    transcript_id = transcript_res.json()['id']

    # Polling
    while True:
        poll_res = requests.get(f"https://api.assemblyai.com/v2/transcript/{transcript_id}", headers=headers)
        result = poll_res.json()
        if result['status'] == 'completed':
            return jsonify({"transcription": result['text']})
        elif result['status'] == 'error':
            return jsonify({"error": "Transcription failed", "details": result['error']}), 500
        time.sleep(1)

