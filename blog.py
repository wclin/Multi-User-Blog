#!/usr/bin/env python
import os
import jinja2
import webapp2

from google.appengine.ext import db

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

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

#class Author(db.Model):
#	name = db.StringProperty(required = True)

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


app = webapp2.WSGIApplication([
	('/', MainPage), ('/NewPost', NewPost), ('/([0-9]+)', PostPage)
], debug=True)
