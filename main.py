import os
import jinja2
import webapp2
import string
import re
import hashlib
import time

#TODO
# Fix permalink bug
# edit/delete comments
# welcome page should really be main blog page
# add new post button


from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
    autoescape = True)

#Global methods
def valid_cookie(raw_cookie):
    arr = raw_cookie.split("|")
    if len(arr) != 2:
        return False
    
    cookie_value = arr[0]
    provided_hash = arr[1]
    test_hash = hashlib.sha256(cookie_value).hexdigest()
    return test_hash == provided_hash

def valid_username(username):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    return username and USER_RE.match(username)

def valid_password(password):
    PWD_RE = re.compile(r"^.{3,20}$")
    return password and PWD_RE.match(password)

def valid_email(email):
    EMAIL_RE = re.compile(r"^[\S]+@[\S]+.[\S]+$")
    return not email or EMAIL_RE.match(email)

def get_hashed_cookie(cookie_key, cookie_value):
    hsh = str(hashlib.sha256(cookie_value).hexdigest())
    hashed_cookie = "%s = %s|%s" % (cookie_key, cookie_value, hsh)
    return str(hashed_cookie)

def blog_key(name = 'default'):
    return db.Key.from_path('blog', name)


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

#Db classes

class Like(db.Model):
    user = db.StringProperty(required = True)
    post_id = db.IntegerProperty(required = True)
    
class BlogPost(db.Model):
    #TODO make author required after clean up db
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
        
        return render_str("post.html", p=self, comments=comments, username=username)

class Comment(db.Model):
    user = db.StringProperty(required = True)
    post_id = db.IntegerProperty()
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)

    def render(self, username):
        self._render_text = self.content.replace("\n", "<BR>")
        return render_str("comment.html", p=self, username=username)

class User(db.Model):
    username = db.StringProperty(required = True)
    pwd_hash = db.StringProperty(required = True)
    email = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)

#Handlers

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
		
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
	return t.render(params)
	
    def render(self, template, **kw):
	self.write(self.render_str(template, **kw))

    
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
            
            new_user = User(username = username, pwd_hash = pwd_hash,
                email = email)
            new_user.put()
            self.response.headers.add_header('Set-Cookie',
                get_hashed_cookie('username', username))
            self.redirect("/blog")


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
                self.write("pwd_match=%s" % pwd_match)
                self.write("user.pwd_has=%s" % user.pwd_hash)
                params['error_password'] = "That password is invalid"
                have_error = True

            
        if have_error:
            self.render('login.html', **params);
        else:
            self.response.headers.add_header('Set-Cookie', get_hashed_cookie('username', username))
            self.redirect("/blog")


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



    
class BlogHandler(Handler):
         
    def get(self):
        hsh = self.request.cookies.get('username')
        username = ""
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username=arr[0]
            
        blogposts = db.GqlQuery('SELECT * from BlogPost ORDER BY created DESC LIMIT 10')
        self.render('front.html', blogposts=blogposts, username=username)
        
class NewPostHandler(Handler):
    def get(self):
        self.render('newpost.html')

    def post(self):
        hsh = self.request.cookies.get('username')
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            subject = self.request.get('subject')
            content = self.request.get('content')
            if subject and content:
                newpost = BlogPost(author=username, subject=subject,
                    content=content, likes=0)
                newpost.put()
                self.redirect('/blog/%s' % str(newpost.key().id()))
            else:
                self.redirect('/blog/newpost')
        else:
            self.redirect('/signup')

#TODO fix bug here, blank display            
class PermalinkHandler(Handler):
    def get(self, post_id):


        params = dict(post_id = post_id)
        
        posts = db.GqlQuery('SELECT * from BlogPost ORDER BY created DESC')
        for post in posts:
            if str(post_id) == str(post.key().id()):
                self.render("permalink.html", post=post)
                break
        
        
        #if not post:
        #    self.error(404)
        #    return

        
class LikeHandler(Handler):
    def get(self):
        self.redirect('/blog')

    def incr_likes(self, post_id, username):
        #find the post in question
        p = db.GqlQuery(
            "SELECT * FROM BlogPost where __key__ = KEY('BlogPost', "
            + post_id + ")")
        post = p.get()

        #find out if the user has already liked it
        q = db.GqlQuery(
            "SELECT * FROM Like where user='" + username + "'"
            + " and post_id=" + post_id)
        like = q.get()

        #if the user already liked it, unlike it
        if post and post.author != username:
            if like:
                like.delete()
                if post.likes > 0:
                    post.likes -= 1
                post.put()
            else:
                like = Like(user = username, post_id = long(post_id))
                like.put()
                if post.likes == None:
                    post.likes = 0
                else:
                    post.likes += 1
                post.put()
            return True
        else:
            params = dict(username=username)
            params['error_msg'] = "You can't like your own post"
            self.render('editpost.html', **params )
            return False
        
            
        
    def post(self, post_id):
        hsh = self.request.cookies.get('username')
        
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            if self.incr_likes(post_id, username):
                self.redirect('/blog')
        else:
            self.redirect('/signup')

        
