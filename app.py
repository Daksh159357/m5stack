import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import assemblyai as aai
from dotenv import load_dotenv

import google.generativeai as genai
from gtts import gTTS # Import the gTTS library

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

app.secret_key = os.urandom(24)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio_output'), exist_ok=True) # Create folder for TTS output

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

# --- Gemini API Key (Hardcoded - REMEMBER SECURITY WARNING) ---
GEMINI_API_KEY = "AIzaSyCfQvgxJVrLkdPCB1vi2xZDAItugoSS60o" # Replace with your actual key if different
genai.configure(api_key=GEMINI_API_KEY)
# --- End of Gemini API Key ---

ALLOWED_EXTENSIONS = {'wav'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    transcribed_text = None
    gemini_response_text = None
    error_message = None
    transcribed_audio_file = None # To store path to TTS audio
    gemini_audio_file = None      # To store path to TTS audio

    if request.method == 'POST':
        if 'audio_file' in request.files:
            file = request.files['audio_file']

            if file.filename == '':
                flash('No audio file selected.')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                try:
                    file.save(filepath)

                    transcriber = aai.Transcriber()
                    flash(f'Uploading "{filename}" for transcription...')
                    upload_url = transcriber.upload_file(filepath)

                    config = aai.TranscriptionConfig(language_code="en_us")
                    transcript = transcriber.transcribe(upload_url, config=config)

                    if transcript.status == aai.TranscriptStatus.completed:
                        transcribed_text = transcript.text
                        txt_filename = os.path.splitext(filename)[0] + ".txt"
                        txt_filepath = os.path.join(app.config['UPLOAD_FOLDER'], txt_filename)
                        with open(txt_filepath, 'w') as f:
                            f.write(transcribed_text)
                        flash('File successfully uploaded and transcribed! Text saved locally.')

                        # --- Generate TTS for Transcribed Text ---
                        if transcribed_text:
                            audio_filename = "transcribed_audio_" + str(int(time.time())) + ".mp3"
                            audio_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'audio_output', audio_filename)
                            try:
                                tts = gTTS(text=transcribed_text, lang='en')
                                tts.save(audio_filepath)
                                transcribed_audio_file = audio_filename # Store only filename for URL
                                flash('Generated audio for transcribed text.')
                            except Exception as tts_e:
                                flash(f'Error generating audio for transcribed text: {tts_e}')
                        # --- End TTS for Transcribed Text ---

                    elif transcript.status == aai.TranscriptStatus.error:
                        error_message = f"Transcription failed: {transcript.error}"
                        flash(f"Error: {transcript.error}. Please try another file or contact support.")
                    else:
                        error_message = f"Transcription status: {transcript.status}. Please try again."
                        flash(f"Unexpected transcription status: {transcript.status}. Please try again.")

                except Exception as e:
                    error_message = f"An unexpected error occurred: {e}"
                    flash(f"An unexpected error occurred: {e}. Please check your API key and file.")
                finally:
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                flash('Invalid file type. Only .wav audio files are allowed.')

        elif 'transcribed_text_for_gemini' in request.form:
            text_to_process = request.form['transcribed_text_for_gemini']

            # If the user already transcribed, carry that text over for re-display
            # This is important if they click "Send to Gemini" without re-uploading
            if 'original_transcribed_text' in request.form:
                transcribed_text = request.form['original_transcribed_text']

            if text_to_process:
                try:
                    # Use a supported Gemini model, e.g., 'gemini-1.5-flash'
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    prompt_parts = [
                        f"Analyze the following transcribed audio text and provide a concise summary or key insights:\n\n{text_to_process}"
                    ]

                    flash('Sending text to Gemini API...')
                    response = model.generate_content(prompt_parts)

                    if response and response.text:
                        gemini_response_text = response.text
                        flash("Gemini API call successful!")

                        # --- Generate TTS for Gemini Response ---
                        audio_filename = "gemini_audio_" + str(int(time.time())) + ".mp3"
                        audio_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'audio_output', audio_filename)
                        try:
                            tts = gTTS(text=gemini_response_text, lang='en')
                            tts.save(audio_filepath)
                            gemini_audio_file = audio_filename # Store only filename for URL
                            flash('Generated audio for Gemini response.')
                        except Exception as tts_e:
                            flash(f'Error generating audio for Gemini response: {tts_e}')
                        # --- End TTS for Gemini Response ---

                    else:
                        error_message = "Gemini API returned an empty or invalid response."
                        flash("Gemini API returned an empty or invalid response.")

                except Exception as e:
                    error_message = f"Error communicating with Gemini API: {e}"
                    flash(f"Error with Gemini API: {e}. Check your API key and network.")
            else:
                flash("No transcribed text to send to Gemini.")

    # Pass all relevant variables to the template
    return render_template('index.html',
                           transcribed_text=transcribed_text,
                           gemini_response_text=gemini_response_text,
                           transcribed_audio_file=transcribed_audio_file,
                           gemini_audio_file=gemini_audio_file,
                           error_message=error_message)

# New route to serve the generated audio files
@app.route('/uploads/audio_output/<filename>')
def serve_audio(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'audio_output'), filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')