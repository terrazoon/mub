import os
import jinja2
import webapp2
import string
import re
import hashlib
import time

from google.appengine.ext import db


	
# This class manages a user
class User(db.Model):
    username = db.StringProperty(required = True)
    pwd_hash = db.StringProperty(required = True)
    email = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)
