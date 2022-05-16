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
from motion_database_server.utils import get_bvh_from_str, extract_compressed_bson, get_bvh_string
from motion_database_server.user_database import UserDatabase
from motion_database_server.skeleton_database import SkeletonDatabase
from anim_utils.animation_data.skeleton_builder import SkeletonBuilder
from anim_utils.animation_data.motion_vector import MotionVector
from morphablegraphs.motion_model.motion_primitive_wrapper import MotionPrimitiveModelWrapper
from morphablegraphs.utilities import convert_to_mgrd_skeleton
import jwt
JWT_ALGORITHM = 'HS256'

def convert_to_small_dict(motion_dict):
    small_dict = dict()
    small_dict["joint_sequence"] = motion_dict["jointSequence"]
    small_dict["poses"]  = []
    small_dict["frame_time"] = motion_dict["frameTime"]
    axes = [0,1,2]
    use_q = True
    for f in motion_dict["frames"]:
        p = f["rootTranslation"]
        pose = [p["x"], p["y"], p["z"]]
        for q in f["rotations"]:
            if use_q:
                for k in ["w", "x", "y", "z"]:
                    pose.append(q[k])
            else:
                _q = []
                for k in ["w", "x", "y", "z"]:
                    _q.append(q[k])
                _q = normalize(_q)
                axis, angle = quaternion_to_axis_angle(_q)
                exp = axis * angle
                for i in axes:
                    pose.append(exp[i])
        small_dict["poses"].append(pose)
        
    return small_dict



INT_T = "INTERGER"
BLOB_T = "BLOB"
TEXT_T = "TEXT"

TABLES = dict()
TABLES["collections"] = [("name",TEXT_T),
                    ("type",TEXT_T), 
                    ("owner",INT_T), 
                    ("parent",INT_T)]
TABLES["skeletons"] = [("name",TEXT_T),
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T),
                    ("owner",INT_T)]
TABLES["motion_clips"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeletonType",INT_T), 
                    ("quaternionFrames",TEXT_T), 
                    ("metaInfo",TEXT_T)]
TABLES["models"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
TABLES["graphs"] = [("name",TEXT_T),
                    ("skeleton",INT_T), 
                    ("data",BLOB_T)]


TABLES2 = dict()
TABLES2["collections"] = [("name",TEXT_T),
                    ("type",TEXT_T), 
                    ("owner",TEXT_T), 
                    ("parent",INT_T), 
                    ("public",INT_T)]
TABLES2["skeletons"] = [("name",TEXT_T),
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
TABLES2["motion_clips"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T), 
                    ("subject",TEXT_T), 
                    ("source",TEXT_T)]
TABLES2["preprocessed_data"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T), 
                    ("source",TEXT_T)]
TABLES2["models"] = [("name",TEXT_T),
                    ("collection",INT_T), 
                    ("skeleton",INT_T), 
                    ("data",BLOB_T), 
                    ("metaData",BLOB_T)]
TABLES2["graphs"] = [("name",TEXT_T),
                    ("skeleton",INT_T), 
                    ("data",BLOB_T)]
TABLES2["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("role",TEXT_T), 
                    ("sharedAccessGroups",TEXT_T), 
                    ("email",TEXT_T)]
TABLES2["user_groups"] = [("name",TEXT_T), # need to be unique
                    ("owner",INT_T),     # user id
                     ("users",TEXT_T)]   #  list of user ids 

                    
