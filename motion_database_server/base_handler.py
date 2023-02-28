#!/usr/bin/env python
#
# Copyright 2019 DFKI GmbH.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the
# following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
import mimetypes
import tornado.web
import json


mimetypes.add_type("application/html", ".html")
mimetypes.add_type("application/xml", ".xml")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

class BaseHandler(tornado.web.RequestHandler):
    """ https://stackoverflow.com/questions/35254742/tornado-server-enable-cors-requests"""
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    def set_default_headers(self):
        self.set_header("access-control-allow-origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Origin, Content-Type, X-Auth-Token")
        self.set_header('Access-Control-Allow-Methods', 'GET, PUT, DELETE, OPTIONS')
        ## HEADERS!
        self.set_header("Access-Control-Allow-Headers", 'Authorization, Content-Type, Access-Control-Allow-Origin, Access-Control-Allow-Headers, X-Requested-By, Access-Control-Allow-Methods')

    def options(self, *args, **kwargs):
        # no body   
        self.set_status(200)
        self.finish()

    def get(self, *args, **kwargs):
        error_string = "GET request not implemented. Use POST instead."
        print(error_string)
        self.write(error_string)

class BaseDBHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application.get_service_context("MOTION_DB")
        self.db_path = self.app.db_path
        self.motion_database = self.app.motion_database
        self.project_service = application.get_service_context("PROJECT_DB")
        self.project_database = self.project_service.project_database
        self.data_transform_service = application.get_service_context("DATA_TRANSFORM_DB")

class JSONHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_dict = json.loads(input_str)
           response_dict = self.method(self, input_dict)
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

    def handle_json_request(self, input_data):
        pass