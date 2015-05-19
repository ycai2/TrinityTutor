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
from google.appengine.api import mail

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

def make_email_hash(email, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(email + salt).hexdigest()
    return '%s' % (h)

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
    email_hash = db.StringProperty(required = True)
    email = db.StringProperty(required = True)
    nickname = db.StringProperty(required = True)
    year = db.IntegerProperty(required = True)
    major = db.StringProperty(required = True)
    description = db.StringProperty()
    confirmed = db.BooleanProperty(required = True) 
    tutorRating = db.FloatProperty()
    numberTutorJobs = db.IntegerProperty(required = True)
    tuteeRating = db.FloatProperty()
    numberTuteeJobs = db.IntegerProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    feedbackList = db.ListProperty(str, indexed = True, default=[])
    connectionList = db.ListProperty(str, indexed = True, default=[])
    appliedList = db.ListProperty(str, indexed = True, default=[])
    createdList = db.ListProperty(str, indexed = True, default=[])

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())
    
    @classmethod
    def by_name(cls, name):
        user = User.all().filter('name =', name).get()
        return user

    @classmethod
    def register(cls, name, pw, email, nickname, year, major, description):
        pw_hash = make_pw_hash(name, pw)
        email_hash = make_email_hash(email)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email_hash = email_hash,
                    email = email,
                    nickname = nickname,
                    year = int(year),
                    major = major,
                    description = description,
                    confirmed = False,
                    tutorRating = 0.0,
                    tuteeRating = 0.0,
                    numberTuteeJobs = 0,
                    numberTutorJobs = 0)

    @classmethod
    def login(cls, name, pw):
        user = cls.by_name(name)
        if user and valid_pw(name, pw, user.pw_hash):
            return user

    def sendVerificationEmail(self):
        userName = self.nickname
        userEmail = self.email
        userEmailHash = self.email_hash
        message = mail.EmailMessage(sender="Trinity Tutor Support <trinitytutortt@gmail.com>", subject = "Verify your account")
        message.to = self.email
        bodyContent = """
        Dear %s,
        Your Trinity Tutor account has been approved. <br>
        Click here to verify your account. <br>
        http://www.trinity-tutor.appspot.com/confirmation/%s <br>
        Your Trinity Tutor account has been approved. <br>
        Click here to verify your account. http://www.trinity-tutor.appspot.com/confirmation/%s <br>
        Please let us know if you have any questions. <br>
        The Trinity Tutor Team
        """
        message.body = bodyContent % (userName, userEmailHash, userEmailHash)
        emailContent = """
        <html><head></head><body>
        Dear %s, <br><br>
        Your Trinity Tutor account has been approved. <br>
        Please let us know if you have any questions.<br>
        <a href="http://www.trinity-tutor.appspot.com/confirmation/%s">Click here to verify your account.</a><br>
        If the link does not automatically take you to the correct page, please copy and paste this link into your address bar: <br>
        http://www.trinity-tutor.appspot.com/confirmation/%s
        <br><br>
        Best, <br>
        The Trinity Tutor Team
        </body></html>
        """
        message.html = emailContent % (userName, userEmailHash, userEmailHash)
        message.send()

    def calculateTutorRating(self, newRating):
        user = self
        oldRating = user.numberTutorJobs * user.tutorRating
        user.numberTutorJobs = user.numberTutorJobs + 1
        user.tutorRating = (oldRating + newRating) / user.numberTutorJobs
        user.put()

    def calculateTuteeRating(self, newRating):
        user = self
        oldRating = user.numberTuteeJobs * user.tuteeRating
        user.numberTuteeJobs = user.numberTuteeJobs + 1
        user.tuteeRating = (oldRating + newRating) / user.numberTuteeJobs
        user.put()

    def deleteSameName(self):
        userID = self.key().id()
        userName = self.name
        users = User.all().filter('name =', userName)
        for user in users:
            if user.key().id() != userID:
                user.delete()

    def deleteSameEmail(self):
        userID = self.key().id()
        userEmail = self.email
        users = User.all().filter('email =', userEmail)
        for user in users:
            if user.key().id() != userID:
                user.delete()

    def render(self):
        # self._render_text = self.content.replace('\n', '<br>')
        return render_str("users.html", user = self)

    def renderRespondent(self):
        return render_str("singleRespondent.html", user = self)

    def renderCreated(self):
        createdList = self.createdList
        createdText = ""
        for postID in createdList:
            post = Post.by_id(int(postID))
            if post:
                createdText += post.render()
        return createdText

    def createFeedback(self):
        feedbackList = self.feedbackList
        feedbackText = ""
        for feedbackID in feedbackList:
            feedback = Feedback.by_id(int(feedbackID))
            if feedback:
                feedbackText += feedback.render()
        return feedbackText

    def renderApplied(self):
        appliedList = self.appliedList
        appliedText = ""
        for postID in appliedList:
            post = Post.by_id(int(postID))
            if post:
                appliedText += post.render()
        return appliedText


