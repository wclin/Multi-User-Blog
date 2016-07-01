#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import jinja2
import webapp2

from google.appengine.ext import db

JINJA_ENVIRONMENT = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
	extensions=['jinja2.ext.autoescape'],
	autoescape=True)

class Author(db.Model):
    name = db.StringProperty(required = True)

class Post(db.Model):
    #author = db.ReferenceProperty(Author)
    author = db.StringProperty()
    title = db.StringProperty()
    content = db.TextProperty()
    created = db.DateTimeProperty(auto_now_add = True)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
	self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
	return (JINJA_ENVIRONMENT.get_template(template)).render(params)

    def render(self, template, **kw):
	self.write(self.render_str(template, **kw))
    
class MainPage(Handler):
    def get(self):
	posts = db.GqlQuery("SELECT * FROM Post "
			    "ORDER BY created DESC ")
	self.render("index.html", posts = posts)

class NewPostHandler(Handler):
    def get(self):
	self.render("newpost.html")

    def post(self):
	author = self.request.get("author")
	title = self.request.get("title")
	content = self.request.get("content")
	Post(author = author, title = title, content = content).put()
	self.redirect("/")


app = webapp2.WSGIApplication([
    ('/', MainPage), ('/NewPost', NewPostHandler)
], debug=True)
