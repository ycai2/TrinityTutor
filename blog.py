import os
import re
import random
import hashlib
import hmac
import datetime
import time
from datetime import datetime, timedelta
from string import letters

import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'hiiii'

#Global function to render html
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

#hash a cookie value with HMac using public key 'secret'
#return the cookie value piped with hashed value
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

#takes an cookie responded by user browser
#and checks to see if hashed values are matched
def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

# Main handler
class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    #hash cookies
    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    #check cookies
    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    #set cookies to include user_id
    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    #find user entry with a certain user id and assign it to a "user" objeact
    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))


#default function initialized when projet is created
class MainPage(BlogHandler):
  def get(self):
      self.write('Hello, World!')


##### user stuff

#generates a salt value
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

#hash the password with sha256 hash function
def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)


def users_key(group = 'default'):
    return db.Key.from_path('users', group)


#Object for User database
class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u



def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)

def comment_key(name = 'default'):
    return db.Key.from_path('comments', name)

#Object for Post database
class Post(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    author = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    #+datetime.timedelta(hours=8)
    selectedTutor = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return Post.get_by_id(uid, parent = blog_key())

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

    def displayRespondents(self):
        respondents = Respondent.all().filter('parentAFH =', str(self.key().id())).order('-created')
        return respondents

    def render_page(self):
        self._render_text = self.content.replace('\n', '<br>')
        #print self.created.now()-datetime.timedelta(hours=5)
        respondents = self.displayRespondents()
        comments = Comment.all().filter('parent_post =', str(self.key().id())).order('-created')
        return render_str("single-post.html", p = self, comments = comments, respondents = respondents)

    def render_ownerPage(self):
        self._render_text = self.content.replace('\n', '<br>')
        #print self.created.now()-datetime.timedelta(hours=5)
        respondents = self.displayRespondents()
        comments = Comment.all().filter('parent_post =', str(self.key().id())).order('-created')
        return render_str("owner-single-post.html", p = self, comments = comments, respondents = respondents)

        #change subject to title later
    def exchangeContact(self, user):
        firstConnection = Connection(postingTitle = self.subject, otherUser = self.selectedTutor, otherUserEmail = User.by_name(self.selectedTutor).email, parent_user = str(user.key().id()))
        firstConnection.put()
        secondConnection = Connection(postingTitle = self.subject, otherUser = str(user.key().id()), otherUserEmail = user.email, parent_user = str(User.by_name(self.selectedTutor)))
        secondConnection.put()
        print user
        time.sleep(1)
        #self.response.out.write("This will send you to a page saying that you exchanged contact information with such and such user. Maybe this should redirect to your connections page")


    def selectTutor(self, selectedTutor, user):
        self.selectedTutor = selectedTutor
        self.exchangeContact(user)

    




# class AFH (db.Model):
#     title = db.StringProperty(required = True)
#     subject = db.StringProperty(required = True)
#     difficulty = db.StringProperty(required = True)
#     owner = db.StringProperty(required = True)
#     selectedTutor = db.StringProperty()
#     wage = db.IntegerProperty(required = True)
#     length = db.StringProperty(required = True)
#     description = db.StringProperty(required = True)
#     dateCreated = db.DateTimeProperty(auto_now_add = True)

    #def render(self):
        #if self.user.name == owner:
            #render the page so that you have the option to select the best respondent
            #add a radial button by each name. Make it a form so when you submit, selectTutor is called with value
        #else:
            #render normal page where you can add your name to respondees
            #adding your name first identifies the username that is doing the adding.
            #that value is passed to selectTutor

    # def exchangeContact(self):
    #     firstConnection = Connection(title = self.title, otherUser = self.selectedTutor, otherUserEmail = User.by_name(self.selectedTutor).email , parent_user = str(self.user.key().id()))
    #     firstConnection.put()
    #     secondConnection = Connection(title = self.title, otherUser = str(self.user.key().id()), otherUserEmail = self.user.email, parent_user = str(User.by_name(self.selectedTutor)))
    #     secondConnection.put()
    #     self.response.out.write("This will send you to a page saying that you exchanged contact information with such and such user. Maybe this should redirect to your connections page")


    # def selectTutor(self, selectedTutor):
    #     selectedTutor = selectedTutor
    #     self.exchangeContact()

    #This is done in PostPage
    # def addRespondent(self):
    #     respondent = self.user.name #make sure this is getting the responder, not owner
    #     toBeAdded = Respondent(respondent = respondent, parentAFH = str(self.key().id()))
    #     toBeAdded.put()

    # def displayRespondents(self):
    #     respondents = Respondent.all().filter('parentAFH =', str(self.key().id())).order('-created')
    #     return respondents


class Respondent(db.Model):
    respondent = db.StringProperty(required = True)
    parentAFH = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)