def _key(name = 'default'):
    return db.Key.from_path('s', name)

#Object for Post database
class Post(db.Model):
    title = db.StringProperty(required = True)
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    wage = db.FloatProperty(required = True)
    meetings = db.IntegerProperty(required = True)
    difficulty = db.IntegerProperty(required = True)
    author = db.StringProperty(required = True)
    authorID = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)
    #+datetime.timedelta(hours=8)
    selectedTutor = db.StringProperty()
    selectedTutorID = db.StringProperty()
    feedbackOnTutee = db.BooleanProperty()
    feedbackOnTutor = db.BooleanProperty()

    respondentNameList = db.ListProperty(str, indexed = True, default=[])
    respondentIDList = db.ListProperty(str, indexed = True, default=[])
    commentIDList = db.ListProperty(str, indexed = True, default=[])

    @classmethod
    def by_id(cls, uid):
        return Post.get_by_id(uid, parent = _key())

    def render(self):
        #self._render_text = self.content.replace('\n', '<br>')
        owner = User.by_id(int(self.authorID))
        return render_str("post.html", post = self, owner = owner)

    def createComments(self):
        commentIDList = self.commentIDList
        commentText = ""
        for commentID in commentIDList:
            comment = Comment.by_id(int(commentID))
            if comment:
                commentText += comment.render()
        return commentText

    def createRepondents(self):
        respondentIDList = self.respondentIDList
        respondentText = ""
        for respondentID in respondentIDList:
            respondent = User.by_id(int(respondentID))
            if respondent:
                respondentText += respondent.renderRespondent()
        return respondentText

    def render_page(self, error_comment):
        self._render_text = self.content.replace('\n', '<br>')
        #print self.created.now()-datetime.timedelta(hours=5)
        owner = User.by_id(int(self.authorID))
        return render_str("single-post.html", post = self, commentText = self.createComments(), respondentText = self.createRepondents(), owner = owner, error_comment = error_comment)

    def render_ownerPage(self, error_comment = ""):
        self._render_text = self.content.replace('\n', '<br>')
        #print self.created.now()-datetime.timedelta(hours=5)
        owner = User.by_id(int(self.authorID))

        return render_str("owner-single-post.html", post = self, respondentNameList = self.respondentNameList, commentText = self.createComments(), respondentText = self.createRepondents(), owner = owner, error_comment = error_comment)

    def sendConnectionEmail(self, receiver, sender, postID):
        receiverName = receiver.nickname
        receiverEmail = receiver.email
        senderUsername = sender.name
        senderEmail = sender.email

        message = mail.EmailMessage(sender="Trinity Tutor Support <trinitytutortt@gmail.com>", subject="Connection Made on Trinity Tutor")
        message.to = receiverEmail
        emailPlainContent = """
        Dear %s,
        %s has connected with you on Trinity Tutor.
        The original posting can be found here <http://www.trinity-tutor.appspot.com/post/%s>
        Please contact %s at %s.
        Best,
        The Trinity Tutor Team
        """
        message.body = emailPlainContent % (receiverName, senderUsername, postID, senderUsername, senderEmail)
        emailHTMLContent = """
        <html><head></head><body>
        Dear %s, <br><br>
        %s has connected with you on Trinity Tutor.<br>
        The original posting can be found <a href="http://www.trinity-tutor.appspot.com/post/%s">here</a>.<br>
        If the link does not automatically take you to the correct page, please copy and paste this link into your address bar: <br>
        http://www.trinity-tutor.appspot.com/post/%s <br>
        Please contact %s at %s.<br><br>
        Best, <br>
        The Trinity Tutor Team
        </body></html>
        """
        message.html = emailHTMLContent % (receiverName, senderUsername, postID, postID, senderUsername, senderEmail)
        message.send()

    def exchangeContact(self, user):
        selectedTutor = User.by_name(self.selectedTutor)
        selectedTutorID = selectedTutor.key().id()
        userID = user.key().id()
        postID = str(self.key().id())
        firstConnection = Connection(parent = connections_key(), otherUserID = str(selectedTutorID), postID = postID)
        firstConnection.put()
        user.connectionList.append(str(firstConnection.key().id()))
        user.put()
        secondConnection = Connection(parent = connections_key(), otherUserID = str(userID), postID = postID)
        secondConnection.put()
        selectedTutor.connectionList.append(str(secondConnection.key().id()))
        selectedTutor.put()

        self.sendConnectionEmail(selectedTutor, user, postID)
        self.sendConnectionEmail(user, selectedTutor, postID)

