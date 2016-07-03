#!/usr/bin/env python
import os
import jinja2
import webapp2
from libs.bcrypt import bcrypt

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

def render_str(template, **params):
	t = JINJA_ENVIRONMENT.get_template(template)
	return t.render(params)

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		return (JINJA_ENVIRONMENT.get_template(template)).render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

class Author(db.Model):
	name = db.StringProperty(required = True)
	pwdh = db.StringProperty(required = True)
	eamil = db.StringProperty()
	dscr = db.StringProperty() 

def blog_key(name = 'default'):
	return db.Key.from_path('blogs', name)

class Post(db.Model):
	#author = db.ReferenceProperty(Author)
	author = db.StringProperty()
	title = db.StringProperty()
	content = db.TextProperty()
	created = db.DateTimeProperty(auto_now_add = True)

	def render(self):
		self._render_text = self.content.replace('\n', '<br>')
		return render_str("post.html", p = self)

class MainPage(Handler):
	def get(self):
		#posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC")
		posts = Post.all().order('-created')
		self.render("index.html", posts = posts)

class PostPage(Handler):
	def get(self, post_id):
		key = db.Key.from_path("Post", int(post_id), parent=blog_key())
		post = db.get(key)
		self.render("permalink.html", post = post)

class NewPost(Handler):
	def get(self):
		self.render("newpost.html")

	def post(self):
		author = self.request.get("author")
		title = self.request.get("title")
		content = self.request.get("content")
		p = Post(parent = blog_key(), author = author, title = title, content = content)
		p.put()
		self.redirect("/%s" % str(p.key().id()))

class SignUp(Handler):
	def get(self):
		self.render("signup.html")

	def post(self):
		name = self.request.get("username")
		pwd = self.request.get("password")
		email = self.request.get("email")
		# Hash the pwd
		pwdh = make_pw_hash(name, pwd)
		a = Author(key_name = name, name = name, pwdh = pwdh, email = email)
		a.put()
		# Add cookie
		token = make_pw_hash(str(a.name), '')
		self.response.headers.add_header('Set-Cookie', 'uname=%s|%s' % (str(a.name), token))
		self.redirect("/Welcome")

class Login(Handler):
	def get(self):
		self.render("login.html")

	def post(self):
		name = self.request.get("username")
		pwd = self.request.get("password")
		u = Author.get_by_key_name(name) if name!='' else None
		# Verify pwd
		if valid_pw(name, pwd, u.pwdh):
			# Add cookie
			token = make_pw_hash(str(u.name), '')
			self.response.headers.add_header('Set-Cookie', 'uname=%s|%s' % (str(u.name), token))
			self.redirect("/Welcome")
		else:
			self.write("No~")

class Logout(Handler):
	def get(self):
		#self.request.cookies.clear()
		self.response.headers.add_header('Set-Cookie', 'uname=%s' % '|')

		self.redirect("/Login")

class Welcome(Handler):
	def get(self):
		cookie = self.request.cookies.get('uname')
		uname, token = cookie.split('|')
		u = Author.get_by_key_name(uname) if uname!='' else None
		# Verify cookie
		if u and valid_pw(uname, '', token):
			self.render("welcome.html", username=str(u.name))
		else: 
			self.write("Nooooo")


app = webapp2.WSGIApplication([
	('/', MainPage), ('/Welcome', Welcome), ('/NewPost', NewPost), ('/SignUp', SignUp), ('/Login', Login), ('/Logout', Logout), ('/([0-9]+)', PostPage)
], debug=True)
