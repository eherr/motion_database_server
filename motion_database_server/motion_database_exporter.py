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
from motion_database_server.utils import get_bvh_from_str, extract_compressed_bson, get_bvh_string, save_json_file

from anim_utils.animation_data.motion_vector import MotionVector

class MotionDatabaseExporter:
    def export_database_to_folder(self, out_dir, parent_name=None):
        os.makedirs(out_dir, exist_ok=True)
        self.export_skeletons(out_dir)
        parent_id = 0
        if parent_name is not None:
            col = self.get_collection_by_name(parent_name)
            if len(col) > 0:
                parent_id = col[0][0]
                print("parent", parent_id)
        for skeleton_name in self.skeletons:
            self.export_motion_data(skeleton_name, out_dir+os.sep+"raw", parent=parent_id)
            #self.export_processed_motion_data(skeleton_name, out_dir+os.sep+"processed", parent=parent_id)

    def export_skeletons(self, out_dir):
        for skeleton_name in self.skeletons:
            self.skeletons[skeleton_name] = self.load_skeleton(skeleton_name)
            skeleton_data = self.skeletons[skeleton_name].to_unity_format()
            skeleton_data["skeleton_model"] = self.skeletons[skeleton_name].skeleton_model
            skeleton_data["name"] = skeleton_name
            save_json_file(skeleton_data, out_dir + os.sep+skeleton_name+".skeleton")
            
    def export_motion_data(self, skeleton_name, out_dir, parent=0):
        for col in self.get_collection_list_by_id(parent):
            print(col)
            col_id, col_name, col_type, owner, public = col
            action_dir = out_dir+os.sep+col_name
            os.makedirs(action_dir, exist_ok=True)
            self.export_collection_clips_to_folder(col_id, skeleton_name, action_dir)
            self.export_motion_data(skeleton_name, action_dir, col_id)

    def export_processed_motion_data(self, skeleton_name, out_dir, parent=0):
        for col in self.get_collection_list_by_id(parent):
            col_id, col_name, col_type, owner, public = col
            action_dir = out_dir+os.sep+col_name
            os.makedirs(action_dir, exist_ok=True)
            self.export_processed_collection_data_to_folder(col_id, skeleton_name, action_dir)
            self.export_processed_motion_data(skeleton_name, action_dir, col_id)

    def export_collection(self, path_str, skeleton_name, out_dir):
        paths = path_str.split("/")
        parent = 0
        level = 0
        path_depth = len(paths)
        for name in paths:
            # find collection by name with parent as filter
            collections = self.get_collection_list_by_id(parent)
            for c_id, c_name, c_type, c_owner in collections:
                if c_name == name:
                    parent = c_id
                    level +=1
                    break

        if level == path_depth: # succes
            print("found path", parent, path_depth)
            self.export_collection_clips_to_folder(parent, skeleton_name, out_dir)
        else:
            print("could not find path", level)            
        return

    def export_collection_clips_to_folder(self, c_id, skeleton_name, directory):
        skeleton = self.load_skeleton(skeleton_name)
        motion_list = self.get_motion_list_by_collection(c_id, skeleton_name)
        if motion_list is None:
            print("could not find motions")
            return
        n_motions = len(motion_list)
        if n_motions < 1:
            print("no motions", c_id)
            return
        directory = directory+os.sep+skeleton_name
        if not os.path.isdir(directory):
            os.makedirs(directory)
        count = 1
        for motion_id, name in motion_list:
            print("download motion", str(count)+"/"+str(n_motions), name)
            self.export_motion_clip(skeleton, motion_id, name, directory, export_annotation=True)
            count+=1

    def export_processed_collection_data_to_folder(self, c_id, skeleton_name, directory):
        skeleton = self.load_skeleton(skeleton_name)
        motion_list = self.get_motion_list_by_collection(c_id, skeleton_name, processed=1)
        if motion_list is None:
            print("could not find motions")
            return
        n_motions = len(motion_list)
        if n_motions < 1:
            print("no motions", c_id)
            return
        directory = directory+os.sep+skeleton_name
        if not os.path.isdir(directory):
            os.makedirs(directory)
        count = 1
        for motion_id, name in motion_list:
            print("download motion", str(count)+"/"+str(n_motions), name)
            self.export_motion_clip(skeleton, motion_id, name, directory, export_annotation=True)
            count+=1


    def export_motion_clip(self, skeleton, motion_id, name, directory, export_annotation=False):
        print("export clip")
        data, meta_data, skeleton_name = self.get_motion_by_id(motion_id)
        if data is None:
            return
        motion_dict = extract_compressed_bson(data)
        motion_vector = MotionVector()
        motion_vector.from_custom_db_format(motion_dict)
        try:
            bvh_str = get_bvh_string(skeleton, motion_vector.frames)
            filename = directory+os.sep+name
            if not name.endswith(".bvh"):
                filename += ".bvh"
            with open(filename, "wt") as out_file:
                out_file.write(bvh_str)
            print("wrote file", filename)
        except Exception as e :
            print("Error: writing file", motion_id, name, e.args)
            pass
            return
        if export_annotation and meta_data is not None and meta_data != b"x00" and meta_data != "":
            meta_filename = filename+".meta"
            try:
                meta_data = bz2.decompress(meta_data)
                meta_data = bson.loads(meta_data)
                save_json_file(meta_data, meta_filename)
            except:
                print("Error could not decode",meta_data)
                pass