def feedbacks_key(group = 'default'):
    return db.Key.from_path('feedbacks', group)

class Feedback(db.Model):
    receiverID = db.StringProperty(required = True)
    writerID = db.StringProperty(required = True)
    postID = db.StringProperty(required = True)
    rating = db.IntegerProperty(required = True)
    comment = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_id(cls, fid):
        return Feedback.get_by_id(fid, parent = feedbacks_key())

    def render(self):
        return render_str("singleFeedback.html", feedback = self, receiver = User.by_id(int(self.receiverID)), writer = User.by_id(int(self.writerID)), post = Post.by_id(int(self.postID)))

def comments_key(group = 'default'):
    return db.Key.from_path('comments', group)

class Comment(db.Model):
    content = db.TextProperty(required = True)
    author = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_id(cls, cid):
        return Comment.get_by_id(cid, parent = comments_key())

    def render(self):
        return render_str("singleComment.html", comment = self)

def connections_key(group = 'default'):
    return db.Key.from_path('connections', group)

class Connection(db.Model):
    otherUserID = db.StringProperty(required = True)
    postID = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_id(cls, cid):
        return Connection.get_by_id(cid, parent = connections_key())

    def render(self):
        return render_str("singleConnection.html", connection = self, user = User.by_id(int(self.otherUserID)), post = Post.by_id(int(self.postID)))

class Created(Handler):
    def get(self):
        if self.user:
            createdText = self.user.renderCreated()
            self.render("createdPosts.html", createdText = createdText)
        else:
            self.redirect('/login')

class Applied(Handler):
    def get(self):
        if self.user:
            appliedText = self.user.renderApplied()
            self.render("appliedPosts.html", appliedText = appliedText)
        else:
            self.redirect('/login')

class Front(Handler):
    def weekAgo(self):
        return datetime.now() - timedelta(seconds = (7 * 24 * 60 * 60))

    def get(self):
        # posts = Post.all().filter("created >", self.weekAgo()).order('-created')
        posts = Post.all().order('-created')
        self.render('front.html', posts = posts)

    def post(self):
        subject = self.request.get('subjectTag')
        sorting = self.request.get('sortingTag')
        if (sorting != 'None') and (subject != 'None'):
            posts = Post.all().filter('subject =', subject).order('-%s' % sorting)

        if (subject == 'None') and (sorting == 'None'):
            posts = Post.all().order('-created')
        
        elif subject == 'None':
            posts = Post.all().order('-%s' % sorting)

        elif sorting == 'None':
            posts = Post.all().filter('subject =', subject).order('-created')

        self.render('front.html', posts = posts, subjectTag = subject, sortingTag = sorting)    

class ShowAllUsers(Handler):
    def get(self):
        if self.user:
            users = User.all().order('-created')
            self.render("loadAllUsers.html", users = users)
        else:
            self.redirect('/login')

class ConnectionRedirect(Handler):
    def get(self):
        if self.user:
            self.redirect('connections/%s' % str(self.user.key().id()))
        else:
            self.redirect('/login')

class MyProfile(Handler):
    def get(self):
        if self.user:
            self.redirect('users/%s' % str(self.user.key().id()))
        else:
            self.redirect('/login')

class ConnectionsPage(Handler):
    def createConnections(self, user):
        connectionList = user.connectionList
        connectionText = ""
        for connectionID in connectionList:
            connection = Connection.by_id(int(connectionID))
            if connection:
                connectionText += connection.render()
        return connectionText

    def get(self, user_id):
        if self.user:
            if self.user.key().id() == int(user_id):
                user = User.by_id(int(user_id))
                self.render("connections.html", user = user, connectionText = self.createConnections(user))
            else:
                self.redirect('/connections')
        else:
            self.redirect('/login')

