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
import numpy as np
import pandas as pd
from db_utils import DataBaseConnection
from anim_utils.animation_data.bvh import BVHReader, BVHWriter
from anim_utils.animation_data.skeleton_builder import SkeletonBuilder
from anim_utils.animation_data.motion_vector import MotionVector
from morphablegraphs.motion_model.motion_primitive_wrapper import MotionPrimitiveModelWrapper
from morphablegraphs.utilities import convert_to_mgrd_skeleton
import hashlib
import jwt


def get_bvh_string(skeleton, frames):
    print("generate bvh string", len(skeleton.animated_joints))
    frames = np.array(frames)
    frames = skeleton.add_fixed_joint_parameters_to_motion(frames)
    frame_time = skeleton.frame_time
    bvh_writer = BVHWriter(None, skeleton, frames, frame_time, True)
    return bvh_writer.generate_bvh_string()

def get_bvh_from_str(bvh_str):
    bvh_reader = BVHReader("")
    lines = bvh_str.split("\\n")
    lines = [l for l in lines if len(l) > 0]
    bvh_reader.process_lines(lines)
    return bvh_reader

INT_T = "INTERGER"
BLOB_T = "BLOB"
TEXT_T = "TEXT"

LEGACY_TABLES = dict()
LEGACY_TABLES["collections"] = [("name",TEXT_T),
                    ("type",TEXT_T), 
                    ("owner",TEXT_T), 
                    ("parent",INT_T)]