class MotionDatabase(UserDatabase, SkeletonDatabase):
    collections_table = "collections"
    motion_table = "motion_clips"
    preprocessed_table = "preprocessed_data"
    model_table = "models"
    graph_table = "graphs"
    def __init__(self, server_secret=None, data_dir="data"):
        self.character_dir = data_dir + os.sep +"characters"
        self.existing_collections = []
        self.upload_buffer = dict()
        self.skeletons = dict()
        self._mp_buffer = dict()
        self._mp_skeleton_type = dict()
        self.jwt = jwt.JWT()
        if server_secret is not None:
            self.server_secret = jwt.jwk.OctetJWK(bytes(server_secret, "utf-8"))
        else:
            self.server_secret = None
        self.enforce_access_rights = server_secret is not None
    
    def connect(self, path):
        self.connect_to_database(path)
        for skel_id, skel_name, owner in self.get_skeleton_list():
            print("add", skel_name)
            self.skeletons[skel_name] = self.load_skeleton(skel_name)

    def create_database(self, path):
        self.connect_to_database(path)
        for t_name in TABLES2:
            self.create_table(t_name, TABLES2[t_name], replace=True)
        print("created database",path)

    def init_database(self, path, recreate=False):
        create_db = not os.path.isfile(path)
        if create_db or recreate:
            self.create_database(path)
        else:
            self.connect_to_database(path)

    def init_skeleton_table(self, path, name="skeletons"):
        self.connect_to_database(path)
        self.create_table(name, TABLES2[name], replace=True)
        
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
        motion_dict = extract_compressed_bson(data)
        print("write to file")
        motion_vector = MotionVector()
        motion_vector.from_custom_unity_format(motion_dict)
        bvh_str = get_bvh_string(skeleton, motion_vector.frames)
        filename = directory+os.sep+name
        if not name.endswith(".bvh"):
            filename += ".bvh"
        with open(filename, "wt") as out_file:
            out_file.write(bvh_str)
        
    def import_database(self, other):
        skeletons = other.get_skeleton_list()
        for skeleton_id, skeleton_name in skeletons:
            skeleton_name = skeleton_name
            print("ad",skeleton_name)
            self.import_skeleton(other, skeleton_name)
            self.import_collection_data_from_src(other,skeleton_name)
        self.import_graphs(other)

    def import_skeletons(self, other):
        skeletons = other.get_skeleton_list()
        for skeleton_id, skeleton_name in skeletons:
            skeleton_name = skeleton_name
            print("ad",skeleton_name)
            self.import_skeleton(other, skeleton_name)

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
            

    def import_skeleton(self,other, skeleton_name):
        skeleton = other.load_skeleton_legacy(skeleton_name)
        if skeleton is None:
            return

        skeleton_format = skeleton.to_unity_format()
        skeleton_format = bson.dumps(skeleton_format)
        skeleton_format = bz2.compress(skeleton_format)
        skeleton_model = bson.dumps(json.loads(skeleton.skeleton_model))
        skeleton_model = bz2.compress(skeleton_model)
        records = [[skeleton_name, skeleton_format, skeleton_model]]
        self.insert_records(self.skeleton_table, ["name", "data","metaData"], records)

    def import_collection_data_from_src(self, other, skeleton_name, parent=0):
        collections = other.parse_collection(skeleton_name, parent)
        for col in collections:
            
            col_id, col_name, col_type, owner, public = col
            if col_id not in self.existing_collections:
                self.existing_collections.append(col_id)
                records = [[col_id, col_name, col_type,owner,parent, public]]
                self.insert_records(self.collections_table,["ID","name", "type","owner","parent", "public"], records )

            self.import_collection_data(skeleton_name, col_id, col_name, collections[col], parent)

            self.import_collection_data_from_src(other, skeleton_name, col_id)
        return
        
    
    def import_collection_data(self, skeleton_name, col_id, col_name, collection_data,parent):

        m_records = []
        for m_id, m_data in collection_data["motions"].items():
            motion_dict =  json.loads(m_data["data"])
            small_dict = convert_to_small_dict(motion_dict)
            data = bson.dumps(small_dict)
            meta_data = b'\x00'
            if m_data["meta_data"] is not None and m_data["meta_data"] != "" :
                meta_data = bson.dumps(json.loads(m_data["meta_data"]))
            m_records.append([ m_data["name"], skeleton_name, col_id, data, meta_data, m_data["subject"], m_data["timestamp"]])
        if len(m_records) > 0:
            self.insert_records(self.motion_table, ["name", "skeleton", "collection","data", "metaData", "subject", "timestamp"], m_records)
            print("inserted motions", len(m_records), col_name)
        else:

            print("no motion records", col_name, len(collection_data["motions"]))

        m_records = []
        for m_id, m_data in collection_data["preprocessed"].items():
            motion_dict = json.loads(m_data["data"])
            small_dict = convert_to_small_dict(motion_dict)
            data = bson.dumps(small_dict)
            if m_data["meta_data"] is not None and m_data["meta_data"] != "" :
                meta_data = json.loads(m_data["meta_data"])
            else:
                meta_data = dict()
            meta_data["time_function"] = m_data["time_func"]
            meta_data = bson.dumps(meta_data)
            m_records.append([ m_data["name"],skeleton_name, col_id, data, meta_data])
        if len(m_records) > 0:
            self.insert_records(self.preprocessed_table, ["name", "skeleton","collection","data","metaData"], m_records)
            print("inserted preprocessed data", len(m_records), col_name)
        else:
            print("no preprocessing records", col_name)


        m_records = []
        for m_id, m_data in collection_data["models"].items():
            data = bson.dumps(json.loads(m_data["data"]))
            cluster_tree_data = b'\x00'
            if m_data["cluster_tree_data"] is not None and m_data["cluster_tree_data"] != "" :
                cluster_tree_data = bson.dumps(json.loads(m_data["cluster_tree_data"]))
            m_records.append([ m_id, m_data["name"],skeleton_name, col_id, data, cluster_tree_data])
        if len(m_records) > 0:
            self.insert_records(self.model_table, ["ID","name", "skeleton","collection","data","metaData"], m_records)
            print("inserted models", len(m_records), col_name)
        else:
            print("no records", col_name)

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

    def parse_collection(self, skeleton_name, parent=0):
        collections = dict()
        for col in self.get_collection_list_by_id(parent):
            col_id, col_name, col_type, owner, public = col
            print("export",  col_id, col_name, col_type, public)
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
            data["data"] = bz2.compress(bson.dumps(input_data["data"]))
        self.update_entry(self.graph_table, data, "id", graph_id)

    def get_graph_by_id(self, graph_id):
        r = self.query_table(self.graph_table, ["skeleton","data"], [("ID", graph_id)])
        return r

    def remove_graph_by_id(self, graph_id):
        return self.delete_entry_by_id(self.graph_table, graph_id)

    def upload_motion(self, part_idx, n_parts, collection, skeleton_name, name, base64_data_str, meta_data, is_processed=False):
        print("upload motion", name)
        if name not in self.upload_buffer:
            upload_state = dict()
            upload_state["parts"] = dict()
            upload_state["n_parts"] = n_parts
            self.upload_buffer[name] = upload_state
        self.upload_buffer[name]["parts"][part_idx] = base64_data_str
        if self.buffer_is_complete(name):
            self._insert_motion_from_buffer_to_db(name, collection, skeleton_name, meta_data, is_processed)

    def _insert_motion_from_buffer_to_db(self, name, collection, skeleton_name, meta_data, is_processed):
        base64_data_str = self.get_data_from_buffer(name)
        data = base64.decodebytes(base64_data_str.encode('utf-8'))
        data = extract_compressed_bson(data)
        n_frames = 0
        if "poses" in data:
            n_frames = len(data["poses"])
        data = bson.dumps(data)
        data = bz2.compress(data)
        del self.upload_buffer[name]
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
        m_records = []
        row = (name, skeleton_name, collection, data, n_frames)
        m_records.append(row)
        #motion_vector.export(motion_vector.skeleton, "out_mv.bvh")
        self.insert_records(self.motion_table, ["name", "skeleton","collection","data","numFrames"], m_records)
            
    def insert_motion(self, collection, skeleton_name, name, data, meta_data, n_frames):
        m_records = []
        row = (name, skeleton_name, collection, data, meta_data, n_frames)
        m_records.append(row)
        self.insert_records(self.motion_table, ["name", "skeleton","collection","data","metaData", "numFrames"], m_records)

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

    def get_motion_list_by_collection_legacy(self, collection, skeleton=""):
        filter_conditions =[("collection",str(collection))]
        if skeleton != "":
            filter_conditions+=[("skeletonType", skeleton)]
        r = self.query_table(self.motion_table, ["ID","name"], filter_conditions)
        return r
    
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

    def check_rights(self, session):
        if self.enforce_access_rights and "user" in session and "token" in session:
            token = session["token"]
            payload = self.jwt.decode(token, self.server_secret)
            if "user_name" in payload:
                return payload["user_name"] == session["user"]
            else:
                return False
        else:
            print(session.keys())
            return not self.enforce_access_rights
    
    def store_character_model(self, name, skeleton_type, data):
        if name[-4:] == ".glb":
            name = name[:-4]
        out_dir = self.character_dir + os.sep + skeleton_type 
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        out_filename = out_dir+ os.sep + name + ".glb"
        with open(out_filename, 'wb') as f:
            f.write(data)
        return True
    
    def delete_character_model(self, name, skeleton_type):
        if name[-4:] == ".glb":
            name = name[:-4]
        filename = self.character_dir + os.sep + skeleton_type + os.sep + name + ".glb"
        if os.path.isfile(filename):
            os.remove(filename)
        return True

    def get_character_model_list(self, skeleton_type):
        path_ = self.character_dir + os.sep + skeleton_type
        file_list = []
        if os.path.isdir(path_):
            file_list = [f for f in os.listdir(path_) if f.endswith('.glb')]
        print("model data", skeleton_type, file_list)
        return file_list
    
    def get_character_model_data(self, name, skeleton_type):
        if name[-4:] == ".glb":
            name = name[:-4]
        in_filename = self.character_dir + os.sep + skeleton_type + os.sep + name + ".glb"
        data = None
        if os.path.isfile(in_filename):
            with open(in_filename, 'rb') as f:
                data = f.read()
        else:
            print(in_filename,"is not a file")
        return data

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

    def get_user_access_rights(self, input_data):
        # set public access
        owner = -1
        public = 1
        # give access to collections owned by user
        if "token" in input_data:
            owner = self.get_user_id_from_token(input_data["token"])
            role = self.get_user_role(owner)
            # allow admin to specify custom filter
            if role == "admin":
                public = -1
                owner = -1
                if "public" in input_data:
                    public = input_data["public"]
                if "owner" in input_data:
                    owner = input_data["owner"]
        return owner, public
