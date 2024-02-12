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
from motion_database_server.database_wrapper import DatabaseWrapper
from motion_database_server.files_database import FilesDatabase
from motion_database_server.collection_database import CollectionDatabase
from motion_database_server.skeleton_database import SkeletonDatabase
from motion_database_server.model_graph_database import ModelGraphDatabase
from motion_database_server.mg_model_database import MGModelDatabase
from anim_utils.animation_data.skeleton_builder import SkeletonBuilder
from anim_utils.animation_data.motion_vector import MotionVector
from motion_database_server.character_storage import CharacterStorage
from motion_database_server.file_storage import FileStorage
from motion_database_server.upload_buffer import UploadBuffer
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.table import Table
from motion_database_server.utils import load_json_file
from motion_db_interface.model_db_session import ModelDBSession
from motion_db_interface.model_registry import ModelRegistry


def load_motion_vector_from_bvh_str(bvh_str):
    bvh_reader = get_bvh_from_str(bvh_str)
    animated_joints = list(bvh_reader.get_animated_joints())
    motion_vector = MotionVector()
    motion_vector.from_bvh_reader(bvh_reader, False)
    motion_vector.skeleton = SkeletonBuilder().load_from_bvh(bvh_reader, animated_joints)
    return motion_vector


class MotionFileDatabase(DatabaseWrapper, CollectionDatabase, FileStorage, FilesDatabase, SkeletonDatabase, ModelGraphDatabase, MGModelDatabase, CharacterStorage):
    
    def __init__(self, schema=None, data_dir="data",port=8888):
        if schema is None:
            schema = DBSchema(TABLES)
        self.schema =schema
        self.tables = dict()
        for name in self.schema.tables:
            self.tables[name] = Table(self, name, self.schema.tables[name])
        SkeletonDatabase.__init__(self)
        FileStorage.__init__(self, data_dir)
        CharacterStorage.__init__(self, data_dir + os.sep +"characters")
        MGModelDatabase.__init__(self)
        self.model_loader = ModelRegistry.get_instance()
        #ProjectDatabase.__init__(self, schema, server_secret)
        self.upload_buffer = UploadBuffer()
        #create local session for data transforms
        session_file = "session.json"
        if os.path.isfile(session_file):
            session_data = load_json_file(session_file)
            session = ModelDBSession("http://localhost:" + str(port) + "/", session_data)
    
    def load_skeletons(self):
        self.skeletons = dict()
        for skel_name, in self.tables["skeletons"].get_record_list(["name"]): 
            self.skeletons[skel_name] = self.load_skeleton(skel_name)

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

    def upload_bvh_clip(self, collection, skeleton_name, name, bvh_str):
        motion_vector = load_motion_vector_from_bvh_str(bvh_str)
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
        record_data["dataType"] = "motion"
        if processed:
            record_data["dataType"] = "aligned_motion"
        return self.create_file(record_data)

    def get_motion_by_id(self, m_id):
        r = self.tables[self.files_table].get_record_by_id(m_id, ["data", "metaData", "skeleton"])
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
        records = self.query_table(self.files_table, columns, [("ID",clip_ids)])
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
       
    def get_motion_list_by_collection(self, collection, skeleton=None, processed=None):
        filter_conditions =[("collection",str(collection))]
        if skeleton is not None:
            filter_conditions+=[("skeleton", skeleton)]
        if processed is not None and processed:
            filter_conditions+=[("dataType", "aligned_motion")]
        else:
            filter_conditions+=[("dataType", "motion")]
        return self.tables[self.files_table].get_record_list( ["ID","name"], filter_conditions)

    def get_motion_list_by_name(self, name, skeleton=None, processed=None, exact_match=False):
        filter_conditions =[]
        if skeleton is not None:
            filter_conditions+=[("skeleton", skeleton)]
        if processed is not None and processed:
            filter_conditions+=[("dataType", "aligned_motion")]
        else:
            filter_conditions+=[("dataType", "motion")]
        return self.tables[self.files_table].search_records_by_name(name, ["ID","name"], exact_match, filter_conditions)

   
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
    
    def get_motion_from_file(self, file_id):
        record = self.tables[self.files_table].get_record_by_id(file_id, ["data", "dataType", "skeleton"])
        data, data_type = None, None
        if record is None:
            print("Error in get motion by id", file_id)
            return data
        
        data, data_type, skeleton_name = record
        data_type_info = self.get_data_loader_info(data_type, "db")
        if data_type_info is None:
            return data
        return self.sample_motion_from_model(data, data_type_info["script"], data_type, skeleton_name)
    
    def sample_motion_from_model(self, model_data, loader_script, data_type, skeleton_name):
        print("motion_from_model", data_type)
        loader_script = loader_script.replace("\r\n", "\n")
        self.model_loader.load_dynamic_module(data_type, loader_script)
        skeleton = self.get_skeleton(skeleton_name)
        data = self.model_loader.sample_motion_from_model(data_type, model_data, skeleton)
        data = bson.dumps(data)
        data = bz2.compress(data)
        return data
    