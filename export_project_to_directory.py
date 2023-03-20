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
import argparse
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.project_database import ProjectDatabase
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.utils import load_json_file
from motion_database_server.utils import extract_compressed_bson

CONFIG_FILE = "db_server_config.json"

def export_data_to_file(db, skeleton, file_id, name, data_type, directory):
    data = db.get_file_by_id(file_id)
    if data is None:
        return
    tags = [t[0] for t in db.get_data_type_tag_list(data_type)]
    binary_data = data
    if "compressed_bson" in tags:
        raw_data = extract_compressed_bson(data)
        data_str = json.dumps(raw_data)
        binary_data = data_str.encode("utf-8")

    filename = directory+os.sep+name + "."+ data_type
    with open(filename, "wb") as out_file:
        out_file.write(binary_data)
   
def get_parent_collection(db_path, project_name):
    schema = DBSchema(TABLES)
    project_db = ProjectDatabase(schema)
    project_db.connect(db_path)
    project_id = project_db.get_project_id(project_name)
    parent_collection_id = None
    if project_id > 0:
        project_info = project_db.get_project_info(project_id)
        parent_collection_id = project_info["collection"]
    project_db.close()
    return parent_collection_id


def export_collection_data_to_files(db: MotionFileDatabase, skeleton_name: str, collection_id: int, directory: str):
    skeleton = db.load_skeleton(skeleton_name)
    file_list = db.get_file_list(collection_id, skeleton_name)
    if file_list is None:
        print("could not find file_list")
        return
    directory = directory+os.sep+skeleton_name
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    for file_id, name, data_type in file_list:
        export_data_to_file(db, skeleton, file_id, name, data_type, directory)


def export_collections_recursively(db: MotionFileDatabase, skeleton_name: str, collection_id: int, directory: str):
   export_collection_data_to_files(db, skeleton_name, collection_id, directory)
   for c in db.get_collection_list_by_id(collection_id):
        child_directory = directory+os.sep+ c[1]
        if not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        export_collections_recursively(db, skeleton_name, c[0], child_directory)



def export_project_to_directory(db_path, project_name, skeleton_name, directory):
    schema = DBSchema(TABLES)
    parent_collection_id = get_parent_collection(db_path, project_name)
    motion_db = MotionFileDatabase(schema)
    motion_db.connect_to_database(db_path)
    skeleton_list = [name for s_id, name, owner in motion_db.get_skeleton_list()]
    if skeleton_name not in skeleton_list:
        print("skeleton",skeleton_name,"not in skeleton list", skeleton_list)
        return
    export_collections_recursively(motion_db, skeleton_name, parent_collection_id, directory)
    motion_db.close()

if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Export data from db.')
    parser.add_argument('project_name', nargs='?', help='Project Name')
    parser.add_argument('skeleton_name', nargs='?', help='Type of skeleton already in the database.')
    parser.add_argument('directory', nargs='?', help='Directory containing BVH files')
    args = parser.parse_args()
    
    if args.skeleton_name is not None and args.directory is not None and args.project_name is not None:
        export_project_to_directory(config["db_path"], args.project_name, args.skeleton_name, args.directory)
  