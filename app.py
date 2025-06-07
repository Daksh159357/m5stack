from flask import Flask, request, render_template_string
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if not exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Check for allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HTML page with inline template
HTML_PAGE = """
<!doctype html>
<html>
<head>
    <title>Upload Photo</title>
</head>
<body>
    <h2>Upload a Photo</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="photo" accept="image/*" required>
        <button type="submit">Upload</button>
    </form>
    {% if filename %}
        <p>Uploaded successfully: <strong>{{ filename }}</strong></p>
        <img src="/uploads/{{ filename }}" style="max-width:300px;">
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def upload():
    filename = None
    if request.method == 'POST':
        if 'photo' not in request.files:
            return 'No file part in the request'
        file = request.files['photo']
        if file.filename == '':
            return 'No selected file'
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return render_template_string(HTML_PAGE, filename=filename)

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return app.send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
