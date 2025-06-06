import os
import logging
import datetime
import boto3
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify
from flask_cors import CORS # Needed if M5Stack and server are on different origins

# Configure basic logging for better visibility in Render logs
# This helps you see what's happening on your server in real-time
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# Enable CORS for all origins. In a production environment, you might want to restrict this
# to only the domains you explicitly trust for better security.
CORS(app)

# --- S3 Configuration ---
# These values are crucial for connecting to your AWS S3 bucket.
# IMPORTANT: These should be set as Environment Variables in your Render.com service settings.
# Do NOT hardcode your AWS credentials directly in this code, especially if it's public!
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
# Default S3 region to 'us-east-1' if not specified.
# Make sure this matches the region where you created your S3 bucket.
S3_REGION = os.environ.get('S3_REGION', 'us-east-1')

# Initialize S3 client outside the request handling functions for efficiency.
# This client will be used for all S3 interactions.
s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME:
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=S3_REGION
        )
        app.logger.info("AWS S3 client initialized successfully.")
    except Exception as e:
        # Log an error if S3 client initialization fails (e.g., bad credentials)
        app.logger.error(f"Failed to initialize AWS S3 client: {e}")
else:
    # Log a warning if environment variables are missing
    app.logger.warning("AWS S3 credentials or bucket name not set as environment variables. S3 uploads will not work.")

# --- Flask Routes ---

@app.route('/')
def home():
    """
    A simple home route to confirm the server is running.
    When you visit your Render app's URL, this message will appear.
    """
    return "M5Stack Audio Upload Server is running! Ready to receive audio and send to S3."

@app.route('/upload', methods=['POST'])
def upload_audio():
    """
    This is the main endpoint for receiving audio from the M5Stack.
    It expects a POST request with the audio data in the request body.
    """
    app.logger.info("Received an audio upload request.")

    # Check if the S3 client was successfully initialized. If not, we can't upload.
    if not s3_client:
        app.logger.error("S3 client not initialized. Cannot upload to S3.")
        return jsonify({"error": "Server not configured for S3 uploads. Check environment variables."}), 500

    # The M5Stack's HTTPClient::POST sends raw binary data.
    # In Flask, this data is accessible via request.data.
    audio_data = request.data

    if not audio_data:
        app.logger.warning("No audio data received in the request body.")
        return jsonify({"error": "No audio data received. Request body was empty."}), 400

    # Try to extract the filename from the 'Content-Disposition' header.
    # The M5Stack code sets this header: http.addHeader("Content-Disposition", "attachment; filename=\"" + filename.substring(1) + "\"");
    filename = None
    content_disposition = request.headers.get('Content-Disposition')
    if content_disposition:
        try:
            # Parse the filename from the header string (e.g., "attachment; filename="rec_1.wav"")
            parts = content_disposition.split('filename=')
            if len(parts) > 1:
                filename = parts[1].strip('"') # Remove surrounding quotes
                app.logger.info(f"Extracted filename from Content-Disposition: {filename}")
        except Exception as e:
            app.logger.warning(f"Could not parse filename from Content-Disposition header: {e}")
            
    # Fallback: If no filename was provided or parsing failed, generate a timestamped filename.
    if not filename:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3] # YYYYMMDD_HHMMSS_milliseconds
        filename = f"audio_{timestamp}.wav"
        app.logger.info(f"Content-Disposition filename not found or invalid. Using generated filename: {filename}")

    try:
        # Upload the audio data directly to the S3 bucket.
        # Key: This is the name/path of the file in your S3 bucket.
        # Body: The raw audio data received from the M5Stack.
        # ContentType: Important for browsers/applications to recognize the file type.
        # ACL='public-read': Optional. Makes the uploaded file publicly accessible via its S3 URL.
        #                    Be cautious with this in production. For private files, you'd use
        #                    signed URLs to grant temporary access.
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=filename,
            Body=audio_data,
            ContentType='audio/wav',
            ACL='public-read' # You might remove this if you want files to be private
        )
        app.logger.info(f"Successfully uploaded '{filename}' to S3 bucket '{S3_BUCKET_NAME}'.")

        # Construct the public URL of the uploaded file (if ACL='public-read')
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{filename}"
        
        # Return a success message and the S3 URL to the M5Stack
        return jsonify({
            "message": f"File '{filename}' uploaded successfully to S3!",
            "s3_url": s3_url
        }), 200

    except ClientError as e:
        # Catch specific S3 client errors (e.g., authentication issues, bucket not found)
        error_message = e.response.get('Error', {}).get('Message', 'Unknown S3 error')
        app.logger.error(f"S3 upload failed for '{filename}': {error_message}")
        return jsonify({"error": f"S3 upload failed: {error_message}"}), 500
    except Exception as e:
        # Catch any other unexpected errors during the process
        app.logger.error(f"An unexpected error occurred during audio upload: {e}", exc_info=True)
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

    # This line should theoretically not be reached as all paths return a response.
    return jsonify({"error": "Unknown request issue."}), 405

# --- Local Development Server Start ---
if __name__ == '__main__':
    # This block only runs when you execute app.py directly (e.g., `python app.py`)
    # It's for local testing.
    # In a production environment like Render, Gunicorn or a similar WSGI server
    # will handle running your app using the 'web: gunicorn app:app' command in your Procfile.
    
    # Render will set a PORT environment variable, use that if available.
    # Otherwise, default to 5000 for local development.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True) # debug=True is good for local development