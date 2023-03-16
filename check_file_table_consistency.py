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
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.utils import load_json_file

CONFIG_FILE = "db_server_config.json"


def check_consistency(db_path, data_dir):
    schema = DBSchema(TABLES)
   
    motion_db = MotionFileDatabase(schema, data_dir=data_dir)
    motion_db.connect_to_database(db_path)
    motion_db.check_file_consistency()
    motion_db.close()

if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Check file table consistency.')
    parser.add_argument('directory', nargs='?', default="data",help='Data directory')
    args = parser.parse_args()
    
    if args.directory is not None:
        check_consistency(config["db_path"], args.directory)
  