#Front page
class BlogFront(BlogHandler):

    def get(self):
        posts = greetings = Post.all().order('-created')

        self.render('front.html', posts = posts)

#Object for Comment database
class Comment(db.Model):
    content = db.TextProperty(required = True)
    author = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    parent_post = db.StringProperty(required = True)







class Connection(db.Model):
    otherUser = db.StringProperty(required = True)
    otherUserEmail = db.StringProperty()
    postingTitle = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    parent_user = db.StringProperty(required = True)

class ConnectionRedirect(BlogHandler):
    def get(self):
        if self.user:
            self.redirect('connections/%s' % str(self.user.key().id()))
        else:
            self.redirect('/login')

class ConnectionsPage(BlogHandler):

    def get(self, user_id):
        if self.user.key().id() == int(user_id):
            connections = Connection.all().filter('parent_user =', str(user_id)).order('-created')
            #self.response.out.write("error for now because connections are empty %s %s" % (user_id, self.user.name))
            self.render_str("connections.html", p = self, connections = connections)
        else:
            self.redirect('/blog/?') #this is when you're accessing someone else's data









class PostPage(BlogHandler):

    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            
        #this should be post_id.owner
        if self.user.name == Post.by_id(int(post_id)).author:
            self.render("ownerPermalink.html", post = post)
        else:


            self.render("permalink.html", post = post)

    def post(self, post_id):
        if not self.user:
            self.redirect('/blog')
        
        isApply = self.request.get('apply')
        isSelect = self.request.get('select')

        if isSelect:
            selected = self.request.get('selectList')
            thisAFH = Post.by_id(int(post_id))
            thisAFH.selectTutor(selected, self.user)
            print self
            time.sleep(1)
            print self
            self.redirect('/connections')
            time.sleep(1)
            print "testing asdasd a"
            print self


        if isApply:
            respondent = self.user.name #make sure this is getting the responder, not owner
            toBeAdded = Respondent(respondent = respondent, parentAFH = str(post_id))
            toBeAdded.put()
            self.redirect('/blog/%s' % post_id)

        else:
            content = self.request.get('content').replace('\n', '<br>')

            key = db.Key.from_path('Post', int(post_id), parent=blog_key())
            post = db.get(key)

            if not post:
                self.error(404)
                return

            if content:
                created = datetime.now() - timedelta(hours=5)
                comment = Comment(parent = comment_key(), created = created, content = content, author = self.user.name, parent_post = post_id)
                comment.put()
            #else:
            self.redirect('/blog/%s' % post_id)

class Applied(BlogHandler):
    def post(self):
        if not self.user:
            self.redirect('/signup')
        else:
            post_id = self.request.get('postID')
            respondent = self.user.name #make sure this is getting the responder, not owner
            toBeAdded = Respondent(respondent = respondent, parentAFH = str(post_id))
            toBeAdded.put()
            self.response.out.write("Congratulations %s" % self.user.name)





class NewPost(BlogHandler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/blog')

        subject = self.request.get('subject')
        content = self.request.get('content')
        

        if subject and content:
            p = Post(parent = blog_key(), subject = subject, content = content, author = self.user.name)
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "Password has to be at least 3 character/numbers"
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/blog')

class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)


class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/blog')

class Welcome(BlogHandler):
    def get(self):
        if self.user:
            self.render('welcome.html', username = self.user.name)
        else:
            self.redirect('/signup')


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/blog/?(?:.json)?', BlogFront),
                               ('/blog/([0-9]+)(?:.json)?', PostPage),
                               ('/blog/newpost', NewPost),
                               ('/blog/applied', Applied),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome),
                               ('/connections', ConnectionRedirect),
                               ('/connections/([0-9]+)(?:.json)?', ConnectionsPage)
                               ],
                              debug=True)
