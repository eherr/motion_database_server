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
from motion_database_server.user_database import UserDatabase
from motion_database_server.utils import load_json_file
import argparse

def create_user(path, name, pw, role, email):
    con = UserDatabase()
    con.connect(path)
    con.create_user(name, pw, email, role, [])

CONFIG_FILE = "db_server_config.json"

if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Create db user.')
    parser.add_argument('name', help='user name')
    parser.add_argument('pw', help='password')
    parser.add_argument('role',  help='role')
    parser.add_argument('email', help='email')
    args = parser.parse_args()
    if  args.name is not None and args.pw is not None and args.role is not None and "db_path" in config:
        db_path = config["db_path"]
        create_user(db_path,  args.name, args.pw,  args.role, args.email)