class FeedbackPage(Handler):
    def get(self, post_id):
        if self.user:
            post = Post.by_id(int(post_id))
            if post.selectedTutor:
                if self.user.key().id() == int(post.selectedTutorID):
                    if post.feedbackOnTutee:
                        #You already gave feedback
                        self.render('popup.html', message = "You have already given feedback on this Post!")
                        self.redirect('/post/%s' % str(post_id))
                    else:
                        self.render("submitFeedback.html", post = post)
                elif self.user.key().id() == int(post.authorID):
                    if post.feedbackOnTutor:
                        #You already gave feedback
                        self.render('popup.html', message = "You have already given feedback on this Post!")
                        self.redirect('/post/%s' % str(post_id))
                    else:
                        self.render("submitFeedback.html", post = post)
                else:
                    #you do not have permission to leave feedback
                    self.render('popup.html', message = "You do not have permission to leave feedback on this Post!")
                    self.redirect('/post/%s' % str(post_id))
            else:
                #no feedback can be given until a tutor has been selected
                self.render('popup.html', message = "No feedback can be given until a Tutor has been selected!")
                self.redirect('/post/%s' % str(post_id))
        else:
            self.redirect('login')

    def post(self, post_id):
        if self.user:
            post = Post.by_id(int(post_id))
            rating = self.request.get('rating')
            ratingVerify = True
            error_rating = ""
            if not (rating.isdigit()):
                error_rating = "Your rating value is invalid"
                ratingVerify = False
            elif ((int(rating) < 1) or (int(rating) > 5)):
                error_rating = "Your rating value is invalid"
                ratingVerify = False
            comment = self.request.get('comment')
            if rating and ratingVerify:
                if self.user.name == post.author:
                    f = Feedback(parent = feedbacks_key(), receiverID = post.selectedTutorID, writerID = str(self.user.key().id()), postID = str(post_id), rating = int(rating), comment = comment)
                    f.put()
                    user = User.by_id(int(post.selectedTutorID))
                    user.feedbackList.append(str(f.key().id()))
                    user.put()
                    user.calculateTutorRating(int(rating))
                    post.feedbackOnTutor = True
                    post.put()
                elif self.user.name == post.selectedTutor:
                    f = Feedback(parent = feedbacks_key(), receiverID = post.authorID, writerID = post.selectedTutorID, postID = str(post_id), rating = int(rating), comment = comment)
                    f.put()
                    user = User.by_id(int(post.authorID))
                    user.feedbackList.append(str(f.key().id()))
                    user.put()
                    user.calculateTuteeRating(int(rating))
                    post.feedbackOnTutee = True
                    post.put()
                else:
                    self.render('popup.html', message = "You don't have permission to give feedback on this Post!")
                self.redirect('/post/%s' % str(post_id))
            else:
                self.render("submitFeedback.html", post = post, error_rating = error_rating)
        else:
            self.redirect('login')

class PostPage(Handler):
    def get(self, post_id):
        post = Post.by_id(int(post_id))
        if not post:
            self.error(404)
            #error
            print "ERROR"
            self.redirect('/')
        else:   
            if self.user:
                if post.selectedTutor:
                    if ((self.user.name == post.selectedTutor) or (self.user.name == post.author)):
                        owner = User.by_id(int(post.authorID))
                        self.render("feedbackOption.html", post = post, owner = owner, commentText = post.createComments())
                    else:
                        self.render("permalink.html", post = post)
                elif self.user.name == post.author:
                    self.render("ownerPermalink.html", post = post)
                else:
                    self.render("permalink.html", post = post)
            else:
                self.redirect("/login")

    def post(self, post_id):
        if not self.user:
            self.redirect('/login')
        else:
            post = Post.by_id(int(post_id))
            if post:
                isApply = self.request.get('apply')
                isSelect = self.request.get('select')

                if isSelect:
                    selected = self.request.get('selectList')
                    if selected:
                        post.selectedTutor = selected
                        post.selectedTutorID = str(User.by_name(selected).key().id())
                        post.put()
                        post.exchangeContact(self.user)
                        self.redirect('/connections')
                    else:
                        self.redirect('/post/%s' % str(post_id))
                elif isApply:
                    respondent = self.user.name
                    alreadyAppliedFlag = False
                    for name in post.respondentNameList:
                        if name == respondent:
                            alreadyAppliedFlag = True
                    if ((alreadyAppliedFlag) or (self.user.name == post.author)):
                        #you already applied to this post/you created this post
                        self.render('popup.html', message = "You cannot apply for this Post!")
                        self.redirect('/post/%s' % post_id)
                    else:
                        post.respondentNameList.append(respondent)
                        post.respondentIDList.append(str(self.user.key().id()))
                        post.put()
                        self.user.appliedList.append(str(post.key().id()))
                        self.user.put()
                        self.redirect('/post/%s' % post_id)
                else:
                    content = self.request.get('content').replace('\n', '<br>')
                    if not post:
                        self.error(404)
                        self.redirect('/post/%s' % str(post_id))
                    else:
                        if content:
                            created = datetime.now() - timedelta(hours=5)
                            comment = Comment(parent = comments_key(), created = created, content = content, author = self.user.name)
                            comment.put()
                            post.commentIDList.append(str(comment.key().id()))
                            post.put()
                            self.redirect('/post/%s' % str(post_id))
                        else:
                            #no content entered
                            error_comment = "No content was entered!"
                            if (self.user.name == post.author):
                                self.render("ownerPermalink.html", post = post, error_comment = error_comment)
                            else:
                                self.render("permalink.html", post = post, error_comment = error_comment)
            else:
                self.error(404)
                #error
                print "ERROR"
                self.redirect('/')

