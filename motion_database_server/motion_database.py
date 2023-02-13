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
import base64
from motion_database_server.utils import get_bvh_from_str, extract_compressed_bson
from motion_database_server.project_database import ProjectDatabase
from motion_database_server.skeleton_database import SkeletonDatabase
from motion_database_server.mg_model_database import MGModelDatabase
from anim_utils.animation_data.skeleton_builder import SkeletonBuilder
from motion_database_server.experiment_database import ExperimentDatabase
from anim_utils.animation_data.motion_vector import MotionVector
from motion_database_server.character_storage import CharacterStorage
from motion_database_server.file_storage import FileStorage
from motion_database_server.model_types_database import ModleTypesDatabase
from motion_database_server.upload_buffer import UploadBuffer
from motion_database_server.schema import DBSchema, TABLES3


class MotionDatabase(ProjectDatabase, SkeletonDatabase, MGModelDatabase, CharacterStorage, FileStorage, ExperimentDatabase, ModleTypesDatabase):
    collections_table = "collections"
    motion_table = "motions"
    def __init__(self, schema=None, server_secret=None, data_dir="data"):
        if schema is None:
            schema = DBSchema(TABLES3)
        SkeletonDatabase.__init__(self)
        FileStorage.__init__(self, data_dir)
        CharacterStorage.__init__(self, data_dir + os.sep +"characters")
        MGModelDatabase.__init__(self)
        self.upload_buffer = UploadBuffer()
        ProjectDatabase.__init__(self, schema, server_secret)
    
    def load_skeletons(self):
        self.skeletons = dict()
        for skel_name, in self.tables["skeletons"].get_record_list(["name"]): 
            self.skeletons[skel_name] = self.load_skeleton(skel_name)

    def get_collection_by_name(self, name, parent=-1, owner=-1, public=-1, exact_match=False):
        filter_conditions =  [("name",name, exact_match)]
        if parent >= 0:
            filter_conditions.append(("parent",parent, True))
        if owner >= 0:
            filter_conditions.append(("owner",owner, True))
        if public >= 0:
            filter_conditions.append(("public",public, True))
        return self.tables[self.collections_table].get_record_list(["ID","name","type", "owner", "public"], filter_conditions)
    
    def get_collection_list_by_id(self, parent_id, owner=-1, public=-1):
        filter_conditions =  [("parent",parent_id)]
        intersection_list = []
        if owner >= 0:
            intersection_list.append(("owner",owner))
        if public >= 0:
            intersection_list.append(("public",public))
        return self.tables[self.collections_table].get_record_list(["ID","name","type", "owner", "public"], filter_conditions)
    
    def get_collection_tree(self, parent_id, owner=-1, public=-1):
        col_dict = dict()
        for c in self.get_collection_list_by_id(parent_id, owner, public):
            col_id = c[0]
            col_data = dict()
            col_data["name"] = c[1]
            col_data["type"] = c[2]
            col_data["owner"] = c[3]
            col_data["public"] = c[4]
            col_data["sub_tree"] = self.get_collection_tree(col_id, owner, public)
            col_dict[col_id] = col_data
        return col_dict
      
    def get_motion_by_id(self, m_id):
        r = self.tables[self.motion_table].get_record_by_id(m_id, ["data", "metaData", "skeleton"])
        data = None
        meta_data = None
        skeleton_name = ""
        if r is not None:
            data = r[0]
            meta_data = r[1]
            skeleton_name = r[2]
        else:
            print("Error in get motion by id", m_id)
        return data, meta_data, skeleton_name
      
    def get_motion_info(self, columns, clip_ids):
        if "ID" not in columns:
            columns.append("ID")
        table = self.motion_table
        records = self.query_table(table, columns, [("ID",clip_ids)])
        result = dict()
        for r in records:
            row = dict()
            r_id = -1
            for idx, col in enumerate(columns):
                if col == "ID":
                    r_id = int(r[idx])
                else:
                    row[col] = int(r[idx])
            result[r_id] = row
        return result

    def replace_motion(self, m_id, collection, skeleton_name, name, motion_data, meta_data, processed=None):
        record_data = dict()
        if collection is not None:
            record_data["collection"] = collection
        if skeleton_name is not None:
            record_data["skeleton"] = skeleton_name
        if name is not None:
            record_data["name"] = name
        if motion_data is not None:
            record_data["data"] = motion_data
        if meta_data is not None:
            record_data["metaData"] = meta_data
        if processed is not None:
            record_data["processed"] = processed
        self.tables[self.motion_table].update_record(m_id, record_data)

    def get_collection_by_id(self, collection_id):
        return self.tables[self.collections_table].get_record_by_id(collection_id,["ID","name","type", "parent"])

    def replace_collection(self, input_data, collection_id):
        self.tables[self.collections_table].update_record(collection_id, input_data)
       
    def get_motion_list_by_collection(self, collection, skeleton=None, processed=None):
        filter_conditions =[("collection",str(collection))]
        if skeleton is not None:
            filter_conditions+=[("skeleton", skeleton)]
        if processed is not None:
            filter_conditions+=[("processed", processed)]
        return self.tables[self.motion_table].get_record_list( ["ID","name"], filter_conditions)

    def get_motion_list_by_name(self, name, skeleton=None, processed=None, exact_match=False):
        filter_conditions =[]
        if skeleton is not None:
            filter_conditions+=[("skeleton", skeleton)]
        if processed is not None:
            filter_conditions+=[("processed", processed)]
        r = self.query_table(self.motion_table, ["ID","name"], filter_conditions)
        return self.tables[self.motion_table].search_records_by_name(name, ["ID","name"], exact_match, filter_conditions)

   
    def upload_motion(self, part_idx, n_parts, collection, skeleton_name, name, base64_data_str, meta_data, processed=0):
        print("upload motion", name)
        self.upload_buffer.update_buffer(name, part_idx, n_parts,base64_data_str)
        if not self.upload_buffer.is_complete(name):
            return
        base64_data_str = self.upload_buffer.get_data(name)
        self.upload_buffer.delete_data(name)

        #extract n frames
        data = base64.decodebytes(base64_data_str.encode('utf-8'))
        data = extract_compressed_bson(data)
        n_frames = 0
        if "poses" in data:
            n_frames = len(data["poses"])
        data = bson.dumps(data)
        data = bz2.compress(data)
        return self.insert_motion(collection, skeleton_name, name, data, meta_data, n_frames, processed)

    def load_motion_vector_from_bvh_str(self, bvh_str):
        bvh_reader = get_bvh_from_str(bvh_str)
        animated_joints = list(bvh_reader.get_animated_joints())
        motion_vector = MotionVector()
        motion_vector.from_bvh_reader(bvh_reader, False)
        motion_vector.skeleton = SkeletonBuilder().load_from_bvh(bvh_reader, animated_joints)
        return motion_vector

    def upload_bvh_clip(self, collection, skeleton_name, name, bvh_str):
        motion_vector = self.load_motion_vector_from_bvh_str(bvh_str)
        data = motion_vector.to_db_format()
        n_frames = len(data["poses"])
        data = bson.dumps(data)
        data = bz2.compress(data)
        self.insert_motion(collection, skeleton_name, name, data, None, n_frames)
            
    def insert_motion(self, collection, skeleton_name, name, motion_data, meta_data, n_frames, processed=0):
        record_data = dict()
        record_data["name"] = name
        record_data["collection"] = collection
        record_data["skeleton"] = skeleton_name
        record_data["numFrames"] = n_frames
        record_data["data"] = motion_data
        if meta_data is not None:
            record_data["metaData"] = meta_data
        record_data["processed"] = processed
        return self.tables[self.motion_table].create_record(record_data)

    def delete_motion_by_id(self, motion_id):
        return self.tables[self.motion_table].delete_record_by_id(motion_id)

    def add_new_collection_by_id(self, name, collection_type, parent_id, owner, public=0):
        owner = max(0, owner)
        record_data = dict()
        record_data["name"] = name
        record_data["type"] = collection_type
        record_data["parent"] = parent_id
        record_data["owner"] = owner
        record_data["public"] = public
        return self.tables[self.collections_table].create_record(record_data)

    def remove_collection_by_id(self, collection_id):
        return self.tables[self.collections_table].delete_record_by_id(collection_id)

    def get_owner_of_collection(self, collection_id):
        return self.tables[self.collections_table].get_value_of_column_by_id(collection_id, "owner")

    def get_owner_of_motion(self, motion_id):
        collection_id = self.tables[self.motion_table].get_value_of_column_by_id(motion_id, "collection")
        if collection_id is None:
            return None
        return self.get_owner_of_collection(collection_id)
