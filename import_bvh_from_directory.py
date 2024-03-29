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
import bson
import bz2
import argparse
from pathlib import Path
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.project_database import ProjectDatabase
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.utils import load_json_file
from anim_utils.animation_data import BVHReader, MotionVector

CONFIG_FILE = "db_server_config.json"

def import_motion(db,new_id, skeleton_name, filename):
    bvh = BVHReader(filename)
    name = filename.split(os.sep)[-1]
    mv = MotionVector()
    mv.from_bvh_reader(bvh)
    data = mv.to_db_format()
    public = 0
    n_frames = mv.n_frames
    data =  bz2.compress(bson.dumps(data))
    meta_data = None
    db.insert_motion(new_id, skeleton_name, name, data, meta_data, n_frames, public)


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


def import_directories_recursively(db: MotionFileDatabase, skeleton_name: str, collection_id: int, path: Path):
    for child_path in path.iterdir():
        if child_path.is_dir():
            new_collection_id = db.add_new_collection_by_id(child_path.name, "collection", collection_id)
            import_directories_recursively(db, skeleton_name, new_collection_id, child_path)
        elif child_path.suffix == ".bvh":
            filename = str(child_path)
            import_motion(db, collection_id, skeleton_name, filename)

def import_directories_to_project(db_path, project_name, skeleton_name, directory):
    schema = DBSchema(TABLES)
    parent_collection_id = get_parent_collection(db_path, project_name)
    motion_db = MotionFileDatabase(schema)
    motion_db.connect_to_database(db_path)
    skeleton_list = [name for s_id, name, owner in motion_db.get_skeleton_list()]
    if skeleton_name not in skeleton_list:
        print("skeleton",skeleton_name,"not in skeleton list", skeleton_list)
        return
    directory_name = directory.split(os.sep)[-1]
    print("create collection",directory_name)
    new_collection_id = motion_db.add_new_collection_by_id(directory_name, "collection", parent_collection_id)
    parent_directory = Path(directory)
    import_directories_recursively(motion_db, skeleton_name, new_collection_id, parent_directory)
    motion_db.close()

if __name__ == "__main__":
    config = load_json_file(CONFIG_FILE)
    parser = argparse.ArgumentParser(description='Import motions to db.')
    parser.add_argument('project_name', help='Project Name')
    parser.add_argument('skeleton_name', help='Type of skeleton already in the database.')
    parser.add_argument('directory', help='Directory containing BVH files')
    args = parser.parse_args()
    
    if args.skeleton_name is not None and args.directory is not None and args.project_name is not None:
        import_directories_to_project(config["db_path"], args.project_name, args.skeleton_name, args.directory)
  