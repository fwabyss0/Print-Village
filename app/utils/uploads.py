import os, uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_file(file_storage, subdir=''):
    if not file_storage or file_storage.filename == '' or not allowed_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit('.',1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subdir)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, secure_filename(fname)))
    return f"{subdir}/{fname}" if subdir else fname