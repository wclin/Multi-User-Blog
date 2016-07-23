#!/usr/bin/env python
import os
import json
import jinja2
import webapp2
import urllib
from libs.bcrypt import bcrypt
import logging as log
import time

from google.appengine.ext import db

SECRET = open("secret.txt", "r").readline()

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def make_pw_hash(name, pwd):
    return bcrypt.hashpw(name + pwd + SECRET, bcrypt.gensalt())


def valid_pw(name, pwd, hashed):
    return bcrypt.hashpw(name + pwd + SECRET, hashed) == hashed


def blog_key(name='default'):
    return db.Key.from_path('blogs', name)


class Alert():
    """A simple class represent bootstrap alert.

    Attributes:
        category (str): corresponding to 4 bootstrap alert class:
            ['alert-success', 'alert-info', 'alert-warning', 'alert-danger']
        message (str): The string shows on alert.

    """
    @classmethod
    def dict(cls, d):
        a = cls()
        a.category = d['category']
        a.message = d['message']
        return a

    @classmethod  # Or maybe __init__ is fine
    def set(cls, category, message):
        a = cls()
        a.category = category
        a.message = message
        return a


class Author(db.Model):
    """A simple author entity.

    Attributes:
        name (StringProperty(required=True)): The name of author, which is unique.
        pwdh (StringProperty(required=True)): The bcrypt hash of password.
        email (StringProperty): The email of author.
        dscr (TextProperty): The description of author will show on sidebar.

    """
    name = db.StringProperty(required=True)
    pwdh = db.StringProperty(required=True)
    email = db.StringProperty()
    dscr = db.TextProperty()


class Post(db.Model):
    """A simple post entity.

    Attributes:
        author (ReferenceProperty(Author)): Every post belongs to one user.
        title (StringProperty): The title of post.
        content (TextProperty): The content of post. Support html format.
        created (DateTimeProperty(auto_now_atdd=True)): The time of post created.
        likes (IntegerProperty(default=0)): The number of likes of post. For every post, the user can only like once.
        isLiked (BooleanProperty): Which is used to control Like/Unlike.
    """
    author = db.ReferenceProperty(Author)
    title = db.StringProperty()
    content = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    likes = db.IntegerProperty(default=0)
    isLiked = db.BooleanProperty()

    def render(self, template_values):
        self._render_text = self.content.replace('\n', '<br>')
        template = JINJA_ENVIRONMENT.get_template('post.html')
        return template.render(template_values)


class Comment(db.Model):
    """A simple comment entity.

    Attributes:
        author (ReferenceProperty(Author)): Every comment belongs to one user.
        post (ReferenceProperty(Post)): Every comment belongs to one post.
        content (TextProperty): The content of comment. Support html format.
        created (DateTimeProperty(auto_now_atdd=True)): The time of comment created.
     """
    author = db.ReferenceProperty(Author)
    post = db.ReferenceProperty(Post)
    content = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add=True)


class Likes(db.Model):
    """An entity in order to represent the many-to-many relation about the preference of users about posts. The existence of the instance(user:u, post:p), indicate u like p.

    Attributes:
        user (ReferenceProperty(Author)
        post (ReferenceProperty(Post))
    """
    user = db.ReferenceProperty(Author)
    post = db.ReferenceProperty(Post)


class Handler(webapp2.RequestHandler):

    def __init__(self, request, response):
        self.initialize(request, response)

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return (JINJA_ENVIRONMENT.get_template(template)).render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def getName(self):
        """
        Return valid Author.name if cookies are valid, else return None
        """
        user = self.getUser()
        return user.name if user else None

    def getUser(self):
        """
        Return valid Author object if cookies are valid, else return None
        """
        cookie = self.request.cookies.get('uname')
        uname, token = cookie.split('|') if cookie else ('', None)
        uname = uname if uname != '' and valid_pw(uname, '', token) else None
        return Author.get_by_key_name(uname) if uname else None

    def setName(self, user=None):
        """
        Set a valid cookie from Author object
        """
        if user:
            token = make_pw_hash(str(user.name), '')
            self.response.headers.add_header(
                'Set-Cookie', 'uname=%s|%s' % (str(user.name), token))
        else:
            self.response.headers.add_header('Set-Cookie', 'uname=%s' % '|')

    def getAlert(self):
        """
        Return an Alert object from url request info: message and categor
        """
        message = self.request.get('message')
        category = self.request.get('category')
        return Alert.set(category, message)

    def getPost(self):
        """
        Return an Post object from url request info: post_id
        """
        post_id = self.request.get("post_id")
        key = db.Key.from_path("Post", int(post_id), parent=blog_key())
        return db.get(key)

    def getComment(self):
        """
    
        """
        comment_id = self.request.get("comment_id")
        key = db.Key.from_path("Comment", int(comment_id))
        return db.get(key)

    def redirectJson(self, url, a):
        """
        Redirect by return json obj.
        """
        self.response.headers['Content-Type'] = 'application/json'
        obj = {'redirect': '%s?%s' % (url, urllib.urlencode(a))}
        self.response.out.write(json.dumps(obj))

    def isLiked(self, p):
        """
        Return if the given post is liked by this user before.
        """
        u = self.getUser()
        return Likes.all().filter('user =', u).filter('post =', p).get() and u


