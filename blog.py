#!/usr/bin/env python
import os
import jinja2
import webapp2
import urllib
from libs.bcrypt import bcrypt
import logging as log

from google.appengine.ext import db

SECRET = open("secret.txt", "r").readline()

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

def make_pw_hash(name, pwd):
	return bcrypt.hashpw(name+pwd+SECRET, bcrypt.gensalt())

def valid_pw(name, pwd, hashed):
	return bcrypt.hashpw(name+pwd+SECRET, hashed) == hashed

def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)

class Alert():
	"""A simple class represent bootstrap alert.
	
	Attributes:
		category (str): corresponding to 4 bootstrap alert class:
			['alert-success', 'alert-info', 'alert-warning', 'alert-danger']
		message (str): The string shows on alert.
	
	"""
	@classmethod  #Or maybe __init__ is fine
	def set(cls, category, message):
		a = cls()
		a.category = category
		a.message = message
		return a

class Author(db.Model):
	name = db.StringProperty(required = True)
	pwdh = db.StringProperty(required = True)
	eamil = db.StringProperty()
	dscr = db.TextProperty() 

class Post(db.Model):
	author = db.ReferenceProperty(Author)
	title = db.StringProperty()
	content = db.TextProperty()
	created = db.DateTimeProperty(auto_now_add = True)
	likes = db.IntegerProperty(default=0)
	isLiked = db.BooleanProperty()

	def render(self, template_values):
		self._render_text = self.content.replace('\n', '<br>')
		template = JINJA_ENVIRONMENT.get_template('post.html')
		return template.render(template_values)

class Handler(webapp2.RequestHandler):
	def __init__(self, request, response):
		self.initialize(request, response)
		self.alert = None

	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		return (JINJA_ENVIRONMENT.get_template(template)).render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))
	
	def getName(self): # return valid name or None
		user = self.getUser()
		return user.name if user else None

	def getUser(self): # return Author or None
		cookie = self.request.cookies.get('uname')
		uname, token = cookie.split('|') if cookie else ('', None)
		uname = uname if uname != '' and valid_pw(uname, '', token) else None
		return Author.get_by_key_name(uname) if uname else None

	def setName(self, user = None): # set Uname Cookie	from Author
		if user:
			token = make_pw_hash(str(user.name), '')
			self.response.headers.add_header('Set-Cookie', 'uname=%s|%s' % (str(user.name), token))
		else:
			self.response.headers.add_header('Set-Cookie', 'uname=%s' % '|')
	
	def getAlert(self):
		message = self.request.get('message')
		category = self.request.get('category')
		return Alert.set(category, message)
	
	def getPost(self):
		post_id = self.request.get("post_id")
		key = db.Key.from_path("Post", int(post_id), parent=blog_key())
		return db.get(key)

	def unEditable(self, p):
		alert = dict(category="alert-danger", message="It's not your post!")
		self.redirect("/%s?%s" % (str(p.key().id()), urllib.urlencode(alert)))

	def isLiked(self, p):
		u = self.getUser()
		return Likes.all().filter('user =', u).filter('post =', p).get()

class Likes(db.Model):
	user = db.ReferenceProperty(Author)
	post = db.ReferenceProperty(Post)

class MainPage(Handler):
	def get(self):
		author = self.getUser()
		if author:
			template_values = {
					'author': author,
					'user': self.getName(),
					'alert': self.getAlert(),
					'posts': Post.all().filter('author =', author).order('-created')
			}
			template = JINJA_ENVIRONMENT.get_template('index.html')
			self.response.write(template.render(template_values))
			#self.render("index.html", author = self.getName(), posts = posts)
		else:
			alert = dict(category="alert-warning", message="Login le ma?")
			self.redirect("/Login?%s" % urllib.urlencode(alert))
			#self.redirect("/Login")

class Timeline(Handler):
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
		#self.render("timeline.html", author = self.getName(), posts = posts)

class Like(Handler):
	def get(self):
		p = self.getPost()
		if self.isLiked(p):
			alert = dict(category="alert-danger", message="Already liked!!")
			self.redirect("/Timeline?%s" % urllib.urlencode(alert))
			return
		u = self.getUser()
		log.info("u = %s" % u)
		if not u:
			alert = dict(category="alert-warning", message="Login before like!")
			self.redirect("/Login?%s" % urllib.urlencode(alert))
			return
		if u and u.name == p.author.name:
			alert = dict(category="alert-danger", message="You self-lover!")
			self.redirect("/Timeline?%s" % urllib.urlencode(alert))
			return
		l = Likes(user = u, post = p)
		l.put()
		p.likes = p.likes + 1
		p.put()
		alert = dict(category="alert-success", message="Like!!")
		self.redirect("/Timeline?%s" % urllib.urlencode(alert))

class UnLike(Handler):
	def get(self):
		p = self.getPost()
		if not self.isLiked(p):
			alert = dict(category="alert-danger", message="Didn't like yet!!")
			self.redirect("/Timeline?%s" % urllib.urlencode(alert))
			return
		l = Likes.all().filter('user =', self.getUser()).filter('post =', p).get()
		l.delete()
		p.likes = p.likes - 1
		p.put()
		alert = dict(category="alert-success", message="UnLike!!")
		self.redirect("/Timeline?%s" % urllib.urlencode(alert))

