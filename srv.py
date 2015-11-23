#! /usr/bin/env python3
import http.server as srv
import cgi
import os
import json
#from http import HTTPStatus #find 3.4 equivalent...
from oauth2client import client, crypt

CLIENT_ID = "746271585204-8kcc5u48lf4q9u76dp32a45piardm6c5.apps.googleusercontent.com"

def load_pg(path):
  with open(path, 'r') as f:
    r = f.read()
    with open('template_head.html','r') as th:
      with open('template_body.html','r') as tb:
        h = th.read()
        b = tb.read()
        with open('api_key.txt') as api:
          with open('comment_form.html') as c_f:
            return r.format(template_head = h, template_body = b, api_key = api.read(), comment_form = c_f.read())

def write_user_page(loc, dt):
  with open(loc, 'w') as f:
    f.write("<!DOCTYPE html><html><head>{template_head}</head><body>{template_body}")
    f.write(dt['content'].replace('{','{{').replace('}','}}'))
    f.write('\n<div> {} needs:<ul> \n'.format(dt['name']))
    for i in dt['tags']:
      f.write('<li>{}</li>\n'.format(i))
    f.write("</ul>{comment_form}</body></html>")
  with open(loc.replace('.html','_comments.json'),'w') as g:
    g.write('{"comments": []}')

def verify_token(token):
  try:
    idinfo = client.verify_id_token(token, CLIENT_ID)
    if idinfo['aud'] != CLIENT_ID: #WEB_CLIENT_ID is CLIENT_ID...
      raise crypt.AppIdentityError("Unrecognized client.")
    if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
      raise crypt.AppIdentityError("Wrong issuer.")
#    if idinfo['hd'] != APPS_DOMAIN_NAME: #maybe when we're legit...
#      raise crypt.AppIdentityError("Wrong hosted domain.")
  except crypt.AppIdentityError as e:
    print("oauth2client error:",e)
    return False
  else:
    return idinfo['sub']

users = set()

def load_need_base():
  return json.load(open('db.json'))

def dump_need_base(db):
  json.dump(db, open('db.json', 'w'))

db = load_need_base()  

class FishRequestHandler(srv.SimpleHTTPRequestHandler):

  def send_content(self, txt, c_type = 'text/plain'):
    self.send_header('content-type',c_type)
    self.send_header('content-length',str(len(txt)))
    self.end_headers()
    self.wfile.write(txt.encode('utf-8'))

  def do_GET(self):
    if self.path == '/markers':
      locs = [db[i][j] for i in db for j in range(len(db[i]))]
      snd = json.dumps({'locs':locs})
      self.send_response(200)
      self.send_header('content-type','application/json')
      self.send_header('content-length',str(len(snd)))
      self.end_headers()
      self.wfile.write(snd.encode('utf-8'))
      return None
    elif self.path.startswith('/comments'):
      loc = self.path[len('/comments&loc='):]
      loc = srv.SimpleHTTPRequestHandler.translate_path(self, loc)
      with open(loc + '_comments.json') as c_f:
        self.send_response(200)
        self.send_header('content-type','application/json')
        self.end_headers()
        self.wfile.write(c_f.read().encode('utf-8'))
      return None
    elif self.path == '/' or self.path == '':
      p = "/index.html"
    else:
      p = self.path
    p = srv.SimpleHTTPRequestHandler.translate_path(self, p)
    if os.path.exists(p) and srv.SimpleHTTPRequestHandler.guess_type(self,p) == "text/html":
      s = load_pg(p)
      self.send_response(200)
      self.send_header('content-type','text/html')
      self.send_header('content-length',str(len(s)))
      self.end_headers()
      self.wfile.write(s.encode('utf-8'))
    else:
      srv.SimpleHTTPRequestHandler.do_GET(self)

  def do_POST(self):
    ctype, p = cgi.parse_header(self.headers['Content-Type'])
    if ctype == 'application/x-www-form-urlencoded' and self.path == "/tokensignin":
      l = int(self.headers['Content-Length'])
      postvars = cgi.parse_qs(self.rfile.read(l), keep_blank_values = 1)
      ver = verify_token(postvars[b'id_token'][0])
      if ver != False:
        users.add(ver)
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin",'*')
        self.send_content(ver)
      else:
        self.send_response(400)
        self.send_content("None")
    elif ctype == 'application/x-www-form-urlencoded' and self.path == "/tokensignout":
      l = int(self.headers['Content-Length'])
      postvars = cgi.parse_qs(self.rfile.read(l), keep_blank_values = 1)
      if postvars[b'id_token'][0] in users:
        users.remove(postvars[b'id_token'][0])
      self.send_response(200)
      self.send_content("None")

    elif ctype == 'application/json' and self.path == '/upload_need':
      global db
      l = int(self.headers['Content-Length'])
      d = self.rfile.read(l).decode('utf-8')
      dt = json.loads(d)
      dt['tags'] = list(filter(lambda x: len(x) > 0, dt['tags']))

      if dt['user'] != "None" and dt['user'] in users:
        data_dict = {'loc':'', 'geo': [dt['loc'][0], dt['loc'][1]], 'tags': dt['tags'], 'u_name': dt['name']}
        if dt['user'] in db:
          data_dict['loc'] = '/' + dt['user'] + '/' + str(len(db[dt['user']])) + '.html'
          db[dt['user']] += [data_dict]
        else:
          data_dict['loc'] = '/' + dt['user'] + '/0.html'
          db[dt['user']] = [data_dict]
          os.mkdir(dt['user'])  

        new_file = dt['user'] + '\\' + str(len(db[dt['user']]) - 1) + '.html'
        write_user_page(new_file, dt)
        dump_need_base(db)
        self.send_response(200)  
        self.send_header('Location',new_file)
        self.send_header("Access-Control-Allow-Origin",'*')
        self.send_content(new_file)

      else:
        self.send_response(401)
        self.send_content("Log in, please!")

    elif self.path == '/comment':
      l = int(self.headers['Content-Length'])
      d = self.rfile.read(l).decode('utf-8')
      dt = json.loads(d)
      loc = dt['loc'] + '_comments.json'
      del dt['loc']
      loc = srv.SimpleHTTPRequestHandler.translate_path(self, loc)
      with open(loc) as f:
        others = json.load(f)
      others['comments'] += [dt]
      with open(loc, 'w') as g:
        json.dump(others, g)
      self.send_response(200)
      self.send_content("Comment posted!")

    else:
      resp = "<html><body><h1>404 -> That fish was caught, apparently!</h1></body></html>"
      self.send_response(404)
      self.send_header("content-type","text/html")
      self.send_header("content-length",str(len(resp)))
      self.end_headers()
      self.wfile.write(resp)

r = srv.HTTPServer(('127.0.0.1',8080),FishRequestHandler)
try:
  r.serve_forever()
finally:
  dump_need_base(db)
