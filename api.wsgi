#! /usr/bin/python3.8
import logging
import os
import sys
from dotenv import load_dotenv
os.environ['MPLCONFIGDIR'] = '/tmp/'
load_dotenv(os.path.join(os.path.dirname(__file__), '.env') )
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, os.path.dirname(__file__) )
from api import app as application
application.secret_key = os.getenv("SECRET_KEY")
