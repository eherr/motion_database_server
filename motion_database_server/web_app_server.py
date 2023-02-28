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

import os
import json
import threading
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
from motion_database_server.base_handler import BaseHandler
class CustomStaticFileHander(tornado.web.StaticFileHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")


class IndexHandler(BaseHandler):
    """ HTTP handler to serve the main web page """

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.enable_editing = False
        self.path_prefix = "./"
        if self.app.activate_port_forwarding:
            self.path_prefix = str(self.app.port)

    def get(self):
        self.render("index.html", path_prefix=self.path_prefix, 
                    enable_editing=self.enable_editing,
                    app_server_port=str(self.app.port),
                    app_server_activate_port_forwarding=self.app.activate_port_forwarding,
                    app_server_enable_download=self.app.enable_download
                    )


class GetMetaHandler(BaseHandler):
    @tornado.gen.coroutine
    def post(self):
        result_object = dict(id=str(self.app.idCounter), server_port=str(self.app.port),
                             activate_port_forwarding=self.app.activate_port_forwarding,
                             enable_download=self.app.enable_download)

        self.write(json.dumps(result_object))


class WebAppServer(tornado.web.Application):
    """ Tornado Server for registering that REST services
    """
    def __init__(self, **kwargs):
        self.port = kwargs.get("port", 8888)
        self.root_path = kwargs.get("root_path", r"./public")
        self.server_secret = kwargs.get("server_secret", None)
        self.activate_port_forwarding = kwargs.get("activate_port_forwarding", False)
        self.enable_download = kwargs.get("enable_download", False)
        self.ssl_options = kwargs.get("ssl_options", None)
        self.activate_user_authentification = kwargs.get("activate_user_authentification", True) 

        self.request_handler_list = [(r"/", IndexHandler), (r"/get_meta_data", GetMetaHandler)]        
        self.service_contexts = dict()
        self.idCounter = 0
        self.mutex = threading.Lock()


    def get_service_context(self, service_name):
        return self.service_contexts[service_name]

    def register_service(self, service_context):
        service_name = service_context.service_name
        self.service_contexts[service_name] = service_context
        self.request_handler_list += service_context.request_handler_list

    def start(self):
        settings = dict(template_path=os.path.join(os.path.dirname(__file__), "..", "templates"))
        
        self.request_handler_list += [(r"/(.+)", CustomStaticFileHander, {"path": self.root_path})]  # NEEDS TO BE AT THE END
        tornado.web.Application.__init__(self, self.request_handler_list, "", None, **settings)

        print("Start Tornado REST interface on port", self.port, self.ssl_options)
        for k in self.service_contexts:
            print("starting service", k)
        print("activate_port_forwarding", self.activate_port_forwarding)
        #asyncio.set_event_loop(asyncio.new_event_loop())
        try:
            if self.ssl_options is not None:
                self.listen(self.port, ssl_options=self.ssl_options)
            else:
                self.listen(self.port)
            def check_keyboard_for_shutdown():
                return
            tornado.ioloop.PeriodicCallback(check_keyboard_for_shutdown, 1000).start()
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            print("Handle Keyboard Interrupt")
            tornado.ioloop.IOLoop.instance().stop()

    def stop(self):
        print("stop")
        tornado.ioloop.IOLoop.instance().stop()

