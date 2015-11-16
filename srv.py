#! /usr/bin/env python3
import http.server as srv
import cgi
#from http import HTTPStatus #find 3.4 equivalent...
from oauth2client import client, crypt

CLIENT_ID = "746271585204-8kcc5u48lf4q9u76dp32a45piardm6c5.apps.googleusercontent.com"

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

class FishRequestHandler(srv.SimpleHTTPRequestHandler):
  def do_GET(self):
    if self.client_address[0] in ok_IPs:
      self.send_header("Access-Control-Allow-Origin",'*')
    srv.SimpleHTTPRequestHandler.do_GET(self)  
  def do_POST(self):
    ctype, p = cgi.parse_header(self.headers['Content-Type'])
    if ctype == 'application/x-www-form-urlencoded':
      l = int(self.headers['Content-Length'])
      postvars = cgi.parse_qs(self.rfile.read(l), keep_blank_values = 1)
      #postvars['id_token'] = postvars[b'id_token'][0].decode('utf-8')
      ver = verify_token(postvars[b'id_token'][0])
      if ver != False:
        users.update(set(ver))
        self.send_response(301)
        self.send_header("Location","/need_upload.html")
        self.send_header("Access-Control-Allow-Origin",'*')
        self.end_headers()
      else:
        self.send_response(400)
        self.end_headers()
    else:
      self.send_response(404)
      self.end_headers()

r = srv.HTTPServer(('127.0.0.1',8080),FishRequestHandler)

r.serve_forever()
