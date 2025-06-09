import os
import time
import requests
from flask import Flask, request, render_template_string

app = Flask(__name__)
ASSEMBLY_API_KEY = "fb2974857cdf45fb979feb8f33d26801"

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Voice to Text - Drag & Drop</title>
    <style>
        body { font-family: Arial; text-align: center; margin: 40px; }
        #drop-area {
            border: 3px dashed #999;
            border-radius: 20px;
            width: 80%;
            max-width: 600px;
            margin: auto;
            padding: 30px;
            font-size: 18px;
            color: #666;
        }
        #drop-area.hover { border-color: #666; }
        #output { margin-top: 30px; font-size: 18px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>🎤 Drag and Drop Your WAV File</h1>
    <div id="drop-area">Drop your <strong>.wav</strong> file here</div>
    <div id="output"></div>

    <script>
        const dropArea = document.getElementById("drop-area");
        const output = document.getElementById("output");

        ["dragenter", "dragover"].forEach(event => {
            dropArea.addEventListener(event, e => {
                e.preventDefault();
                e.stopPropagation();
                dropArea.classList.add("hover");
            }, false);
        });

        ["dragleave", "drop"].forEach(event => {
            dropArea.addEventListener(event, e => {
                e.preventDefault();
                e.stopPropagation();
                dropArea.classList.remove("hover");
            }, false);
        });

        dropArea.addEventListener("drop", async e => {
            const file = e.dataTransfer.files[0];
            if (!file.name.endsWith(".wav")) {
                output.innerText = "Please upload a .wav file.";
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            output.innerText = "⏳ Transcribing... Please wait.";

            const res = await fetch("/", {
                method: "POST",
                body: formData
            });

            const result = await res.text();
            output.innerText = result;
        });
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

@app.route("/", methods=["POST"])
def transcribe():
    if "file" not in request.files:
        return "No file uploaded", 400

    file = request.files["file"]
    file_path = os.path.join("/tmp", file.filename)
    file.save(file_path)

    headers = {"authorization": ASSEMBLY_API_KEY}

    # Upload to AssemblyAI
    with open(file_path, "rb") as f:
        upload_res = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            files={"file": f}
        )
    audio_url = upload_res.json().get("upload_url")

    # Start transcription
    transcript_res = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers={**headers, "content-type": "application/json"},
        json={"audio_url": audio_url}
    )

    transcript_id = transcript_res.json()["id"]
    polling_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"

    # Wait until transcription completes
    while True:
        status_res = requests.get(polling_url, headers=headers)
        status = status_res.json()
        if status["status"] == "completed":
            break
        elif status["status"] == "error":
            return f"Transcription failed: {status['error']}", 500
        time.sleep(2)

    text = status["text"]

    # Save transcription to file
    txt_path = os.path.join("/tmp", file.filename.rsplit(".", 1)[0] + ".txt")
    with open(txt_path, "w") as f:
        f.write(text)

    return text

if __name__ == "__main__":
    app.run(debug=True)
