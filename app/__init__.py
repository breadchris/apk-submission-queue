#!/usr/bin/env python

import os
import simplejson
import traceback
import logging
from datetime import datetime

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request, render_template, redirect, url_for, send_from_directory
from flask_bootstrap import Bootstrap
from werkzeug import secure_filename
from celery import Celery

import models
from emulator_manager import Challenge, EmulatorManager

def setup_app_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

CELERY_BROKER_URL = 'redis://localhost:6379/0'

logger = setup_app_logger('root')
celery = Celery(__name__, broker=CELERY_BROKER_URL)

challenge_4_apk = os.path.join(os.path.dirname(__file__), "apks/challenge4.apk")
challenge_4 = Challenge(challenge_4_apk, "flag{my_favorite_cereal_and_mazes}", "/data/local/tmp/challenge4")

challenge_5_apk = os.path.join(os.path.dirname(__file__), "apks/challenge5.apk")
challenge_5 = Challenge(challenge_4_apk, "fla{challenge_5_example_flag}", "/data/local/tmp/challenge5")

emu_manager = EmulatorManager(["android_P_x86_64_1"], [challenge_4])

def create_app():
    app = Flask(__name__)
    app.config['CELERY_BROKER_URL'] = CELERY_BROKER_URL
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

    celery.conf.update(app.config)

    bootstrap = Bootstrap(app)

    app.config['SECRET_KEY'] = 'hard to guess string'
    app.config['UPLOAD_FOLDER'] = '/tmp/submissions/'
    app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
    app.config['ALLOWED_EXTENSIONS'] = set(['apk'])

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    import views
    app.register_blueprint(views.status)
    app.register_blueprint(views.uploadbp)

    models.init_db()

    emu_manager.init_emulators()

    limiter = Limiter(app, default_limits = ["1/second"], key_func=get_remote_address)
    limiter.limit("20/hour")(views.uploadbp)

    return app, limiter

app, limiter = create_app()
