#this is only to test the code for the webpage.
#python 3 only.
import http.server as srv

r = srv.HTTPServer(('localhost',8080),srv.SimpleHTTPRequestHandler)

r.serve_forever()
