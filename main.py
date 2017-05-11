import os
import jinja2
import webapp2
import string
import re
import hashlib

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
		
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
	return t.render(params)
	
    def render(self, template, **kw):
	self.write(self.render_str(template, **kw))


class WelcomeHandler(Handler):
    def get(self):
        self.post()
        
    def post(self):
        username = self.request.cookies.get('username')
        self.render("welcome.html", username=username)

def valid_username(username):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return username and USER_RE.match(username)

def valid_password(password):
    PWD_RE = re.compile(r"^.{3,20}$")
    return password and PWD_RE.match(password)

def valid_email(email):
    EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")
    return not email or EMAIL_RE.match(email)

class User(db.Model):
    username = db.StringProperty(required = True)
    pwd_hash = db.StringProperty(required = True)
    email = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)
    
class SignupHandler(Handler):

    def get(self):
        self.render("signup.html")
        
    def post(self):
        have_error = False
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")

        params = dict(username = username, email=email)

        if not valid_username(username):
            params['error_username'] = "That's not a valid username"
            have_error = True

        if not valid_password(password):
            params['error_password'] = "That's not a valid password"
            have_error = True
        elif password != verify:
            params['error_verify'] = "Your passwords don't match"
            have_error = True

        if not valid_email(email):
            params['error_email'] = "That's not a valid email"
            have_error = True

        #check if user already exists
        user = db.GqlQuery("SELECT * from User where username='%s'" % username)
        if user.get():
            params['error_username'] = "That user already exists"
            have_error = True
            
        if have_error:
            self.render('signup.html', **params);
        else:
            pwd_hash = hashlib.sha256(username).hexdigest()
            
            new_user = User(username = username, pwd_hash = pwd_hash, email = email)
            new_user.put()
            self.response.headers.add_header('Set-Cookie', 'username=%s' % str(username))
            self.redirect("/welcome")


class LoginHandler(Handler):

    def get(self):
        self.render("login.html")
        
    def post(self):
        have_error = False
        username = self.request.get("username")
        password = self.request.get("password")
        
        params = dict(username = username, password = password)

        if not valid_username(username):
            params['error_username'] = "That's not a valid username"
            have_error = True

        if not valid_password(password):
            params['error_password'] = "That's not a valid password"
            have_error = True
        
        #check if user already exists
        q = db.GqlQuery("SELECT * from User where username='%s'" % username)
        user = q.get()
        if not user:
            params['error_username'] = "That user doesn't exist"
            have_error = True

        if user:
            pwd_match = hashlib.sha256(password).hexdigest()
            if pwd_match != user.pwd_hash:
                params['error_password'] = "That password is invalid"
                have_error = True

            
        if have_error:
            self.render('login.html', **params);
        else:
            self.response.headers.add_header('Set-Cookie', 'username=%s' % str(username))
            self.redirect("/welcome")


class LogoutHandler(Handler):

    def get(self):
        self.response.headers.add_header('Set-Cookie', 'username=; Path=/')
        self.redirect('/signup')   
        
    def post(self):
        self.response.headers.add_header('Set-Cookie', 'username=; Path=/')
        
        self.redirect('/signup')        
	
class MainPage(Handler):
	def get(self):       
            self.redirect("/signup")
		


##### blog


def blog_key(name = 'default'):
    return db.Key.from_path('blog', name)


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogPost(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self):
        self._render_text = self.content.replace("\n", "<BR>")
        return render_str("post.html", p=self)
    
class BlogHandler(Handler):
    def get(self):
        blogposts = db.GqlQuery('SELECT * from BlogPost ORDER BY created DESC LIMIT 10')
        self.render('front.html', blogposts=blogposts)
        
class NewPostHandler(Handler):
    def get(self):
        self.render('newpost.html')

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')
        if subject and content:
            newpost = BlogPost(subject=subject, content=content)
            newpost.put()

            p = db.GqlQuery('SELECT * from BlogPost ORDER BY created DESC LIMIT 1')
            self.redirect('/blog/%s' % str(p.get().key().id()))
        else:
            self.redirect('/blog/newpost')
            
class PermalinkHandler(Handler):
    def get(self, post_id):
        #key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.GqlQuery('SELECT * from BlogPost ORDER BY created DESC LIMIT 1')
        
        if not post:
            self.write('no')
            #self.error(404)
            return

        self.render("permalink.html", post = post.get())

		
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/signup', SignupHandler),
    ('/welcome', WelcomeHandler),
    ('/blog/newpost', NewPostHandler),
    ('/blog', BlogHandler),
    ('/blog/([0-9]+)', PermalinkHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    

], debug=True)