class DeleteHandler(Handler):
    def get(self):
        self.redirect('/blog')

    def delete_post(self, post_id, username):
        p = db.GqlQuery(
            "SELECT * FROM BlogPost where __key__ = KEY('BlogPost', "
            + post_id + ")")
        post = p.get()
        
        if post and post.author == username:            
            post.delete()
            
            return True
        else:
            params = dict(username=username)
            params['error_msg'] = "You can't delete other people's posts"
            self.render('editpost.html', **params )
            return False

        
    def post(self, post_id):
        hsh = self.request.cookies.get('username')
        
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            if self.delete_post(post_id, username):
                
                self.redirect('/blog')
                return
        else:
            self.redirect('/signup')


class EditHandler(Handler):
    def get(self):
        self.render('editpost.html')

    def edit_post(self, post_id, username):
        p = db.GqlQuery(
            "SELECT * FROM BlogPost where __key__ = KEY('BlogPost', "
            + post_id + ")")
        post = p.get()
        if post and post.author == username:
            self.render('editpost.html', p = post)
        else:
            params = dict(username=username)
            params['error_msg'] = "You can't edit other people's posts"
            self.render('editpost.html', **params )

        
    def post(self, post_id):
        hsh = self.request.cookies.get('username')
        
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            self.edit_post(post_id, username)
        else:
            self.redirect('/signup')

class SaveHandler(Handler):
    def get(self):
        self.render('editpost.html')

    def save_post(self, post_id, subject, content, username):
        p = db.GqlQuery(
            "SELECT * FROM BlogPost where __key__ = KEY('BlogPost', "
            + post_id + ")")
        post = p.get()
        if post and post.author == username:
            post.subject = subject
            post.content = content
            post.put()

        
    def post(self, post_id):
        hsh = self.request.cookies.get('username')
        subject = self.request.get("subject")
        content = self.request.get("content")
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            self.save_post(post_id, subject, content, username)
            self.redirect("/blog")
        else:
            self.redirect('/signup')

        
class NewCommentHandler(Handler):
    def get(self, post_id):
        self.render('new_comment.html')

    def post(self, post_id):
        hsh = self.request.cookies.get('username')
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            content = self.request.get('content')
            if content:
                comment = Comment(user=username, content=content,
                    post_id = long(post_id))
                comment.put()
                self.redirect('/blog')
            else:
                self.redirect('/blog')
        
        else:
            self.redirect('/signup')
            
class DeleteCommentHandler(Handler):
    def get(self, comment_id):
        
        hsh = self.request.cookies.get('username')

        if not valid_cookie(hsh):
            self.redirect('/signup')
            
        arr = hsh.split("|")
        username = arr[0]
            
        p = db.GqlQuery(
        "SELECT * FROM Comment where __key__ = KEY('Comment', "
            + comment_id + ")")
        comment = p.get()

        params = dict(username=username)    
        if comment and comment.user == username:            
            comment.delete()
            params['success_msg'] = "You deleted your comment"
            self.render('editpost.html', **params )
            
        else:
            params['error_msg'] = "You can't delete other people's comments"
            self.render('editpost.html', **params )
                           


class EditCommentHandler(Handler):
    def get(self, comment_id):
        hsh = self.request.cookies.get('username')
        if not valid_cookie(hsh):
            self.redirect('/signup')
         
        arr = hsh.split("|")
        username = arr[0]
        
        q = db.GqlQuery(
            "SELECT * FROM Comment where __key__ = KEY('Comment', "
            + comment_id + ")")
        comment = q.get()
        if comment and comment.user == username:
            #self.write(comment.user)
            #self.write(comment.content)
            self.render('edit_comment.html', p = comment)
        else:
            params = dict(username=username)
            params['error_msg'] = "You can't edit other people's comments"
            self.render('edit_comment.html', **params )

        
    def post(self, comment_id):
        hsh = self.request.cookies.get('username')
        
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            self.edit_comment(comment_id, username)
        else:
            self.redirect('/signup')


class SaveCommentHandler(Handler):
    def get(self):
        self.write("get")
        #self.render('edit_comment.html')

    def save_comment(self, comment_id, content, username):
        p = db.GqlQuery(
            "SELECT * FROM Comment where __key__ = KEY('Comment', "
            + comment_id + ")")
        comment = p.get()
        if comment and comment.user == username:
            comment.content = content
            comment.put()

        
    def post(self, comment_id):
        hsh = self.request.cookies.get('username')
        content = self.request.get("content")
        if valid_cookie(hsh): 
            arr = hsh.split("|")
            username = arr[0]
            self.save_comment(comment_id, content, username)
            self.redirect("/blog")
        else:
            self.redirect('/signup')
            
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/signup', SignupHandler),
    ('/blog/newpost', NewPostHandler),
    ('/blog', BlogHandler),
    ('/blog/([0-9]+)', PermalinkHandler),
    ('/login', LoginHandler),
    ('/logout', LogoutHandler),
    ('/like/([0-9]+)', LikeHandler),
    ('/delete/([0-9]+)', DeleteHandler),
    ('/edit/([0-9]+)', EditHandler),
    ('/save/([0-9]+)', SaveHandler),
    ('/blog/new_comment/([0-9]+)', NewCommentHandler),
    ('/blog/delete_comment/([0-9]+)', DeleteCommentHandler),
    ('/blog/edit_comment/([0-9]+)', EditCommentHandler),
    ('/blog/save_comment/([0-9]+)', SaveCommentHandler),
    
    
    

], debug=True)