LEGACY_TABLES["skeletons"] = [("name",TEXT_T),
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
LEGACY_TABLES["motion_clips"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeletonType",INT_T), 
                    ("quaternionFrames",TEXT_T), 
                    ("metaInfo",TEXT_T)]
LEGACY_TABLES["models"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
LEGACY_TABLES["graphs"] = [("name",TEXT_T),
                    ("skeleton",INT_T), 
                    ("data",BLOB_T)]


TABLES = dict()
TABLES["collections"] = [("name",TEXT_T),
                    ("type",TEXT_T), 
                    ("owner",TEXT_T), 
                    ("parent",INT_T)]
TABLES["skeletons"] = [("name",TEXT_T),
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
TABLES["motion_clips"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T), 
                    ("subject",TEXT_T), 
                    ("source",TEXT_T), 
                    ("numFrames",INT_T),
                    ("public",INT_T)]
TABLES["preprocessed_data"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T), 
                    ("source",TEXT_T)]
TABLES["models"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
TABLES["graphs"] = [("name",TEXT_T),
                    ("skeleton",INT_T), 
                    ("data",BLOB_T)]
TABLES["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("role",TEXT_T), 
                    ("userGroup",TEXT_T)]
                    
class MotionDatabase(DataBaseConnection):
    def __init__(self, server_secret=None):
        self.table_descs = TABLES
        self.collections_table = "collections"
        self.skeleton_table = "skeletons"
        self.motion_table = "motion_clips"
        self.preprocessed_table = "preprocessed_data"
        self.model_table = "models"
        self.graph_table = "graphs"
        self.user_table = "users"
        self.existing_collections = []
        self.upload_buffer = dict()
        self.skeletons = dict()
        self._mp_buffer = dict()
        self._mp_skeleton_type = dict()
        self.server_secret = server_secret
        self.enforce_access_rights = server_secret is not None
        print("set server secret", self.server_secret, self.enforce_access_rights)
    
    def connect(self, path):
        self.connect_to_database(path)
        for skel_id, skel_name in self.get_skeleton_list():
            print("add", skel_name)
            self.skeletons[skel_name] = self.load_skeleton(skel_name)

    def create_database(self, path):
        self.connect_to_database(path)
        for t_name in self.table_descs:
            self.create_table(t_name, self.table_descs[t_name], replace=True)
        print("created database",path)

    def init_database(self, path, recreate=False):
        create_db = not os.path.isfile(path)
        if create_db or recreate:
            self.create_database(path)
        else:
            self.connect_to_database(path)

    def init_skeleton_table(self, path, name="skeletons"):
        self.connect_to_database(path)
        self.create_table(name, self.table_descs[name], replace=True)
        
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
        if not os.path.isdir(directory):
            os.makedirs(directory)
        count = 1
        for motion_id, name in motion_list:
            print("download motion", str(count)+"/"+str(n_motions), name)
            self.export_motion_clip(skeleton, motion_id, name, directory)
            count+=1

    def export_motion_clip(self, skeleton, motion_id, name, directory):
        print("export clip")
        data, skeleton, meta_data = self.get_motion_by_id(motion_id)
        if data is None:
            return
        motion_dict = bson.loads(data)
        print("write to file")
        motion_vector = MotionVector()
        motion_vector.from_custom_unity_format(motion_dict)
        bvh_str = get_bvh_string(skeleton, motion_vector.frames)
        filename = directory+os.sep+name
        if not name.endswith(".bvh"):
            filename += ".bvh"
        with open(filename, "wt") as out_file:
            out_file.write(bvh_str)

    def import_graphs(self, other):
        graphs = other.get_graph_list()
        for graph_id, graph_name in graphs:
            r = other.get_graph_by_id(graph_id)
            if len(r)> 0:
                skeleton_name, graph_data = r[0]
                print("import", graph_id, graph_name)
                data = bson.dumps(json.loads(graph_data))
                records = [[graph_name,skeleton_name, data]]
                self.insert_records(self.graph_table, ["name","skeleton","data"], records)


    def load_skeleton(self, skeleton_name):
        data, skeleton_model = self.get_skeleton_by_name(skeleton_name)
        if data is not None:
            data = bson.loads(data)
            add_extra_end_site=False
            print("load default", len(data["referencePose"]["rotations"]))
            skeleton = SkeletonBuilder().load_from_custom_unity_format(data, add_extra_end_site=add_extra_end_site)
        
        if skeleton_model is not None:
            try:
                skeleton_model = bson.loads(skeleton_model)
                skeleton.skeleton_model = skeleton_model
            except Exception as e:
                print("Could not load skeleton model", e.args)
        return skeleton

    def get_collection_list_by_id(self, parent_id, owner=-1):
        filter_conditions =  [("parent",parent_id)]
        if owner >= 0:
            filter_conditions.append(("owner",owner))
        collection_records = self.query_table(self.collections_table, ["ID","name","type", "owner"],filter_conditions)
        return collection_records

    def parse_collection(self, skeleton_name, parent=0):
        collections = dict()
        for col in self.get_collection_list_by_id(parent):
            col_id, col_name, col_type, owner = col
            print("export",  col_id, col_name, col_type)
            m_data = self.get_data_in_collection(col_id, skeleton_name, is_aligned=0)
            collections[col] = m_data
        return collections

    def get_data_in_collection(self, c_id, skeleton_name,  is_aligned):
        motion_list = self.get_motion_list_by_collection_legacy(c_id, skeleton_name)
        print(" data_in_collection",len(motion_list))
        motion_data = dict()
        processed_data = dict()
        for m_id,name in motion_list:
            #print("m_", m_id, name)
            data, meta_data, time_func, skeleton_name, subject, timestamp , is_aligned= self.get_motion_by_id_legacy(m_id)
            motion = {"name": name, "data": data, 
                    "skeleton": skeleton_name, 
                    "meta_data": meta_data, 
                    "time_func": time_func,
                    "subject": subject,
                    "timestamp": timestamp}
            if is_aligned:
                processed_data[m_id] = motion
            else:
                motion_data[m_id] = motion
            
        model_data = dict()
        
        model_list = self.get_model_list_by_collection(c_id, skeleton_name)
        for m_id,name in model_list: 
            data, cluster_tree_data, skeleton_name = self.get_model_by_id_legacy(m_id)
            model = {"name": name, "data": data, 
                    "skeleton": skeleton_name, 
                    "cluster_tree_data": cluster_tree_data}
            model_data[m_id] = model

        collection_data = dict()
        collection_data["motions"] = motion_data
        collection_data["preprocessed"] = processed_data
        collection_data["models"] = model_data
        return collection_data
      
    def get_motion_by_id(self, m_id):
        r = self.query_table(self.motion_table, ["data", "metaData", "skeleton"], [("ID",m_id)])
        data = None
        meta_data = None
        skeleton_name = ""
        
        if len(r) > 0:
            data = r[0][0]
            meta_data = r[0][1]
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
        if data is not None:
            data["data"] = motion_data
        if meta_data is not None:
            data["metaData"] = meta_data
        self.update_entry(self.motion_table, data, "ID", m_id)

    def add_new_skeleton(self, name, data=b"x00", meta_data=b"x00"):
        skeleton_list = self.get_name_list(self.skeleton_table)
        if name != "" and name not in skeleton_list.values:
            records = [(name, data, meta_data)]
            self.insert_records(self.skeleton_table, ["name", "data", "metaData"], records)
            self.skeletons[name] = self.load_skeleton(name)
        else:
            print("Error: skeleton already exists")

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

    def get_preprocessed_data_by_id(self, m_id):
        r = self.query_table(self.preprocessed_table, ["data", "metaData", "skeleton"], [("ID",m_id)])
        data = None
        meta_data = None
        
        if len(r) > 0:
            data = r[0][0]
            meta_data = r[0][1]
            skeleton_name = r[0][2]
        else:
            print("Error in get processed data", m_id)
        return data, meta_data, skeleton_name

    def get_model_by_id(self, m_id):
        r = self.query_table(self.model_table, ["data", "metaData", "skeleton"], [("ID",m_id)])
        skeleton_name = ""
        data = None
        if len(r) > 0:
            data = r[0][0]
            cluster_tree_data = r[0][1]
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
        if data != "":
            data["data"] = motion_data
        if meta_data != "":
            data["metaData"] = meta_data
        self.update_entry(self.motion_table, data, "ID", str(m_id))
    
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
        self.update_entry(self.collections_table, input_data, "id", collection_id)
    
    def get_skeleton_by_name(self, name):
        records = self.query_table(self.skeleton_table,[ "data", "metaData"], [("name", name)])
        #recordsrecords = self.get_skeleton_by_name(skeleton_table, name)
        data = None
        meta_data = None
        if len(records) > 0:
            data = records[0][0]
            meta_data = records[0][1]
        return data, meta_data

    def get_motion_list_by_collection(self, collection, skeleton=""):
        filter_conditions =[("collection",str(collection))]
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
        records = [(name, skeleton, data)]
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
            data["data"] = bson.dumps(input_data["data"])
        self.update_entry(self.graph_table, data, "id", graph_id)

    def get_graph_by_id(self, graph_id):
        r = self.query_table(self.graph_table, ["skeleton","data"], [("ID", graph_id)])
        return r

    def remove_graph_by_id(self, graph_id):
        return self.delete_entry_by_id(self.graph_table, graph_id)

    def get_skeleton_list(self):
        r = self.query_table(self.skeleton_table, ["ID","name"], [])
        return r


    def upload_motion(self, part_idx, n_parts, collection, skeleton_name, name, data, meta_data, is_processed=False):
        print("upload motion", name)
        if name not in self.upload_buffer:
            upload_state = dict()
            upload_state["parts"] = dict()
            upload_state["n_parts"] = n_parts
            self.upload_buffer[name] = upload_state
        self.upload_buffer[name]["parts"][part_idx] = data
        if self.buffer_is_complete(name):
            data = self.get_data_from_buffer(name)
            data = json.loads(data)
            n_frames = 0
            public = 0
            if "poses" in data:
                n_frames = len(data["poses"])
            data = bson.dumps(data)
            del self.upload_buffer[name]
            if is_processed:
                return self.insert_preprocessed_data(collection, skeleton_name, name, data, meta_data)
            else:
                return self.insert_motion(collection, skeleton_name, name, data, meta_data, n_frames, public)

    def upload_bvh_clip(self, collection, skeleton_name, name, bvh_str):
        bvh_reader = get_bvh_from_str(bvh_str)
        animated_joints = list(bvh_reader.get_animated_joints())
        motion_vector = MotionVector()
        motion_vector.from_bvh_reader(bvh_reader, False)
        motion_vector.skeleton = SkeletonBuilder().load_from_bvh(bvh_reader, animated_joints)
        data = motion_vector.to_db_format()
        n_frames = len(data["poses"])
        data = bson.dumps(data)
        m_records = []
        row = (name, skeleton_name, collection, data, n_frames)
        m_records.append(row)
        motion_vector.export(motion_vector.skeleton, "out_mv.bvh")
        self.insert_records(self.motion_table, ["name", "skeleton","collection","data","numFrames"], m_records)
            
    def insert_motion(self, collection, skeleton_name, name, data, meta_data, n_frames, public):
        m_records = []
        row = (name, skeleton_name, collection, data, meta_data, n_frames, public)
        m_records.append(row)
        self.insert_records(self.motion_table, ["name", "skeleton","collection","data","metaData", "numFrames", "public"], m_records)

    def insert_preprocessed_data(self, collection, skeleton_name, name, data, meta_data):
        m_records = []
        row = (name, skeleton_name, collection, data, meta_data)
        m_records.append(row)
        self.insert_records(self.preprocessed_table, ["name", "skeleton","collection","data","metaData"], m_records)

    def delete_motion_by_id(self, motion_id):
        return self.delete_entry_by_id(self.motion_table, motion_id)

    def delete_preprocessed_data(self, motion_id):
        return self.delete_entry_by_id(self.preprocessed_table, motion_id)

    def buffer_is_complete(self, name):
        return self.upload_buffer[name]["n_parts"] == len(self.upload_buffer[name]["parts"])

    def get_data_from_buffer(self, name):
        b_data= None
        for idx in range(self.upload_buffer[name]["n_parts"]):
            if b_data is None:
                b_data =  self.upload_buffer[name]["parts"][idx]
            else:
                b_data += self.upload_buffer[name]["parts"][idx]
        data = b_data
        return data

    def add_new_collection_by_id(self, name, collection_type, parent_id, owner=0):
        owner = max(0, owner)
        records = [(name, collection_type, parent_id, owner)]
        self.insert_records(self.collections_table, ["name", "type", "parent", "owner"], records)
        records = self.get_max_id(self.collections_table)
        new_id = -1
        if len(records) > 0:
            new_id = int(records.iloc[0]["ID"])
        return new_id

    def remove_collection_by_id(self, motion_id):
        return self.delete_entry_by_id(self.collections_table, motion_id)

    def upload_motion_model(self, name, mp_name, skeleton, data):
        records = []
        row = (name, mp_name, skeleton, data)
        records.append(row)
        self.insert_records(self.model_table, ["name", "collection","skeleton", "data"], records)
        records = self.get_max_id(self.model_table)
        new_id = -1
        if len(records) > 0:
            new_id = int(records.iloc[0]["ID"])
        return new_id


    def upload_cluster_tree(self, model_id, cluster_tree_data):
        data = dict()
        data["metaData"] = cluster_tree_data
        self.update_entry(self.model_table, data, "ID", str(model_id))

    def remove_skeleton(self, name):
        self.delete_entry_by_name(self.skeleton_table, name)

    def delete_model_by_id(self, m_id):
        self.delete_entry_by_id(self.model_table, m_id)

    def get_motion_primitive_sample(self, model_id):
            mv = None
            if model_id not in self._mp_buffer:
                data, cluster_tree_data, skeleton_name = self.get_model_by_id(model_id)
                data = bson.loads(data)
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


    def get_skeleton(self, skeleton_type):
        if skeleton_type in self.skeletons:
            return self.skeletons[skeleton_type]
        else:
            return None


    def get_motion_list_by_collection_legacy(self, collection, skeleton=""):
        filter_conditions =[("collection",str(collection))]
        if skeleton != "":
            filter_conditions+=[("skeletonType", skeleton)]
        r = self.query_table(self.motion_table, ["ID","name"], filter_conditions)
        return r
        
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

    def get_motion_by_id_legacy(self, m_id):
        filter_conditions = [("ID",m_id)]
        r = self.query_table(self.motion_table, ["quaternionFrames", "metaInfo", "timeFunction", "skeletonType", "subject", "isAligned", "Timestamp"], filter_conditions)
        skeleton_name = ""
        data = None
        meta_data = None
        
        if len(r) > 0:
            data = r[0][0]
            meta_data = r[0][1]
            time_func = r[0][2]
            skeleton_name = r[0][3]
            subject = r[0][4]
            is_aligned = r[0][5] == 1
            timestamp = r[0][6]
        else:
            print("Error in get_motion_by_id_legacy")
        return data, meta_data, time_func, skeleton_name, subject, timestamp, is_aligned

    def get_model_by_id_legacy(self, m_id):
        filter_conditions = [("ID",m_id)]
        r = self.query_table(self.model_table, ["data", "clusterTreeData", "skeleton"], filter_conditions)
        skeleton_name = ""
        data = None
        
        if len(r) > 0:
            data = r[0][0]
            cluster_tree_data = r[0][1]
            skeleton_name = r[0][2]
        else:
            print("Error in get_model_by_id_legacy")
        return data, cluster_tree_data, skeleton_name

    def authenticate_user(self, user, password):
        success = False
        m = hashlib.sha256()
        m.update(bytes(password,"utf-8"))
        password = m.digest()
        filter_conditions = [("name",user)]
        print(user, password)
        r = self.query_table(self.user_table, ["password"], filter_conditions)
        if  len(r) >0:
            success = r[0][0] == password
        return success

    def generate_token(self, payload):
        if self.server_secret is not None:  
            return jwt.encode(payload, self.server_secret, algorithm='HS256').decode("utf-8")
        else:
            return ""
    
    def create_user(self, user, password, role, group):
        m = hashlib.sha256()
        m.update(bytes(password,"utf-8"))
        password = m.digest()
        records = [[user, password, role, group]]
        self.insert_records(self.user_table, ["name", "password", "role","userGroup"], records)

    def remove_user(self, name):
        self.delete_entry_by_name(self.user_table,name)

    def check_rights(self, session):
        if self.enforce_access_rights and "user" in session and "token" in session:
            token = bytes(session["token"], "utf-8")
            payload = jwt.decode(token, self.server_secret, algorithm='HS256')
            print("decoded", payload)
            if "user" in payload:
                return payload["user"] == session["user"]
            else:
                return False
        else:
            print(session.keys())
            return not self.enforce_access_rights

        