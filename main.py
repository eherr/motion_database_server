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
import time
import json
from motion_database_server import DBApplicationServer

def load_json_file(file_path):
    if os.path.isfile(file_path):
        with open(file_path, "r") as in_file:
            return json.load(in_file)


def main(config):
    port=8888
    if "port" in config:
        port = config["port"]
    db_path = r"./motion.db"
    if "db_path" in config:
        db_path = config["db_path"]
    root_path = r"./public"
    if "root_path" in config:
        root_path = config["root_path"]
    enable_editing = False
    if "enable_editing" in config:
        enable_editing = config["enable_editing"]
    enable_download = False
    if "enable_download" in config:
        enable_download = config["enable_download"]
    activate_port_forwarding = False
    if "activate_port_forwarding" in config:
        activate_port_forwarding = config["activate_port_forwarding"]
    ssl_options = None
    if "ssl_options" in config and type(config["ssl_options"]) == dict:
        ssl_options = config["ssl_options"]
    server_secret = None
    if "server_secret" in config:
        server_secret = config["server_secret"]
    print("activate_port_forwarding", activate_port_forwarding)
    server = DBApplicationServer(root_path, db_path, port, enable_editing=enable_editing,enable_download=enable_download,activate_port_forwarding=activate_port_forwarding, ssl_options=ssl_options, server_secret=server_secret)
    
    server.start()



CONFIG_FILE = "db_server_config.json"
if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    main(config)
