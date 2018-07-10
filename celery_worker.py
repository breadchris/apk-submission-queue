#!/usr/bin/env python
import os
from app import celery, create_app

app, limiter = create_app()
app.app_context().push()