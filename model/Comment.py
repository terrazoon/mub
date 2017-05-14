import os
import jinja2
import webapp2
import string
import re
import hashlib
import time

from google.appengine.ext import db

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

template_dir = os.path.join(os.path.dirname(__file__), '../templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
    autoescape = True)

# This class manages one individual comment
class Comment(db.Model):
    user = db.StringProperty(required = True)
    post_id = db.IntegerProperty()
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self, username):
        self._render_text = self.content.replace("\n", "<BR>")
        return render_str("comment.html", p=self, username=username)