class PostPage(Handler):
	def get(self, post_id):
		key = db.Key.from_path("Post", int(post_id), parent=blog_key())
		post = db.get(key)
		# So weird \/
		template_values = {
				'user': self.getName(),
				'alert': self.getAlert(),
				'p': post,
				'post_id': post_id
		}
		#template = JINJA_ENVIRONMENT.get_template('permalink.html')
		#self.response.write(template.render(template_values))
		self.render("permalink.html", post = post, template_values = template_values)

class DeletePost(Handler):
	def get(self):
		p = self.getPost()
		if self.getName() != p.author.name:
			self.unEditable(p)
			return
		p.delete()
		alert = dict(category="alert-success", message="Deleted!!")
		self.redirect("/Timeline?%s" % urllib.urlencode(alert))

class EditPost(Handler):
	def get(self):
		p = self.getPost()
		if self.getName() != p.author.name:
			self.unEditable(p)
			return
		template_values = {
				'user': self.getName(),
				'alert': self.getAlert(),
				'p': p,
				'post_id': self.request.get("post_id"),
		}
		template = JINJA_ENVIRONMENT.get_template('editpost.html')
		self.response.write(template.render(template_values))
		#self.render("editpost.html", template_values)
	
	def post(self):
		p = self.getPost()
		if self.getName() != p.author.name:
			self.unEditable(p)
			return
		p.title = self.request.get("title")
		p.content = self.request.get("content")
		p.put()
		self.redirect("/%s" % str(p.key().id()))

class NewPost(Handler):
	def get(self):
		if self.getUser():
			template_values = {
					'user': self.getName(),
					'alert': self.getAlert(),
			}
			template = JINJA_ENVIRONMENT.get_template('newpost.html')
			self.response.write(template.render(template_values))
			#self.render("newpost.html", author = self.getName())
		else:
			alert = dict(category="alert-warning", message="Login first yo")
			self.redirect("/Login?%s" % urllib.urlencode(alert))

	def post(self):
		author = self.getUser()
		title = self.request.get("title")
		content = self.request.get("content")
		if author:
			p = Post(parent = blog_key(), author = author, title = title, content = content)
			p.put()
			alert = dict(category="alert-success", message="Here~")
			self.redirect("/%s?%s" % (str(p.key().id()), urllib.urlencode(alert)))
		else:
			alert = dict(category="alert-danger", message="Please login first!")
			self.redirect("/Login?%s" % urllib.urlencode(alert))

class SignUp(Handler):
	def get(self):
		template_values = {
				'user': self.getName(),
				'alert': self.getAlert(),
		}
		template = JINJA_ENVIRONMENT.get_template('signup.html')
		self.response.write(template.render(template_values))
		#self.render("signup.html", author = self.getName())

	def post(self):
		name = self.request.get("username")
		pwd = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")
		dscr = self.request.get("description")
		pwdh = make_pw_hash(name, pwd)
		a = Author.get_by_key_name(name)
		if not pwd or pwd != verify:
			alert = dict(category="alert-danger", message="Verification failed!")
			self.render("signup.html", user = self.getName(), alert = alert, username = name, email = email, description = dscr)
			#self.redirect("/SignUp?%s" % urllib.urlencode(alert))
			return
		if a:
			alert = dict(category="alert-danger", message="Duplicate!")
			self.render("signup.html", user = self.getName(), alert = alert, username = name, email = email, description = dscr)
			#self.redirect("/SignUp?%s" % urllib.urlencode(alert))
			return
		else :
			a = Author(key_name = name, name = name, pwdh = pwdh, email = email, dscr = dscr)
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
		#self.render("login.html", template_values)

	def post(self):
		name = self.request.get("username")
		pwd = self.request.get("password")
		u = Author.get_by_key_name(name) if name!='' else None
		if u and valid_pw(name, pwd, u.pwdh):
			self.setName(u)
			self.redirect("/Welcome")
		else:
			alert = dict(category="alert-warning", message="Try again~")
			self.redirect("/Login?%s" % urllib.urlencode(alert))

class Logout(Handler):
	def get(self):
		self.setName()
		alert = dict(category="alert-success", message="Bye~")
		self.redirect("/Login?%s" % urllib.urlencode(alert))

class Welcome(Handler):
	def get(self):
		if self.getName():
			alert = dict(category="alert-success", message="Welcome!")
			self.redirect("/Timeline?%s" % urllib.urlencode(alert))
		else: 
			alert = dict(category="alert-danger", message="Nooooo")
			self.redirect("/Login?%s" % urllib.urlencode(alert))


app = webapp2.WSGIApplication([
	('/', MainPage), 
	('/Timeline', Timeline), 
	('/Welcome', Welcome), 
	('/NewPost', NewPost), 
	('/EditPost', EditPost), 
	('/DeletePost', DeletePost), 
	('/Like', Like),
	('/UnLike', UnLike),
	('/SignUp', SignUp), 
	('/Login', Login), 
	('/Logout', Logout), 
	('/([0-9]+)', PostPage)
], debug=True)