class MainPage(Handler):
    """
    The page show posts of current user.
    """

    def get(self):
        author = self.getUser()
        if author:
            template_values = {
                'author': author,
                'user': self.getName(),
                'alert': self.getAlert(),
                'posts': Post.all().filter(
                    'author =',
                    author).order('-created')}
            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))
            # self.render("index.html", template_values) can't work
        else:
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-warning",
                message="Login before action!")))


class Timeline(Handler):
    """
    The page show posts of every user.
    """

    def get(self):
        posts = Post.all().order('-created').fetch(limit=100)
        for post in posts:
            post.isLiked = True if self.isLiked(post) else False
        template_values = {
            'user': self.getName(),
            'alert': self.getAlert(),
            'posts': posts
        }
        template = JINJA_ENVIRONMENT.get_template('timeline.html')
        self.response.write(template.render(template_values))


class Like(Handler):

    def get(self):
        u = self.getUser()
        if not u:
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-warning",
                message="Login before action!")))
            return
        p = self.getPost()
        if self.isLiked(p):
            self.redirect("/Timeline?%s" % urllib.urlencode(dict(
                category="alert-danger", message="Already liked!!")))
            return
        if u and u.name == p.author.name:
            self.redirect("/Timeline?%s" % urllib.urlencode(dict(
                category="alert-danger", message="You self-lover!")))
            return
        l = Likes(user=u, post=p)
        l.put()
        p.likes = p.likes + 1
        p.put()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirect("/Timeline?%s" % urllib.urlencode(dict(
            category="alert-success", message="Like!!")))


class UnLike(Handler):

    def get(self):
        p = self.getPost()
        if not self.isLiked(p):
            self.redirect("/Timeline?%s" % urllib.urlencode(dict(
                category="alert-danger", message="Didn't like yet!!")))
            return
        l = Likes.all().filter(
            'user =', self.getUser()).filter(
            'post =', p).get()
        l.delete()
        p.likes = p.likes - 1
        p.put()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirect("/Timeline?%s" % urllib.urlencode(dict(
            category="alert-success", message="UnLike!!")))


class PostPage(Handler):

    def get(self, post_id):
        key = db.Key.from_path("Post", int(post_id), parent=blog_key())
        post = db.get(key)
        template_values = {
            'user': self.getName(),
            'alert': self.getAlert(),
            'p': post,
            'post_id': post_id,
            'comments': Comment.all().filter('post =', post).order('-created')
        }
        self.render(
            "permalink.html",
            post=post,
            template_values=template_values)


class DeletePost(Handler):

    def get(self):
        p = self.getPost()
        if not self.getUser():
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-warning",
                message="Login before action!")))
            return
        if self.getName() != p.author.name:
            self.redirect("/%s?%s" %
                          (str(p.key().id()), urllib.urlencode(dict(
                              category="alert-danger",
                              message="It's not yours!"))))
            return
        p.delete()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirect("/Timeline?%s" % urllib.urlencode(dict(
            category="alert-success", message="Deleted!!")))


class EditPost(Handler):

    def post(self):
        if not self.getUser():
            self.redirectJson("/Login", dict(
                category="alert-warning", message="Login before action!"))
            return
        p = self.getPost()
        if self.getName() != p.author.name:
            self.redirectJson("/" + str(p.key().id()), dict(
                category="alert-danger", message="It's not yours!"))
            return
        p.title = self.request.get("title")
        p.content = self.request.get("content")
        p.put()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirectJson("/" + str(p.key().id()), dict(
            category="alert-success", message="check please~"))


class NewPost(Handler):

    def post(self):
        author = self.getUser()
        title = self.request.get("title")
        content = self.request.get("content")
        if not author:
            self.redirectJson("/Login", dict(
                category="alert-warning",
                message="Login before action!"))
            return
        p = Post(
            parent=blog_key(),
            author=author,
            title=title,
            content=content)
        p.put()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirectJson("/" + str(post.key().id()), dict(
            category="alert-success", message="Here~"))


