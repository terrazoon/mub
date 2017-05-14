import os
import jinja2
import webapp2
import string
import re
import hashlib
import time

from google.appengine.ext import db


# This class manages all the likes for the blog
class Like(db.Model):
    user = db.StringProperty(required = True)
    post_id = db.IntegerProperty(required = True)