class EditPost(Handler):
    def get(self, post_id):
        post = Post.by_id(int(post_id))
        if not post:
            self.error(404)
            #error
            print "ERROR"
            self.redirect('/')  
        else:   
            if self.user:
                if post.selectedTutor:
                    if ((self.user.name == post.author) or (self.user.name == post.selectedTutor)):
                        owner = User.by_id(int(post.authorID))
                        self.render("feedbackOption.html", post = post, owner = owner, commentText = post.createComments())
                    else:
                        self.render("permalink.html", post = post)
                elif self.user.name == post.author:
                    self.render("editPost.html", post = post)
                else:
                    self.render("permalink.html", post = post)
            else:
                self.redirect("/login")

    def post(self, post_id):
        post = Post.by_id(int(post_id))
        if not post:
            self.error(404)
            #error
            print "ERROR"
            self.redirect('/')
        else:
            if self.user:
                if not post.selectedTutor:
                    if (self.user.key().id() == int(post.authorID)):
                        title = self.request.get('title')
                        subject = self.request.get('subjectList')
                        content = self.request.get('content')
                        meetings = self.request.get('meetingsList')
                        difficulty = self.request.get('difficultyList')
                        wage = self.request.get('wage')
                        wageVerify = True
                        meetingsVerify = True
                        difficultyVerify = True
                        error_meetings = None
                        error_difficulty = None

                        try:
                            float(wage)
                            wageVerify = True
                        except ValueError:
                            wageVerify = False
                        if not (meetings.isdigit()):
                            error_meetings = "Your meetings value is invalid."
                            meetingsVerify = False
                        elif ((int(meetings) < 1) or (int(meetings) > 3)):
                            print meetings
                            error_meetings = "Your meetings value is invalid."
                            meetingsVerify = False

                        if not (difficulty.isdigit()):
                            error_difficulty = "Your difficulty value is invalid."
                            difficultyVerify = False
                        elif ((int(meetings) > 1) and (int(meetings) < 4)):
                            print "ASDASD"
                            print difficulty
                            error_difficulty = "Your difficulty value is invalid."
                            difficultyVerify = False

                        if title and subject and content and wageVerify and meetingsVerify and difficultyVerify:
                            post.title = title
                            post.subject = subject
                            post.content = content
                            post.wage = float(wage)
                            post.meetings = int(meetings)
                            post.difficulty = int(difficulty)
                            post.put()
                            self.redirect('/post/%s' % post_id)
                        else:
                            error = "Enter information in the required fields! Some of your information may have been reset to default values!"
                            self.render("editPost.html", title = title, subject = subject, content = content, wage = wage, error_meetings = error_meetings, error_difficulty = error_difficulty)
                    else:
                        self.redirect('/post/%s' % post_id)
                else:
                    self.redirect('/post/%s' % post_id)
            else:
                self.redirect('/login')

