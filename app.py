import os
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import assemblyai as aai
from dotenv import load_dotenv # Used to load API key from .env file

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Configure upload folder and maximum file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit for uploads

# Set a secret key for session management (used for flash messages)
app.secret_key = os.urandom(24) 

# Ensure the upload folder exists when the app starts
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Set AssemblyAI API Key from environment variable
# It's crucial that this line executes AFTER load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'wav'}

def allowed_file(filename):
    """Checks if a filename has an allowed WAV extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles file uploads, transcription, and displays results.
    Renders the index.html template.
    """
    transcribed_text = None
    error_message = None

    if request.method == 'POST':
        # Check if an audio file was submitted in the form
        if 'audio_file' not in request.files:
            flash('No file part in the request.')
            return redirect(request.url)
        
        file = request.files['audio_file']
        
        # If the user submits an empty file input (no file selected)
        if file.filename == '':
            flash('No audio file selected.')
            return redirect(request.url)

        # Process the file if it exists and is allowed
        if file and allowed_file(file.filename):
            # Secure the filename before saving to prevent directory traversal attacks
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                # Save the uploaded file locally
                file.save(filepath)

                # Initialize AssemblyAI Transcriber
                transcriber = aai.Transcriber()
                
                # Upload the local audio file to AssemblyAI's cloud
                flash(f'Uploading "{filename}" for transcription...')
                upload_url = transcriber.upload_file(filepath)

                # Request transcription with default language (English US)
                config = aai.TranscriptionConfig(language_code="en_us")
                transcript = transcriber.transcribe(upload_url, config=config)

                # Check transcription status
                if transcript.status == aai.TranscriptStatus.completed:
                    transcribed_text = transcript.text
                    
                    # Save the transcribed text locally as a .txt file
                    txt_filename = os.path.splitext(filename)[0] + ".txt"
                    txt_filepath = os.path.join(app.config['UPLOAD_FOLDER'], txt_filename)
                    with open(txt_filepath, 'w') as f:
                        f.write(transcribed_text)
                    flash('File successfully uploaded and transcribed! Text saved locally.')

                elif transcript.status == aai.TranscriptStatus.error:
                    error_message = f"Transcription failed: {transcript.error}"
                    flash(f"Error: {transcript.error}. Please try another file or contact support.")
                else:
                    # This case should be rare as .transcribe waits for completion
                    error_message = f"Transcription status: {transcript.status}. Please try again."
                    flash(f"Unexpected transcription status: {transcript.status}. Please try again.")

            except Exception as e:
                # Catch any unexpected errors during the process
                error_message = f"An unexpected error occurred: {e}"
                flash(f"An unexpected error occurred: {e}. Please check your API key and file.")
            finally:
                # Clean up: remove the temporary uploaded audio file
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            flash('Invalid file type. Only .wav audio files are allowed.')

    # Render the HTML template, passing transcribed text and error messages
    return render_template('index.html', transcribed_text=transcribed_text, error_message=error_message)

if __name__ == '__main__':
    # Run the Flask development server
    # debug=True enables auto-reloading on code changes and provides a debugger
    app.run(debug=True)