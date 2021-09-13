#! /usr/bin/python3.8
import logging
import os
import sys
from dotenv import load_dotenv
load_dotenv(os.path.join('/scratch/gccb/mark/flask', '.env') )
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/scratch/gccb/mark/flask/')
from api import app as application
application.secret_key = os.getenv("SECRET_KEY")
