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
class Handler(webapp2.RequestHandler):
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
    created = db.DateTimeProperty(auto_now_add = True)
    email = db.StringProperty(required = True)
    nickname = db.StringProperty(required = True)
    year = db.IntegerProperty(required = True)
    major = db.StringProperty(required = True)
    description = db.StringProperty()
    feedbackList = db.ListProperty(str, indexed = True, default=[])

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email, nickname, year, major, description):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email,
                    nickname = nickname,
                    year = int(year),
                    major = major,
                    description = description)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u

    def render(self):
        # self._render_text = self.content.replace('\n', '<br>')
        return render_str("users.html", p = self)



def _key(name = 'default'):
    return db.Key.from_path('s', name)

def comment_key(name = 'default'):
    return db.Key.from_path('comments', name)

#Object for Post database
class Post(db.Model):
    title = db.StringProperty(required = True)
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)

    wage = db.IntegerProperty(required = True)
    meetings = db.StringProperty(required = True)
    difficulty = db.StringProperty(required = True)

    author = db.StringProperty(required = True)
    authorID = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    #+datetime.timedelta(hours=8)
    selectedTutor = db.StringProperty()
    selectedTutorID = db.StringProperty()

    feedbackOnTutee = db.BooleanProperty()
    feedbackOnTutor = db.BooleanProperty()

    @classmethod
    def by_id(cls, uid):
        return Post.get_by_id(uid, parent = _key())

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
        firstConnection = Connection(postingTitle = self.subject, otherUser = self.selectedTutor, otherUserID = str(User.by_name(self.selectedTutor).key().id()), otherUserEmail = User.by_name(self.selectedTutor).email, parent_user = User.by_id(user.key().id()).name)
        firstConnection.put()
        secondConnection = Connection(postingTitle = self.subject, otherUser = User.by_id(user.key().id()).name, otherUserID = str(user.key().id()), otherUserEmail = User.by_id(user.key().id()).email, parent_user = self.selectedTutor)
        secondConnection.put()
        
    def selectTutor(self, selectedTutor, user):
        self.exchangeContact(user)


class Respondent(db.Model):
    respondent = db.StringProperty(required = True)
    parentAFH = db.StringProperty()
    userid = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

def feedback_key(name = 'default'):
    return db.Key.from_path('feedbacks', name)

class Feedback(db.Model):
    receiver = db.StringProperty(required = True)
    receiverID = db.StringProperty(required = True)
    writer = db.StringProperty(required = True)
    writerID = db.StringProperty(required = True)
    AFHID = db.StringProperty(required = True)
    AFHTitle = db.StringProperty(required = True)
    AFHSubject = db.StringProperty(required = True)
    AFHDifficulty = db.StringProperty(required = True)
    rating = db.IntegerProperty(required = True)
    comment = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_id(cls, uid):
        return Feedback.get_by_id(uid, parent = feedback_key())

    def render(self):
        return render_str("singleFeedback.html", feedback = self)

class Comment(db.Model):
    content = db.TextProperty(required = True)
    author = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    parent_post = db.TextProperty(required = True)

class Connection(db.Model):
    otherUser = db.StringProperty(required = True)
    otherUserID = db.StringProperty(required = True)
    otherUserEmail = db.StringProperty(required = True)
    postingTitle = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    parent_user = db.StringProperty(required = True)

