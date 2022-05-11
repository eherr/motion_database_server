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
        records = self.query_table(self.skeleton_table,[ "data", "metaData"], [("name", name)])
        data = None
        meta_data = None
        if len(records) > 0:
            data = records[0][0]
            meta_data = records[0][1]
        return data, meta_data

    def get_skeleton_list(self):
        r = self.query_table(self.skeleton_table, ["ID","name", "owner"], [])
        return r

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

    def replace_skeleton(self, name, skeleton_data=b"x00", meta_data=b"x00"):
        print("replace skeleton", name)
        if name != "":
            data = dict()
            if name != "":
                data["name"] = name
            if skeleton_data != b"x00":
                data["data"] = skeleton_data
            if meta_data != b"x00":
                data["metaData"] = meta_data
            self.update_entry(self.skeleton_table, data, "name", name)
            print("load skeleton")
            self.skeletons[name] = self.load_skeleton(name)


    def load_skeleton_legacy(self, skeleton_name):
        skeleton = None
        bvh_str, skeleton_model = self.get_skeleton_by_name_legacy(skeleton_name)

        ref_bvh = get_bvh_from_str(bvh_str)
        animated_joints = list(ref_bvh.get_animated_joints())
        n_joints = len(animated_joints)
        print("animated joints", len(animated_joints))
        if n_joints > 0:
            skeleton = SkeletonBuilder().load_from_bvh(ref_bvh, animated_joints, skeleton_model=skeleton_model)
        return skeleton

    def get_skeleton_by_name_legacy(self, name):
        records = self.query_table(self.skeleton_table,[ "BVHString", "model"], [("name", name)])
        #recordsrecords = self.get_skeleton_by_name(skeleton_table, name)
        bvh_str = ""
        model_str = ""
        if len(records) > 0:
            bvh_str = records[0][0]
            model_str = records[0][1]
        return bvh_str, model_str