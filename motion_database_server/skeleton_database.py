#!/usr/bin/env python
#
# Copyright 2022 DFKI GmbH.
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
from motion_database_server.utils import extract_compressed_bson, get_bvh_from_str
from anim_utils.animation_data.skeleton_builder import SkeletonBuilder

class SkeletonDatabase(object):
    skeleton_table ="skeletons"
    def __init__(self) -> None:
        self.skeletons = dict()
    
    def load_skeleton(self, skeleton_name):
        data, skeleton_model = self.get_skeleton_by_name(skeleton_name)
        if data is not None:
            data = extract_compressed_bson(data)
            #print("load default", len(data["referencePose"]["rotations"]))
            skeleton = SkeletonBuilder().load_from_custom_unity_format(data, add_extra_end_site=False)
        
        if skeleton_model is not None:
            try:
                skeleton_model = bz2.decompress(skeleton_model)
                skeleton_model = bson.loads(skeleton_model)
                skeleton.skeleton_model = skeleton_model
            except Exception as e:
                print("Could not load skeleton model", e.args)
        return skeleton
    
    def add_new_skeleton(self, name, data=b"x00", meta_data=b"x00", owner=1):
        skeleton_list = self.get_name_list(self.skeleton_table)
        if name != "" and name not in skeleton_list.values:
            records = [(name, data, meta_data, owner)]
            self.insert_records(self.skeleton_table, ["name", "data", "metaData", "owner"], records)
            self.skeletons[name] = self.load_skeleton(name)
            return True
        else:
            print("Error: skeleton already exists")
            return False

    def get_skeleton_by_name(self, name):
        record = self.tables[self.skeleton_table].get_record_by_name(name, ["data", "metaData"])
        data = None
        meta_data = None
        if record is not None:
            data = self.load_data_file(self.skeleton_table, record[0])
            meta_data = self.load_data_file(self.skeleton_table, record[1])
        return data, meta_data

    def get_skeleton_list(self):
        return self.tables[self.skeleton_table].get_record_list(["ID","name", "owner"])

    def get_skeleton(self, skeleton_type):
        if skeleton_type in self.skeletons:
            return self.skeletons[skeleton_type]
        else:
            return None

    def load_skeleton_from_bvh_str(self, bvh_str):
        bvh_reader = get_bvh_from_str(bvh_str)
        animated_joints = list(bvh_reader.get_animated_joints())
        skeleton = SkeletonBuilder().load_from_bvh(bvh_reader, animated_joints)
        return skeleton

    def remove_skeleton(self, name):
        self.delete_entry_by_name(self.skeleton_table, name)

    def replace_skeleton(self, name, skeleton_data=None, meta_data=None):
        print("replace skeleton", name)
        if name != "":
            data = dict()
            if name != "":
                data["name"] = name
            if skeleton_data  is not None:
                data["data"] = self.save_hashed_file(self.skeleton_table, "data", skeleton_data) 
            if meta_data is not None:
                data["metaData"] = self.save_hashed_file(self.skeleton_table, "metaData", meta_data) 
            
            self.tables[self.skeleton_table].update_record_by_name(name, data)
            print("load skeleton")
            self.skeletons[name] = self.load_skeleton(name)

    def remove_skeleton(self, name):
        self.tables[self.skeleton_table].delete_record_by_name(name)
