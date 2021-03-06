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
import argparse
from motion_database import MotionDatabase
from anim_utils.utilities.io_helper_functions import load_json_file
from anim_utils.animation_data import BVHReader, SkeletonBuilder

CONFIG_FILE = "db_server_config.json"

if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Import skeleton to db.')
    parser.add_argument('name', nargs='?', help='name')
    parser.add_argument('skeleton_path', nargs='?', help='BVH file')
    args = parser.parse_args()
    if args.name is not None and args.skeleton_path is not None:
        db = MotionDatabase()
        db_path = config["db_path"]
        db.connect(db_path)
        bvh = BVHReader(args.skeleton_path)
        skeleton = SkeletonBuilder().load_from_bvh(bvh)
        data = skeleton.to_unity_format()
        meta_data = dict()
        meta_data["cos_map"] = dict()
        meta_data["joints"] = dict()
        meta_data["joint_constraints"] = dict()
        data = bson.dumps(data)
        meta_data = bson.dumps(meta_data)
        print("add new skeleton", args.name)
        db.add_new_skeleton(args.name, data, meta_data)
        db.close()
