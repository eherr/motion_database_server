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
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.project_database import ProjectDatabase
from motion_database_server.utils import load_json_file


def create_database(db_path, project_name, user_name, pw, email):
    schema = DBSchema(TABLES)
    schema.create_database(db_path)
    project_db = ProjectDatabase(schema)
    project_db.connect_to_database(db_path)
    user_id = project_db.create_user(user_name, pw, email, "admin", [])
    project_db.create_project(project_name, user_id, True)
    


CONFIG_FILE = "db_server_config.json"
if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Create database.')
    parser.add_argument('project_name', nargs='?', help='project_name')
    parser.add_argument('user_name', nargs='?', help='user name')
    parser.add_argument('pw', nargs='?', help='password')
    parser.add_argument('email', nargs='?', help='email')
    args = parser.parse_args()
    kwargs = vars(args)
    if args.db_path is not None and args.user_name is not None and args.pw is not None and args.email is not None:
        create_database(config["db_path"], **kwargs)