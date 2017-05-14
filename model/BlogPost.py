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

	
# This class manages one individual post
class BlogPost(db.Model):
    author = db.StringProperty(required = True)
    likes = db.IntegerProperty()
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self, username):
        self._render_text = self.content.replace("\n", "<BR>")
        
        comments = db.GqlQuery("SELECT * from Comment where post_id=%d"
            % self.key().id())
        
        return render_str("post.html", p=self, comments=comments,
            username=username)