class Front(Handler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        self.render('front.html', posts = posts)

class ShowAllUsers(Handler):
    def get(self):
        users = User.all().order('-created')
        self.render("front.html", posts = users)

class ConnectionRedirect(Handler):
    def get(self):
        if self.user:
            self.redirect('connections/%s' % str(self.user.key().id()))
        else:
            self.redirect('/login')

class ShowMyAccount(Handler):
    def get(self):
        if self.user:
            self.redirect('users/%s' % str(self.user.key().id()))
        else:
            self.redirect('/login')

class ConnectionsPage(Handler):
    def get(self, user_id):
        if self.user:
            if self.user.key().id() == int(user_id):
                username = User.by_id(int(user_id)).name
                connections = Connection.all().filter('parent_user =',username).order('-created')
                self.render("connections.html", p = self, connections = connections)
            else:
                self.redirect('/')
        else:
            self.redirect('/login')

class FeedbackPage(Handler):
    def get(self, post_id):
        post = Post.by_id(int(post_id))

        if post.selectedTutor:
            if self.user.key().id() == int(post.selectedTutorID):
                print "hello selected tutor yee"
                print post.feedbackOnTutee
                if post.feedbackOnTutee:
                    print "You already did this Tutee"
                    self.redirect('/')
                else:
                    self.render("submitFeedback.html", post = post)
                #render feedback render_page
            elif self.user.key().id() == int(post.authorID):
                if post.feedbackOnTutor:
                    print "You already did this Author"
                    self.redirect('/')
                else:
                    print "hello author"
                self.render("submitFeedback.html", post = post)
        else:
            print "you do not have permission to view this page"

    def post(self, post_id):
        post = Post.by_id(int(post_id))

        if not self.user:
            self.redirect('/login')
        else:
            rating = int(self.request.get('rating'))
            comment = self.request.get('comment')

            if rating:
                if self.user.name == post.author:
                    f = Feedback(receiver = post.selectedTutor, receiverID = post.selectedTutorID, writer = self.user.name, writerID = str(self.user.key().id()), AFHID = str(post_id), AFHTitle = post.title, AFHSubject = post.subject, AFHDifficulty = post.difficulty, rating = rating, comment = comment)
                    f.put()
                    user = User.by_id(int(post.selectedTutorID))
                    user.feedbackList.append(str(f.key().id()))
                    user.put()
                    post.feedbackOnTutor = True
                    post.put()
                    #feedback should be attached to each user for speed
                    #fix this later. create an array for each user and add this feedback to that user?
                else:
                    f = Feedback(receiver = post.author, receiverID = post.authorID, writer = post.selectedTutor, writerID = post.selectedTutorID, AFHID = str(post_id), AFHTitle = post.title, AFHSubject = post.subject, AFHDifficulty = post.difficulty, rating = rating, comment = comment)
                    f.put()
                    user = User.by_id(self.user.key().id())
                    user.feedbackList.append(str(f.key().id()))
                    user.put()
                    post.feedbackOnTutee = True
                    post.put()
                self.redirect('/')
            else:
                print "You must submit a rating"
                #fix this later

class PostPage(Handler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=_key())
        post = db.get(key)

        if not post:
            self.error(404)
            
        if not self.user:
            self.redirect("/login")
        else:
            if post.selectedTutor:
                if self.user.key().id() == int(post.selectedTutorID):
                    self.redirect('/feedback/%s' % post_id)
                elif self.user.key().id() == int(post.authorID):
                    self.redirect('/feedback/%s' % post_id)
            elif self.user.name == Post.by_id(int(post_id)).author:
                print "HALSKDJALSKDJAasd134234523454325S"
                self.render("ownerPermalink.html", post = post)
            else:
                print "HALSKDJALSKDJAS"
                self.render("permalink.html", post = post)

    def post(self, post_id):
        if not self.user:
            self.redirect('/')
        
        isApply = self.request.get('apply')
        isSelect = self.request.get('select')

        if isSelect:
            selected = self.request.get('selectList')
            if selected:
                thisAFH = Post.by_id(int(post_id))
                thisAFH.selectedTutor = selected
                thisAFH.selectedTutorID = str(User.by_name(selected).key().id())
                thisAFH.put()
                thisAFH.selectTutor(selected, self.user)
                self.redirect('/connections')
            else:
                self.redirect('/')

        elif isApply:
            respondent = self.user.name
            alreadyAppliedFlag = False
            respondents = Respondent.all().filter('parentAFH =', str(post_id)).order('-created')
            for each in respondents:
                if each.respondent == respondent:
                    alreadyAppliedFlag = True
            if alreadyAppliedFlag:
                self.redirect('/afh/%s' % post_id)
            else:
                toBeAdded = Respondent(respondent = respondent, parentAFH = str(post_id), userid = str(User.by_name(respondent).key().id()))
                toBeAdded.put()
                self.redirect('/afh/%s' % post_id)

        else:
            content = self.request.get('content').replace('\n', '<br>')
            key = db.Key.from_path('Post', int(post_id), parent=_key())
            post = db.get(key)

            if not post:
                self.error(404)
                return

            else:
                if content:
                    created = datetime.now() - timedelta(hours=5)
                    comment = Comment(parent = comment_key(), created = created, content = content, author = self.user.name, parent_post = post_id)
                    comment.put()
                self.redirect('/afh/%s' % post_id)


class NewPost(Handler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/')
        else:

            title = self.request.get('title')
            selectedSubject = self.request.get('subjectList')
            content = self.request.get('content')
            wage = int(self.request.get('wage'))
            selectedMeetings = self.request.get('meetingsList')
            selectedDifficulty = self.request.get('difficultyList')

            if title and selectedSubject and content and wage and selectedMeetings and selectedDifficulty:
                p = Post(parent = _key(), title = title, subject = selectedSubject, content = content, wage = wage, meetings = selectedMeetings, difficulty = selectedDifficulty, author = self.user.name, authorID = str(self.user.key().id()))
                p.put()
                self.redirect('/afh/%s' % str(p.key().id()))
            
            else:
                error = "Enter information in the required fields!"
                self.render("newpost.html", title = title, subject=selectedSubject, content=content, wage = wage, meetings = selectedMeetings, difficulty = selectedDifficulty, error=error)


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(Handler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')
        self.name = self.request.get('name')
        self.year = self.request.get('year')
        self.major = self.request.get('major')
        self.description = self.request.get('description')


        params = dict(username = self.username,
                      email = self.email,
                      name = self.name,
                      year = self.year,
                      major = self.major,
                      description = self.description)

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
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email, self.name, self.year, self.major, self.description)
            u.put()
            self.login(u)
            self.redirect('/')

class Profile(Handler):
    def get(self, user_id):
        user = User.by_id(int(user_id))
        if not self.user:
            self.redirect("/login")
        else:

            feedbacks = user.feedbackList
            print "feed back is "
            print feedbacks
            feedbackText = ""
            for thing in feedbacks:
                each = Feedback.get_by_id(int(thing))
                feedbackText += each.render()

            self.render("profile.html", u = user, feedbacks = feedbackText)

class Login(Handler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(Handler):
    def get(self):
        self.logout()
        self.redirect('/')

class Welcome(Handler):
    def get(self):
        if self.user:
            self.render('welcome.html', username = self.user.name)
        else:
            self.redirect('/signup')


app = webapp2.WSGIApplication([('/', Front),
                               ('/afh/([0-9]+)(?:.json)?', PostPage),
                               ('/feedback/([0-9]+)(?:.json)?', FeedbackPage),
                               ('/newpost', NewPost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome),
                               ('/myaccount', ShowMyAccount),
                               ('/users', ShowAllUsers),
                               ('/connections', ConnectionRedirect),
                               ('/connections/([0-9]+)(?:.json)?', ConnectionsPage),
                               ('/users/([0-9]+)(?:.json)?', Profile)
                               ],
                              debug=True)
