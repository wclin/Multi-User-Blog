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

def render_str(template, **params): # used by permalink post.render()
	t = JINJA_ENVIRONMENT.get_template(template)
	return t.render(params)

class Alert(): # Or maybe __init__ is fine
	# ['alert-success', 'alert-info', 'alert-warning', 'alert-danger']
	@classmethod
	def set(cls, category, message):
		a = cls()
		a.category = category
		a.message = message
		return a

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

class Author(db.Model):
	name = db.StringProperty(required = True)
	pwdh = db.StringProperty(required = True)
	eamil = db.StringProperty()
	dscr = db.StringProperty() 

class Post(db.Model):
	author = db.ReferenceProperty(Author)
	title = db.StringProperty()
	content = db.TextProperty()
	created = db.DateTimeProperty(auto_now_add = True)

	def render(self, template_values):
		self._render_text = self.content.replace('\n', '<br>')
		#template_values = {
		#		'user': self.getName(),
		#		'alert': self.getAlert(),
		#		'p': self
		#}
		template = JINJA_ENVIRONMENT.get_template('post.html')
		#self.response.write(template.render(template_values))
		return template.render(template_values)
		#return render_str("post.html", template_values)

class MainPage(Handler):
	def get(self):
		author = self.getUser()
		if author:
			template_values = {
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
		template_values = {
				'user': self.getName(),
				'alert': self.getAlert(),
				'posts': Post.all().order('-created')
		}
		template = JINJA_ENVIRONMENT.get_template('timeline.html')
		self.response.write(template.render(template_values))
		#self.render("timeline.html", author = self.getName(), posts = posts)

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

class EditPost(Handler):
	def getPost(self):
		post_id = self.request.get("post_id")
		key = db.Key.from_path("Post", int(post_id), parent=blog_key())
		return db.get(key)

	def unEditable(self, p):
		alert = dict(category="alert-danger", message="It's not your post!")
		self.redirect("/%s?%s" % (str(p.key().id()), urllib.urlencode(alert)))

	def get(self):
		p = self.getPost()
		if self.getName() != p.author.name:
			self.unEditable(p)
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
			#self.write("Login first yo")
			alert = dict(category="alert-warning", message="Login first yo")
			self.redirect("/Login?%s" % urllib.urlencode(alert))
			#self.redirect("/Login")

	def post(self):
		author = self.getUser()
		title = self.request.get("title")
		content = self.request.get("content")
		if author:
			p = Post(parent = blog_key(), author = author, title = title, content = content)
			p.put()
			alert = dict(category="alert-success", message="Here~")
			#self.redirect("/%s?%s" % (str(p.key().id()), urllib.urlencode(alert)))
			self.redirect("/%s" % str(p.key().id()))
		else:
			alert = dict(category="alert-danger", message="Please login first!")
			self.redirect("/Login?%s" % urllib.urlencode(alert))
			#self.write("No valid yo")

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
		# Password verify twice
		pwd = self.request.get("password")
		email = self.request.get("email")
		pwdh = make_pw_hash(name, pwd)
		a = Author.get_by_key_name(name)
		if a:
			alert = dict(category="alert-danger", message="Duplicate!")
			self.redirect("/Login?%s" % urllib.urlencode(alert))
			#self.write("Already been used lwo")
		else :
			a = Author(key_name = name, name = name, pwdh = pwdh, email = email)
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
		#self.redirect("/Login")

class Welcome(Handler):
	def get(self):
		if self.getName():
			alert = dict(category="alert-success", message="Welcome!")
			self.redirect("/Timeline?%s" % urllib.urlencode(alert))
			#self.redirect("/")
		else: 
			alert = dict(category="alert-danger", message="Nooooo")
			self.redirect("/Login?%s" % urllib.urlencode(alert))
			#self.write("Nooooo")


app = webapp2.WSGIApplication([
	('/', MainPage), 
	('/Timeline', Timeline), 
	('/Welcome', Welcome), 
	('/NewPost', NewPost), 
	('/EditPost', EditPost), 
	('/SignUp', SignUp), 
	('/Login', Login), 
	('/Logout', Logout), 
	('/([0-9]+)', PostPage)
], debug=True)