class DeletePost(Handler):
    def get(self, post_id):
        post = Post.by_id(int(post_id))
        if not post:
            self.error(404)
            #error
            print "ERROR"
            self.redirect('/myaccount')
        else:   
            if self.user:
                if not post.selectedTutor:
                    if (self.user.key().id() == int(post.authorID)):
                        owner = User.by_id(int(post.authorID))
                        self.render("deletePost.html", post = post, owner = owner)
                    else:
                        self.render("permalink.html", post = post)
                else:
                    #You have already selected someone so you can't change delete this post
                    self.redirect('/post/%s' % post_id)
            else:
                self.redirect("/login")

    def post(self, post_id):
        post = Post.by_id(int(post_id))
        if not post:
            self.error(404)
            #error
            print "ERROR"
            self.redirect('/myaccount')
        else:   
            if self.user:
                if not post.selectedTutor:
                    if (self.user.key().id() == int(post.authorID)):
                        post.delete()
                        self.redirect('/myaccount')
                    else:
                        self.render("permalink.html", post = post)
                else:
                    #You have already selected someone so you can't change delete this post
                    self.redirect('/post/%s' % post_id)
            else:
                self.redirect("/login")

class NewPost(Handler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if self.user:
            title = self.request.get('title')
            subject = self.request.get('subjectList')
            content = self.request.get('content')
            meetings = self.request.get('meetingsList')
            difficulty = self.request.get('difficultyList')
            wage = self.request.get('wage')
            wageVerify = True
            meetingsVerify = True
            difficultyVerify = True
            error_meetings = ""
            error_difficulty = ""
            try:
                float(wage)
                wageVerify = True
            except ValueError:
                wageVerify = False
            if not (meetings.isdigit()):
                error_meetings = "Your meetings value is invalid."
                meetingsVerify = False
            elif ((int(meetings) < 1) or (int(meetings) > 3)):
                error_meetings = "Your meetings value is invalid."
                meetingsVerify = False

            if not (difficulty.isdigit()):
                error_difficulty = "Your difficulty value is invalid."
                difficultyVerify = False
            elif ((int(meetings) < 1) or (int(meetings) > 4)):
                error_difficulty = "Your difficulty value is invalid."
                difficultyVerify = False

            if title and subject and content and wageVerify and meetingsVerify and difficultyVerify:
                post = Post(parent = _key(), title = title, subject = subject, content = content, wage = float(wage), meetings = int(meetings), difficulty = int(difficulty), author = self.user.name, authorID = str(self.user.key().id()))
                post.put()

                self.user.createdList.append(str(post.key().id()))
                self.user.put()

                self.redirect('/post/%s' % str(post.key().id()))
            else:
                error = "Enter information in the required fields! Some of your information may have been reset to default values!"
                self.render("newpost.html", title = title, subject = subject, content = content, wage = wage, error_meetings = error_meetings, error_difficulty = error_difficulty, error = error)
        else:
            self.redirect('/login')

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return email and EMAIL_RE.match(email)

class Register(Handler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        have_email_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        if '@' not in self.request.get('email'):
            self.email = self.request.get('email')+'@trincoll.edu'
        else: 
            self.email = self.request.get('email')
            have_email_error = True
        self.email_hash = make_email_hash(self.email)
        self.name = self.request.get('name')
        self.year = self.request.get('year')
        self.major = self.request.get('major')
        self.description = self.request.get('description')
        params = dict(username = self.username,
                      email = self.request.get('email'),
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
        elif not (self.year.isdigit()):
            params['error_year'] = "Your class year must be an integer."
            have_error = True
        elif ((int(self.year) < 2014) or (int(self.year) > 2020)):
            params['error_year'] = "Your class year must be an integer between 2014 and 2020."
            have_error = True
        if (not valid_email(self.email)) or have_email_error:
            params['error_email'] = "That's not a valid email."
            have_error = True
        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done(**params)

    def done(self, **params):
        userCheck = User.all().filter('name = ', self.username)
        emailCheck = User.all().filter('email =', self.email)
        registeredFlag = False
        if userCheck:
            for each in userCheck:
                if each.confirmed:
                    registeredFlag = True
            if registeredFlag:
                userMessage = 'That user already exists.'
                self.render('signup-form.html', error_username = userMessage, **params)
            elif emailCheck:
                for each in emailCheck:
                    if each.confirmed:
                        registeredFlag = True
                if registeredFlag:
                    emailMessage = "That email is already registered with Trinity Tutor."
                    self.render('signup-form.html', error_email = emailMessage, **params)
                else:
                    user = User.register(self.username.lower(), self.password, self.email.lower(), self.name, self.year, self.major, self.description)
                    user.put()
                    user.sendVerificationEmail()
                    self.render('popup.html', message = "Please check your email for a verification link")
                    self.redirect('/')
            else:
                user = User.register(self.username.lower(), self.password, self.email.lower(), self.name, self.year, self.major, self.description)
                user.put()
                user.sendVerificationEmail()
                self.render('popup.html', message = "Please check your email for a verification link")
                self.redirect('/')
        elif emailCheck:
            for each in emailCheck:
                if each.confirmed:
                    registeredFlag = True
            if registeredFlag:
                emailMessage = "That email is already registered with Trinity Tutor."
                self.render('signup-form.html', error_email = emailMessage, **params)
            elif userCheck:
                for each in userCheck:
                    if each.confirmed:
                        registeredFlag = True
                if registeredFlag:
                    userMessage = 'That user already exists.'
                    self.render('signup-form.html', error_username = userMessage, **params)
                else:
                    user = User.register(self.username.lower(), self.password, self.email.lower(), self.name, self.year, self.major, self.description)
                    user.put()
                    user.sendVerificationEmail()
                    self.render('popup.html', message = "Please check your email for a verification link")
                    self.redirect('/')
            else:
                user = User.register(self.username.lower(), self.password, self.email.lower(), self.name, self.year, self.major, self.description)
                user.put()
                user.sendVerificationEmail()
                self.render('popup.html', message = "Please check your email for a verification link")
                self.redirect('/')
        else:
            user = User.register(self.username.lower(), self.password, self.email.lower(), self.name, self.year, self.major, self.description)
            user.put()
            user.sendVerificationEmail()
            self.render('popup.html', message = "Please check your email for a verification link")
            self.redirect('/')

class Profile(Handler):
    def get(self, user_id):
        user = User.by_id(int(user_id))
        if not self.user:
            self.redirect("/login")
        else:
            ownerFlag = False
            if self.user.name == user.name:
                ownerFlag = True
            print self
            self.render("profile.html", u = user, username = user.name, feedbacks = user.createFeedback(), ownerFlag = ownerFlag)

class EditProfile(Handler):
    def get(self):
        user = User.by_name(self.user.name)
        if not self.user:
            self.redirect("/login")
        else:
            self.render("editableProfile.html", user = user)

    def post(self):
        user = User.by_name(self.user.name)
        if not self.user:
            self.redirect("/login")
        else:
            have_error = False
            self.username = user.name
            self.password = self.request.get('password')
            self.verify = self.request.get('verify')
            self.name = self.request.get('name')
            self.year = self.request.get('year')
            self.major = self.request.get('major')
            self.id = user.key().id()
            self.description = self.request.get('description')

            params = dict(username = self.username,
                          name = self.name,
                          year = self.year,
                          major = self.major,
                          description = self.description,
                          u = user)

            if not valid_password(self.password):
                params['error_password'] = "Password has to be at least 3 character/numbers"
                have_error = True
                
            elif self.password != self.verify:
                params['error_verify'] = "Your passwords didn't match."
                have_error = True

            elif not (self.year.isdigit()):
                params['error_year'] = "Your class year must be an integer."
                have_error = True

            elif ((int(self.year) < 2014) or (int(self.year) > 2020)):
                params['error_year'] = "Your class year must be an integer between 2014 and 2020."
                have_error = True

            if have_error:
                self.render('editableProfile.html', **params)

            else:
                self.done(**params)

    def done(self, **params):
        user = User.by_id(int(self.id))
        user.password = self.password
        pw_hash = make_pw_hash(user.name, user.password)
        user.pw_hash = pw_hash
        user.nickname = self.name
        user.year = int(self.year)
        user.major = self.major
        user.description = self.description
        user.put()
        self.redirect('/users/%s' % user.key().id())

class Login(Handler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username').lower()
        verifyCheckUser = User.by_name(username)
        if verifyCheckUser:
            password = self.request.get('password')
            u = User.login(username, password)
            if u and verifyCheckUser.confirmed:
                self.login(u)
                self.redirect('/')
            else:
                if u and not verifyCheckUser.confirmed:
                    message = 'This account has not been verified with Trinity Tutor. Please check your email for a verification link.'
                else:
                    message = 'Either Username OR password invalid!'
                self.render('login-form.html', error = message)
        else:
            message = 'Username "%s" not registered with Trinity Tutor.' % self.request.get('username')
            self.render('login-form.html', error = message)


class Logout(Handler):
    def get(self):
        self.logout()
        self.redirect('/')

class ConfirmPage(Handler):
    def get(self, email_hash):
        registeredFlag = False
        user = User.all().filter('email_hash =', email_hash).order('-created').get()
        userEmailCheck = User.all().filter('email =', user.email).order('-created')
        userNames = User.all().filter('name =', user.name)
        if user:
            if not user.confirmed:
                if userNames:
                    for each in userNames:
                        if each.confirmed:
                            registeredFlag = True
                    if registeredFlag:
                        #throw error because username has already been registered
                        print "username has already been registered with TT"
                        self.redirect('/')
                    elif userEmailCheck:
                        print "check above"
                        for each in userEmailCheck:
                            print each.key().id()
                            if each.confirmed:
                                registeredFlag = True
                        if registeredFlag:
                            #throw error because email has already been registered
                            print "email has already been registered with TT"
                            self.redirect('/')
                        else:
                            self.render("confirmationPage.html", userName = user.name, userConfirmed = user.confirmed, userEmail = user.email)
                else:
                    self.render("confirmationPage.html", userName = user.name, userConfirmed = user.confirmed, userEmail = user.email)
            else:
                self.render("confirmationPage.html", userName = user.name, userConfirmed = user.confirmed, userEmail = user.email)
        else:
            print "no such user exists"
            self.redirect('/')

    def post(self, email_hash):
        registeredFlag = False
        user = User.all().filter('email_hash =', email_hash).order('-created').get()
        userEmailCheck = User.all().filter('email =', user.email).order('-created')
        userNames = User.all().filter('name =', user.name)
        if user:
            if not user.confirmed:
                if userNames:
                    for each in userNames:
                        if each.confirmed:
                            registeredFlag = True
                    if registeredFlag:
                        #throw error because username has already been registered
                        print "username has already been registered with TT"
                        self.redirect('/')
                    elif userEmailCheck:
                        for each in userEmailCheck:
                            if each.confirmed:
                                registeredFlag = True
                        if registeredFlag:
                            #throw error because email has already been registered
                            print "email has already been registered with TT"
                            self.redirect('/')
                        else:
                            user.confirmed = True
                            user.put()
                            user.deleteSameEmail()
                            user.deleteSameName()
                            self.render('popup.html', message = "Your account has been verified. Please login!")
                            self.redirect('/login')
                else:
                    user.confirmed = True
                    user.put()
                    user.deleteSameEmail()
                    user.deleteSameName()
                    self.render('popup.html', message = "Your account has been verified. Please login!")
                    self.redirect('/login')
            else:
                user.confirmed = True
                user.put()
                user.deleteSameEmail()
                user.deleteSameName()
                self.render('popup.html', message = "Your account has been verified. Please login!")
                self.redirect('/login')
        else:
            print "no such user exists"
            self.redirect('/')

class FAQ(Handler):
    def get(self):
        self.render("faq.html")

class CronTask(Handler):
    def weekAgo(self):
        return datetime.now() - timedelta(seconds = (7 * 24 * 60 * 60))

    def dayAgo(self):
        return datetime.now() - timedelta(seconds = (24 * 60 * 60))

    def get(self):
        posts = Post.all().order('-created')
        for post in posts:
            if not post.selectedTutor:
                if post.created < self.weekAgo():
                    post.delete()
        users = User.all().order('-created')
        for user in users:
            if not user.confirmed:
                if user.created < self.dayAgo():
                    user.delete()


app = webapp2.WSGIApplication([('/', Front),
                               ('/post/([0-9]+)(?:.json)?', PostPage),
                               ('/editpost/([0-9]+)(?:.json)?', EditPost),
                               ('/deletepost/([0-9]+)(?:.json)?', DeletePost),
                               ('/feedback/([0-9]+)(?:.json)?', FeedbackPage),
                               ('/confirmation/([a-zA-Z0-9]+)', ConfirmPage),
                               ('/crontask', CronTask),
                               ('/newpost', NewPost),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/myaccount', MyProfile),
                               ('/editmyaccount', EditProfile),
                               ('/created', Created),
                               ('/applied', Applied),
                               ('/users', ShowAllUsers),
                               ('/connections', ConnectionRedirect),
                               ('/connections/([0-9]+)(?:.json)?', ConnectionsPage),
                               ('/users/([0-9]+)(?:.json)?', Profile),
                               ('/FAQ', FAQ),
                               ],
                              debug=True)
