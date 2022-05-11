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
import requests
from motion_database_server.motion_database import MotionDatabase
from motion_database_server.kubernetes_interface import load_kube_config
from motion_database_server.motion_database_handlers import BaseHandler, MOTION_DB_HANDLER_LIST
from motion_database_server.user_database_handlers import USER_DB_HANDLER_LIST
from motion_database_server.skeleton_database_handlers import SKELETON_DB_HANDLER_LIST
from motion_database_server.character_storage_handlers import CHARACTER_HANDLER_LIST
from motion_database_server.job_server_handlers import JOB_SERVER_HANDLER_LIST


class CustomStaticFileHander(tornado.web.StaticFileHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")


class IndexHandler(BaseHandler):
    """ HTTP handler to serve the main web page """

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.enable_editing = False
        self.motion_database = self.app.motion_database
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



class DBApplicationServer(tornado.web.Application):
    """ Wrapper for the MotionDatabase class that starts the Tornado Webserver
    """
    def __init__(self, **kwargs):
        self.port = kwargs.get("port", 8888)
        self.root_path = kwargs.get("root_path", r"./public")
        self.db_path = kwargs.get("db_path", r"./motion.db")
        server_secret = kwargs.get("server_secret", None)
        self.motion_database = MotionDatabase(server_secret)
        self.motion_database.connect(self.db_path)
        self.activate_port_forwarding = kwargs.get("activate_port_forwarding", False)
        self.enable_download = kwargs.get("enable_download", False)
        self.ssl_options = kwargs.get("ssl_options", None)
        kube_config = kwargs.get("kube_config", None)
        if kube_config is not None:
            load_kube_config(kube_config["config_file"])
            self.k8s_namespace = kube_config["namespace"]
        else:
            self.k8s_namespace = ""
        request_handler_list = [(r"/", IndexHandler)]
        request_handler_list += USER_DB_HANDLER_LIST
        request_handler_list += SKELETON_DB_HANDLER_LIST
        request_handler_list += MOTION_DB_HANDLER_LIST
        request_handler_list += CHARACTER_HANDLER_LIST
        request_handler_list += JOB_SERVER_HANDLER_LIST
        request_handler_list += [(r"/(.+)", CustomStaticFileHander, {"path": self.root_path})]
        template_path = os.path.join(os.path.dirname(__file__), "..", "templates")
        settings = dict(template_path=template_path)
        tornado.web.Application.__init__(self, request_handler_list, "", None, **settings)
        self.server_registry = dict()
        self.activate_user_authentification = kwargs.get("activate_user_authentification", True) 
        self.idCounter = 0
        self.mutex = threading.Lock()

    def start(self):
        print("Start Animation Database REST interface on port", self.port, self.ssl_options)
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

    def get_server_status(self, name):
        result = dict()
        if name not in self.server_registry:
            return result
        server_address = self.server_registry[name]["address"]
        server_port = self.server_registry[name]["port"]
        url_str = "http://" + server_address + ":" + str(server_port)+'/status'
        try:
            r = requests.get(url_str)
            r_dict = json.loads(r.text)
            if "success" in r_dict:
                result = r_dict
            else:
                print("Failed to register server")
        except Exception as e:
            print("Exception during registration", e.args)
        return result
