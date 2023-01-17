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
import bson
import bz2
import base64
import numpy as np
import jwt
from motion_database_server.utils import get_bvh_from_str, extract_compressed_bson, get_bvh_string, save_json_file
from motion_database_server.user_database import UserDatabase
from motion_database_server.skeleton_database import SkeletonDatabase
from anim_utils.animation_data.skeleton_builder import SkeletonBuilder
from anim_utils.animation_data.motion_vector import MotionVector
from motion_database_server.character_storage import CharacterStorage
from motion_database_server.file_storage import FileStorage
from motion_database_server.upload_buffer import UploadBuffer
from morphablegraphs.motion_model.motion_primitive_wrapper import MotionPrimitiveModelWrapper
from morphablegraphs.utilities import convert_to_mgrd_skeleton
from motion_database_server.schema import DBSchema, TABLES3
JWT_ALGORITHM = 'HS256'



class MotionDatabase(UserDatabase, SkeletonDatabase, CharacterStorage, FileStorage):
    collections_table = "collections"
    motion_table = "motion_clips"
    preprocessed_table = "preprocessed_data"
    model_table = "models"
    graph_table = "graphs"
    def __init__(self, schema=None, server_secret=None, data_dir="data"):
        if schema is None:
            schema = DBSchema(TABLES3)
        self.schema = schema
        self.upload_buffer = UploadBuffer()
        SkeletonDatabase.__init__(self)
        self._mp_buffer = dict()
        self._mp_skeleton_type = dict()
        self.jwt = jwt.JWT()
        if server_secret is not None:
            self.server_secret = jwt.jwk.OctetJWK(bytes(server_secret, "utf-8"))
        else:
            self.server_secret = None
        self.enforce_access_rights = server_secret is not None
        FileStorage.__init__(self,data_dir)
        CharacterStorage.__init__(self, data_dir + os.sep +"characters")
    
    def connect(self, path):
        self.connect_to_database(path)
        print(path)
    
    def load_skeletons(self):
        self.skeletons = dict()
        for skel_id, skel_name, owner in self.get_skeleton_list():
            self.skeletons[skel_name] = self.load_skeleton(skel_name)

    def create_database(self, path):
        self.connect_to_database(path)
        self.schema.create_tables(self)
        print("created database",path)

    def init_database(self, path, recreate=False):
        create_db = not os.path.isfile(path)
        if create_db or recreate:
            self.create_database(path)
        else:
            self.connect_to_database(path)

    def delete_files_of_entry(self, table_name, filter_conditions, data_cols):
        data_records = self.query_table(table_name, data_cols, filter_conditions)
        if len(data_records) <1:
            return
        for data_file_name in data_records[0]:
            self.delete_data_file(table_name, data_file_name)

    def delete_entry_by_id(self, table_name, entry_id):
        filter_conditions = [("ID",entry_id)]
        data_cols = self.schema.get_data_cols(table_name)
        if len(data_cols) > 0:
            self.delete_files_of_entry(table_name, filter_conditions, data_cols)
        super().delete_entry_by_id(table_name, entry_id)
    

    def get_collection_by_name(self, name, parent=-1, owner=-1, public=-1, exact_match=False):
        filter_conditions =  [("name",name, exact_match)]
        intersection_list = None
        if parent >= 0:
            filter_conditions.append(("parent",parent, True))
        if owner >= 0:
            filter_conditions.append(("owner",owner, True))
        if public >= 0:
            filter_conditions.append(("public",public, True))
        collection_records = self.query_table(self.collections_table, ["ID","name","type", "owner", "public"],filter_conditions, intersection_list)
        return collection_records
    
    def get_collection_list_by_id(self, parent_id, owner=-1, public=-1):
        filter_conditions =  [("parent",parent_id)]
        intersection_list = []
        if owner >= 0:
            intersection_list.append(("owner",owner))
        if public >= 0:
            intersection_list.append(("public",public))
        collection_records = self.query_table(self.collections_table, ["ID","name","type", "owner", "public"],filter_conditions, intersection_list)
        return collection_records
    
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
        r = self.query_table(self.motion_table, ["data", "metaData", "skeleton"], [("ID",m_id)])
        data = None
        meta_data = None
        skeleton_name = ""
        
        if len(r) > 0:
            data = self.load_data_file(self.motion_table, r[0][0])
            meta_data = self.load_data_file(self.motion_table, r[0][1])
            skeleton_name = r[0][2]
        else:
            print("Error in get motion by id", m_id)
        return data, meta_data, skeleton_name
      
    def get_motion_info(self, columns, clip_ids, is_processed=False):
        if "ID" not in columns:
            columns.append("ID")
        table = self.motion_table
        if is_processed:
            table = self.preprocessed_table
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


    def replace_motion(self, m_id, collection, skeleton_name, name, motion_data, meta_data):
        data = dict()
        if collection is not None:
            data["collection"] = collection
        if skeleton_name is not None:
            data["skeleton"] = skeleton_name
        if name is not None:
            data["name"] = name
        if motion_data is not None:
            data["data"] = self.save_hashed_file(self.motion_table, "data", motion_data)
        if meta_data is not None:
            data["metaData"] = self.save_hashed_file(self.motion_table, "metaData", meta_data) 
        self.update_entry(self.motion_table, data, "ID", m_id)

    def get_preprocessed_data_by_id(self, m_id):
        r = self.query_table(self.preprocessed_table, ["data", "metaData", "skeleton"], [("ID",m_id)])
        data = None
        meta_data = None
        
        if len(r) > 0:
            data = self.load_data_file(self.preprocessed_table, r[0][0])
            meta_data = self.load_data_file(self.preprocessed_table, r[0][1]) 
            skeleton_name = r[0][2]
        else:
            print("Error in get processed data", m_id)
        return data, meta_data, skeleton_name

    def get_model_by_id(self, m_id):
        r = self.query_table(self.model_table, ["data", "metaData", "skeleton"], [("ID",m_id)])
        skeleton_name = ""
        data = None
        if len(r) > 0:
            data = self.load_data_file(self.model_table, r[0][0])
            cluster_tree_data = self.load_data_file(self.model_table, r[0][1])
            skeleton_name = r[0][2]
        else:
            print("Error in get model data",m_id)
        return data, cluster_tree_data, skeleton_name

    def replace_preprocessed_data(self, m_id, collection, skeleton_name, name, motion_data, meta_data):
        data = dict()
        if collection != "":
            data["collection"] = collection
        if skeleton_name != "":
            data["skeleton"] = skeleton_name
        if name != "":
            data["name"] = name
        if motion_data != "":
            data["data"] = self.save_hashed_file(self.motion_table, "data", motion_data)
        if meta_data != "":
            data["metaData"] = self.save_hashed_file(self.motion_table, "metaData", meta_data) 
        self.update_entry(self.preprocessed_table, data, "ID", str(m_id))
    
    def get_collection_by_id(self, collection_id):
        filter_conditions =  [("ID",collection_id)]
        collection_records = self.query_table(self.collections_table, ["ID","name","type", "parent"],filter_conditions)
        collection = None
        if len(collection_records) > 0:
            collection = collection_records[0]
        return collection

    def replace_collection(self, input_data, collection_id):
        data = dict()
        if "name" in input_data:
            data["name"] = input_data["name"]
        if "parent" in input_data:
            data["parent"] = input_data["parent"]
        if "type" in input_data:
            data["type"] = input_data["type"]
        if "owner" in input_data:
            data["owner"] = input_data["owner"]
        if "public" in input_data:
            data["public"] = input_data["public"]
        self.update_entry(self.collections_table, data, "id", collection_id)

    def get_motion_list_by_collection(self, collection, skeleton=""):
        filter_conditions =[("collection",str(collection))]
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        r = self.query_table(self.motion_table, ["ID","name"], filter_conditions)
        return r

    def get_motion_list_by_name(self, name, skeleton="", exact_match=False):
        filter_conditions =[("name", name, exact_match)]
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        r = self.query_table(self.motion_table, ["ID","name"], filter_conditions)
        return r

    def get_preprocessed_data_list_by_collection(self, collection, skeleton=""):
        filter_conditions =[("collection",str(collection))]
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        r = self.query_table(self.preprocessed_table, ["ID","name"], filter_conditions)
        return r

    def get_model_list_by_collection(self, collection, skeleton=""):
        filter_conditions =[("collection",str(collection))]
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        r = self.query_table(self.model_table, ["ID","name"], filter_conditions)
        return r

    def get_graph_list(self, skeleton=""):
        filter_conditions = []
        if skeleton != "":
            filter_conditions+=[("skeleton", skeleton)]
        r = self.query_table(self.graph_table, ["ID","name"], filter_conditions)
        return r
    
    def add_new_graph(self, name, skeleton, data):
        data_file = self.save_hashed_file(self.graph_table, "data", data)
        records = [(name, skeleton, data_file)]
        print("add graph",records)
        self.insert_records(self.graph_table, ["name", "skeleton", "data"], records)
        records = self.get_max_id(self.graph_table)
        new_id = -1
        if len(records) > 0:
            new_id = int(records.iloc[0]["ID"])
        return new_id

    def replace_graph(self, graph_id, input_data):
        data = dict()
        if "name" in input_data:
            data["name"] = input_data["name"]
        if "skeleton" in input_data:
            data["skeleton"] = input_data["skeleton"]
        if "data" in input_data:
            graph_data = bz2.compress(bson.dumps(input_data["data"]))
            data["data"] = self.save_hashed_file(self.graph_table, "data",  graph_data)
        self.update_entry(self.graph_table, data, "id", graph_id)

    def get_graph_by_id(self, graph_id):
        r = self.query_table(self.graph_table, ["skeleton","data"], [("ID", graph_id)])
        return r

    def remove_graph_by_id(self, graph_id):
        return self.delete_entry_by_id(self.graph_table, graph_id)

    def upload_motion(self, part_idx, n_parts, collection, skeleton_name, name, base64_data_str, meta_data, is_processed=False):
        print("upload motion", name)
        self.upload_buffer.update_buffer(name, part_idx, n_parts,base64_data_str)
        if self.upload_buffer.is_complete(name):
            #self._insert_motion_from_buffer_to_db(name, collection, skeleton_name, meta_data, is_processed)
            base64_data_str = self.buffer.get_data(name)
            self.delete_data(name)

            #extract n frames
            data = base64.decodebytes(base64_data_str.encode('utf-8'))
            data = extract_compressed_bson(data)
            n_frames = 0
            if "poses" in data:
                n_frames = len(data["poses"])
            data = bson.dumps(data)
            data = bz2.compress(data)

            if is_processed:
                return self.insert_preprocessed_data(collection, skeleton_name, name, data, meta_data)
            else:
                return self.insert_motion(collection, skeleton_name, name, data, meta_data, n_frames)

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
        data_file = self.save_hashed_file(self.motion_table, "data", data)
        m_records = [(name, skeleton_name, collection, data_file, n_frames)]
        #motion_vector.export(motion_vector.skeleton, "out_mv.bvh")
        self.insert_records(self.motion_table, ["name", "skeleton","collection","data","numFrames"], m_records)
            
    def insert_motion(self, collection, skeleton_name, name, data, meta_data, n_frames):
        data_file = self.save_hashed_file(self.preprocessed_table, "data", data)
        meta_data_file = self.save_hashed_file(self.preprocessed_table, "metaData", meta_data)
        m_records = [(name, skeleton_name, collection, data_file, meta_data_file, n_frames)]
        self.insert_records(self.motion_table, ["name", "skeleton","collection","data", "metaData", "numFrames"], m_records)

    def insert_preprocessed_data(self, collection, skeleton_name, name, data, meta_data):
        data_file = self.save_hashed_file(self.preprocessed_table, "data", data)
        meta_data_file = self.save_hashed_file(self.preprocessed_table, "metaData", meta_data)
        m_records = [(name, skeleton_name, collection, data_file, meta_data_file)]
        self.insert_records(self.preprocessed_table, ["name", "skeleton","collection","data","metaData"], m_records)
        

    def delete_motion_by_id(self, motion_id):
        return self.delete_entry_by_id(self.motion_table, motion_id)

    def delete_preprocessed_data(self, motion_id):
        return self.delete_entry_by_id(self.preprocessed_table, motion_id)

    def add_new_collection_by_id(self, name, collection_type, parent_id, owner, public=0):
        owner = max(0, owner)
        records = [(name, collection_type, parent_id, owner, public)]
        self.insert_records(self.collections_table, ["name", "type", "parent", "owner", "public"], records)
        records = self.get_max_id(self.collections_table)
        new_id = -1
        if len(records) > 0:
            new_id = int(records.iloc[0]["ID"])
        return new_id

    def remove_collection_by_id(self, motion_id):
        return self.delete_entry_by_id(self.collections_table, motion_id)

    def upload_motion_model(self, name, mp_name, skeleton, model_data):
        records = []
        data_file = self.save_hashed_file(self.motion_table, "data", model_data)
        row = (name, mp_name, skeleton, data_file)
        records.append(row)
        self.insert_records(self.model_table, ["name", "collection","skeleton", "data"], records)
        records = self.get_max_id(self.model_table)
        new_id = -1
        if len(records) > 0:
            new_id = int(records.iloc[0]["ID"])
        return new_id


    def upload_cluster_tree(self, model_id, cluster_tree_data):
        data = dict()
        data["metaData"] = self.save_hashed_file(self.motion_table, "metaData", cluster_tree_data)
        self.update_entry(self.model_table, data, "ID", str(model_id))

    def remove_skeleton(self, name):
        filter_conditions = [("name",name)]
        data_cols = self.schema.get_data_cols(self.skeleton_table)
        self.delete_files_of_entry(self.skeleton_table, filter_conditions, data_cols)
        self.delete_entry_by_name(self.skeleton_table, name)

    def delete_model_by_id(self, m_id):
        self.delete_entry_by_id(self.model_table, m_id)

    def get_motion_primitive_sample(self, model_id):
        mv = None
        if model_id not in self._mp_buffer:
            data, cluster_tree_data, skeleton_name = self.get_model_by_id(model_id)
            data = extract_compressed_bson(data)
            self._mp_buffer[model_id] = MotionPrimitiveModelWrapper()
            mgrd_skeleton = convert_to_mgrd_skeleton(self.skeletons[skeleton_name])
            self._mp_buffer[model_id]._initialize_from_json(mgrd_skeleton, data)
            self._mp_skeleton_type[model_id] = skeleton_name
        if self._mp_buffer[model_id] is not None:
            skeleton_name = self._mp_skeleton_type[model_id]
            mv = self._mp_buffer[model_id].sample(False).get_motion_vector()
            # mv = self._mp_buffer[action_name].skeleton.add_fixed_joint_parameters_to_motion(mv)
            animated_joints = self._mp_buffer[model_id].get_animated_joints()
            new_quat_frames = np.zeros((len(mv), self.skeletons[skeleton_name].reference_frame_length))
            for idx, reduced_frame in enumerate(mv):
                new_quat_frames[idx] = self.skeletons[skeleton_name].add_fixed_joint_parameters_to_other_frame(reduced_frame,
                                                                                            animated_joints)
            mv = new_quat_frames
        return mv

    def get_motion_vector_from_random_sample(self, model_id):
        frames = self.get_motion_primitive_sample(model_id)
        motion_vector = MotionVector()
        motion_vector.frames = frames
        motion_vector.n_frames = len(frames)
        skeleton_type = self._mp_skeleton_type[model_id]
        motion_vector.skeleton = self.skeletons[skeleton_type]
        return motion_vector, skeleton_type

    def check_rights(self, session):
        if self.enforce_access_rights and "user" in session and "token" in session:
            token = session["token"]
            payload = self.jwt.decode(token, self.server_secret)
            if "username" in payload:
                return payload["username"] == session["user"]
            else:
                return False
        else:
            return not self.enforce_access_rights
    

    def get_owner_of_collection(self, collection_id):
        owner = None
        r = self.query_table(self.collections_table, ["owner"], [("ID", collection_id)])
        if len(r) > 0:
            owner = r[0][0]
        return owner

    def get_owner_of_motion(self, motion_id):
        owner = None
        r = self.query_table(self.motion_table, ["collection"], [("ID", motion_id)])
        if len(r) > 0:
            collection_id = r[0][0]
            owner = self.get_owner_of_collection(collection_id)
        return owner    
    
    def get_owner_of_model(self, model_id):
        owner = None
        r = self.query_table(self.model_table, ["collection"], [("ID", model_id)])
        if len(r) > 0:
            collection_id = r[0][0]
            owner = self.get_owner_of_collection(collection_id)
        return owner

    def get_owner_of_skeleton(self, skeleton_name):
        owner = None
        r = self.query_table(self.skeleton_table, ["owner"], [("name", skeleton_name)])
        if len(r) > 0:
            owner = r[0][0]
        return owner



