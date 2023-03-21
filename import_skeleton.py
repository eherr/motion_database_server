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
import bson
import bz2
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.utils import load_json_file
from anim_utils.animation_data import BVHReader, SkeletonBuilder

CONFIG_FILE = "db_server_config.json"

def add_skeleton(db_path, name, bvh_file, skeleton_model_file):
    
    schema = DBSchema(TABLES)
    db = MotionFileDatabase(schema)
    db.connect_to_database(db_path)
    bvh = BVHReader(bvh_file)
    skeleton = SkeletonBuilder().load_from_bvh(bvh)
    data = skeleton.to_unity_format()
    data = bz2.compress(bson.dumps(data))
    meta_data = None
    if skeleton_model_file is not None:
        meta_data = load_json_file(skeleton_model_file)
        meta_data = bz2.compress(bson.dumps(meta_data))
    db.add_new_skeleton(name, data, meta_data)
    db.close()

if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Import skeleton to db.')
    parser.add_argument('name', help='name')
    parser.add_argument('bvh_file', help='BVH file')
    parser.add_argument('skeleton_model', nargs="?", default=None, help='JSON file')
    args = parser.parse_args()
    if args.name is not None and args.bvh_file is not None:
        db_path = config["db_path"]
        add_skeleton(db_path, args.name, args.bvh_file, args.skeleton_model)
