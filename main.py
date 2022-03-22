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
from motion_database_server.motion_database_server import DBApplicationServer
from motion_database_server.utils import load_json_file


def main(config):
    port = config.get("port", 8888)
    db_path = config.get("db_path", r"./motion.db")
    root_path = config.get("root_path", r"./public")
    enable_editing = config.get("enable_editing", False)
    enable_download = config.get("enable_download", False)
    activate_port_forwarding = config.get("activate_port_forwarding", False)
    ssl_options = config.get("ssl_options", None)
    server_secret = config.get("server_secret", None)
    print("activate_port_forwarding", activate_port_forwarding)
    server = DBApplicationServer(root_path, db_path, port, enable_editing=enable_editing,enable_download=enable_download,activate_port_forwarding=activate_port_forwarding, ssl_options=ssl_options, server_secret=server_secret)
    
    server.start()



CONFIG_FILE = "db_server_config.json"
if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    main(config)
