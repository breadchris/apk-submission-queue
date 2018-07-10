import os
import time
from datetime import datetime

from . import celery
from models import db_session
from app import emu_manager
from flask import Blueprint, current_app, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

status = Blueprint('status', __name__)
uploadbp= Blueprint('uploadbp', __name__)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def gen_file_name(filename):
    """
    If file was exist already, rename it and return a new name
    """
    i = 1
    name, extension = os.path.splitext(filename)
    while os.path.exists(os.path.join(current_app.config['UPLOAD_FOLDER'], "{}_{}_{}".format(name, i, extension))):
        i += 1

    return filename

# 5 min timeout
@celery.task(bind=True, soft_time_limit=10*60)
def run_apk_in_emu(self, apk_file):
    # TODO: Check if the user is able to submit apk
    # to check:
    #   - they already have an apk running atm
    #   - they have attempted too many submissions within the hour
    self.update_state(state='PENDING', meta={
        "status": "Waiting for next available emulator...",
        "time": datetime.utcnow()
    })

    emu = None
    while emu is None:
        emu = emu_manager.get_emulator()
        time.sleep(3)

    # Run submission will release the emulator on completition
    success = emu_manager.run_submission(self, emu, apk_file)
    if success == True:
        return {
            "status": "Done running APK!",
            "time": datetime.utcnow()
        }
    else:
        return {
            "status": "There was an error when running your APK. If this problem persists, contact an admin.",
            "time": datetime.utcnow()
        }

@status.route("/status/<task_id>}", methods=['GET'])
def get_status(task_id):
    task = run_apk_in_emu.AsyncResult(task_id)

    status_update = {}
    if task.info is None:
        status_update = {"time": datetime.utcnow(), "status": "Pending..."}
    else:
        status_update = {"time": task.info.get("time", 0), "status": task.info.get("status", "")}

    return render_template('status.html', status_update=status_update)

@uploadbp.route("/upload", methods=['POST'])
def upload():
    # TODO: Check if we have a valid user
    # TODO: IP rate limit?
    files = request.files['file']

    if not files:
        return simplejson.dumps({"result": "No file to upload"})

    filename = secure_filename(files.filename)
    filename = gen_file_name(filename)

    if not allowed_file(files.filename):
        return simplejson.dumps({"result": "File not allowed"})
    else:
        # save file to disk
        uploaded_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        files.save(uploaded_file_path)

        task = run_apk_in_emu.delay(uploaded_file_path)

        return redirect(url_for('status.get_status', task_id=task.id))


@status.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')