class NewComment(Handler):

    def post(self):
        author = self.getUser()
        post = self.getPost()
        content = self.request.get("content")
        if not author:
            self.redirectJson("/Login", dict(
                category="alert-warning",
                message="Login before action!"))
            return
        c = Comment(
            author=author,
            post=post,
            content=content)
        c.put()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirectJson("/" + str(post.key().id()), dict(
            category="alert-success",
            message="Comment Success!"))


class EditComment(Handler):

    def post(self):
        if not self.getUser():
            self.redirectJson("/Login", dict(
                category="alert-warning",
                message="Login before action!"))
            return
        c = self.getComment()
        p = c.post
        if self.getName() != c.author.name:
            self.redirectJson("/" + str(p.key().id()), dict(
                category="alert-danger",
                message="It's not yours!"))
            return
        c.content = self.request.get("content")
        c.put()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirectJson("/" + str(p.key().id()), dict(
            category="alert-success",
            message="Comment Edit Success!"))


class DeleteComment(Handler):

    def get(self):
        if not self.getUser():
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-warning",
                message="Login before action!")))
            return
        c = self.getComment()
        p = c.post
        if self.getName() != c.author.name:
            self.redirect("/%s?%s" %
                          (str(p.key().id()), urllib.urlencode(dict(
                              category="alert-danger",
                              message="It's not yours!"))))
            return
        c.delete()
        # http://stackoverflow.com/questions/16879275/why-webapp2-redirect-to-a-page-but-its-not-reload
        time.sleep(0.1)
        self.redirect("/%s?%s" %
                      (str(p.key().id()), urllib.urlencode(dict(
                          category="alert-success",
                          message="Deleted!!"))))


class SignUp(Handler):

    def get(self):
        template_values = {
            'user': self.getName(),
            'alert': self.getAlert(),
        }
        template = JINJA_ENVIRONMENT.get_template('signup.html')
        self.response.write(template.render(template_values))

    def post(self):
        name = self.request.get("username").replace(' ', '')
        pwd = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")
        dscr = self.request.get("description")
        pwdh = make_pw_hash(name, pwd)
        a = Author.get_by_key_name(name)
        if not pwd or pwd != verify:
            alert = dict(
                category="alert-danger",
                message="Verification failed!")
            self.render(
                "signup.html",
                user=self.getName(),
                alert=alert,
                username=name,
                email=email,
                description=dscr)
            return
        if a:
            alert = dict(category="alert-danger", message="Duplicate!")
            self.render(
                "signup.html",
                user=self.getName(),
                alert=alert,
                username=name,
                email=email,
                description=dscr)
            return
        else:
            a = Author(
                key_name=name,
                name=name,
                pwdh=pwdh,
                email=email,
                dscr=dscr)
            a.put()
            self.setName(a)
            self.redirect("/Welcome")


class Login(Handler):

    def get(self):
        template_values = {
            'user': self.getName(),
            'alert': self.getAlert(),
        }
        template = JINJA_ENVIRONMENT.get_template('login.html')
        self.response.write(template.render(template_values))

    def post(self):
        name = self.request.get("username")
        pwd = self.request.get("password")
        u = Author.get_by_key_name(name) if name != '' else None
        if u and valid_pw(name, pwd, u.pwdh):
            self.setName(u)
            self.redirect("/Welcome")
        else:
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-warning", message="Try again~")))


class Logout(Handler):

    def get(self):
        if not self.getUser():
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-warning",
                message="Login before action!")))
            return
        self.setName()
        self.redirect("/Login?%s" % urllib.urlencode(dict(
            category="alert-success", message="Bye~")))


class Welcome(Handler):

    def get(self):
        if self.getName():
            self.redirect("/Timeline?%s" % urllib.urlencode(dict(
                category="alert-success", message="Welcome!")))
        else:
            self.redirect("/Login?%s" % urllib.urlencode(dict(
                category="alert-danger", message="Nooooo")))


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/Timeline', Timeline),
    ('/Welcome', Welcome),
    ('/NewPost', NewPost),
    ('/EditPost', EditPost),
    ('/DeletePost', DeletePost),
    ('/NewComment', NewComment),
    ('/EditComment', EditComment),
    ('/DeleteComment', DeleteComment),
    ('/Like', Like),
    ('/UnLike', UnLike),
    ('/SignUp', SignUp),
    ('/Login', Login),
    ('/Logout', Logout),
    ('/([0-9]+)', PostPage)
], debug=True)
