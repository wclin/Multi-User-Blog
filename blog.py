#!/usr/bin/env python
import os
import jinja2
import webapp2
import urllib
from libs.bcrypt import bcrypt
import Queue

from google.appengine.ext import db

SECRET = open("secret.txt", "r").readline()

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

#ALERT = Queue.Queue()

def make_pw_hash(name, pwd):
	return bcrypt.hashpw(name+pwd+SECRET, bcrypt.gensalt())

def valid_pw(name, pwd, hashed):
	return bcrypt.hashpw(name+pwd+SECRET, hashed) == hashed


def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)

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

	def render(self):
		self._render_text = self.content.replace('\n', '<br>')
		template_values = {
				'user': self.getName(),
				'alert': self.getAlert(),
		}
		template = JINJA_ENVIRONMENT.get_template('login.html')
		self.response.write(template.render(template_values))
		#return render_str("post.html", author = self.author, p = self)

class MainPage(Handler):
	def get(self):
		author = self.getUser()
		if author:
			posts = Post.all().filter('author =', author).order('-created')
			template_values = {
					'user': self.getName(),
					'alert': self.getAlert(),
			}
			template = JINJA_ENVIRONMENT.get_template('login.html')
			self.response.write(template.render(template_values))
			#self.render("index.html", author = self.getName(), posts = posts)
		else:
			self.redirect("/Login")

class Timeline(Handler):
	def get(self):
		posts = Post.all().order('-created')
		template_values = {
				'user': self.getName(),
				'alert': self.getAlert(),
		}
		template = JINJA_ENVIRONMENT.get_template('login.html')
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
		}
		template = JINJA_ENVIRONMENT.get_template('login.html')
		self.response.write(template.render(template_values))
		#self.render("permalink.html", post = post)

class NewPost(Handler):
	def get(self):
		if self.getUser():
			template_values = {
					'user': self.getName(),
					'alert': self.getAlert(),
			}
			template = JINJA_ENVIRONMENT.get_template('login.html')
			self.response.write(template.render(template_values))
			#self.render("newpost.html", author = self.getName())
		else:
			#self.write("Login first yo")
			self.redirect("/Login")

	def post(self):
		author = self.getUser()
		title = self.request.get("title")
		content = self.request.get("content")
		if author:
			p = Post(parent = blog_key(), author = author, title = title, content = content)
			p.put()
			self.redirect("/%s" % str(p.key().id()))
		else:
			self.write("No valid yo")

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
			self.write("Already been used lwo")
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
			alert = dict(category="alert-warning", message="No~")
			self.redirect("/Login?%s" % urllib.urlencode(alert))

class Logout(Handler):
	def get(self):
		self.setName()
		self.redirect("/Login")

class Welcome(Handler):
	def get(self):
		if self.getName():
			self.redirect("/")
		else: 
			self.write("Nooooo")


app = webapp2.WSGIApplication([
	('/', MainPage), ('/Timeline', Timeline), ('/Welcome', Welcome), ('/NewPost', NewPost), ('/SignUp', SignUp), ('/Login', Login), ('/Logout', Logout), ('/([0-9]+)', PostPage)
], debug=True)
