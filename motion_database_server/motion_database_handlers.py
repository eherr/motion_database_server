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
import time
import json
import bson
import bz2
import tornado.web
from motion_database_server.utils import get_bvh_string
from anim_utils.animation_data import MotionVector
from motion_database_server.base_handler import BaseDBHandler


USER_ROLE_ADMIN = "admin"

class GetMotionHandler(BaseDBHandler):
    def post(self):
        input_str = self.request.body.decode("utf-8")
        print("get motion",input_str)
        start = time.time()
        input_data = json.loads(input_str)
        is_processed = False
        if "is_processed" in input_data:
            is_processed = input_data["is_processed"]
        if is_processed:
            data, meta_data, skeleton_type = self.motion_database.get_preprocessed_data_by_id(input_data["clip_id"])
        else:
            data, meta_data, skeleton_type = self.motion_database.get_motion_by_id(input_data["clip_id"])
        
        self.write(data)

        delta = time.time()- start
        print("retrieved clip in", delta, "seconds")


class GetMotionInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        input_str = self.request.body.decode("utf-8")
        print("get motion info",input_str)
        start = time.time()
        input_data = json.loads(input_str)
        is_processed = False
        columns = []
        clip_ids = []
        if "is_processed" in input_data:
            is_processed = input_data["is_processed"]
        if "columns" in input_data:
            columns = input_data["columns"]
        if "clip_ids" in input_data:
            clip_ids = input_data["clip_ids"]
        if len(clip_ids) > 0 and len(columns):
            data = self.motion_database.get_motion_info(columns, clip_ids, is_processed)
            json_str = json.dumps(data)
            self.write(json_str)
        delta = time.time()- start
        print("processed query in", delta, "seconds")



class GetMetaHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        result_object = dict(id=str(self.app.idCounter), server_port=str(self.app.port),
                             activate_port_forwarding=self.app.activate_port_forwarding,
                             enable_download=self.app.enable_download)

        self.write(json.dumps(result_object))



def load_bvh_str(filepath):
    bvh_str = ""
    with open(filepath, "r") as infile:
        for line in infile.readlines():
            bvh_str += line
    return bvh_str


class DownloadBVHHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)

            input_data = json.loads(input_str)

            data, meta_data, skeleton_name = self.motion_database.get_motion_by_id(input_data["clip_id"])
          
            # bvh_str = motion_record["BVHString"]
            if data is not None:
                data = bz2.decompress(data)
                data = bson.loads(data)
                motion_vector = MotionVector()
                motion_vector.from_custom_db_format(data)
                skeleton = self.motion_database.get_skeleton(skeleton_name)
                bvh_str = get_bvh_string(skeleton, motion_vector.frames)
                self.write(bvh_str)
            else:
                self.write("Not found")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadAnnotationHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("get annotation", input_str)
            input_data = json.loads(input_str)
            m_id = input_data["clip_id"]
            is_processed = False
            if "is_processed" in input_data:
                is_processed = input_data["is_processed"]
            if is_processed:
                data, meta_data, skeleton_name = self.motion_database.get_preprocessed_data_by_id(m_id)
            else:
                data, meta_data, skeleton_name = self.motion_database.get_motion_by_id(m_id)

            if meta_data is not None and meta_data != b"x00" and meta_data != "":
                try:
                    meta_data = bz2.decompress(meta_data)
                    meta_data = bson.loads(meta_data)
                    annotation_str = json.dumps(meta_data)
                    self.write(annotation_str)
                except:
                    print("could not decode annotation", m_id)
                    self.write("")
            else:
                self.write("")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class GetTimeFunctionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("get_time_function",input_str)

            input_data = json.loads(input_str)
            m_id = input_data["clip_id"]
            data, meta_data, skeleton_name = self.motion_database.get_preprocessed_data_by_id(m_id)
            if meta_data is not None and meta_data != b"x00" and meta_data != "":
                meta_data = bz2.decompress(meta_data)
                meta_data = bson.loads(meta_data)
                if "time_function" in meta_data:
                    time_function_str = json.dumps(meta_data["time_function"])
                    self.write(time_function_str)
                else:
                    self.write("")
            else:
                self.write("")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class UploadMotionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            collection = input_data["collection"]
            res_str = ""
            is_processed = False
            if "is_processed" in input_data:
                is_processed = input_data["is_processed"]
            meta_data = b"x00"
            if "meta_data" in input_data:
                try:
                    meta_data = json.loads(input_data["meta_data"])
                    if is_processed and "time_function" in meta_data:
                        is_processed = True
                    else:
                        is_processed = False
                except:
                    print("Warning: could not read meta data of",input_data["name"])
                    meta_data = b"x00"
                    is_processed = False
            if "data" in input_data:
                n_parts = input_data["n_parts"]
                part_idx = input_data["part_idx"]
            print("upload motion", is_processed, input_data["is_processed"])
            if meta_data!= b"x00":
                meta_data = bson.dumps(meta_data)
                meta_data = bz2.compress(meta_data)
            data = input_data["data"]
            #data = base64.decodebytes(data.encode('utf-8'))
            res_str = self.motion_database.upload_motion(part_idx, n_parts, collection,
                                                input_data["skeleton_name"],
                                                input_data["name"],
                                                input_data["data"],
                                                meta_data, is_processed)
            if res_str is not None:
                self.write(res_str)
            else:
                self.write("done")

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class UploadBVHClipHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("call upload from bvh")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            name = input_data["name"]
            bvh_data = input_data["bvh_data"]
            skeleton = input_data["skeleton"]
            collection = input_data["collection"]
            print("a", name, skeleton, collection)
            res_str = self.motion_database.upload_bvh_clip(collection,
                                                skeleton,
                                                name,
                                                bvh_data)
     
            self.write("done")

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class ReplaceMotionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            result_str = ""
            is_processed = False
            if "is_processed" in input_data:
                is_processed = input_data["is_processed"]
            name = None
            if "name" in input_data:
                name = input_data["name"]
            meta_data = None
            if "meta_data" in input_data:
                try:
                    meta_data = json.loads(input_data["meta_data"])
                    meta_data = bson.dumps(meta_data)
                    meta_data = bz2.compress(meta_data)
                except:
                    print("Warning: could not read meta data")
                    meta_data = None
            collection = None
            if "collection" in input_data:
                collection = input_data["collection"]
            skeleton_name = None
            if "skeleton_name" in input_data:
                skeleton_name = input_data["skeleton_name"]
            if "data" in input_data:
                motion_data = bson.dumps(input_data["data"])
                motion_data = bz2.compress(motion_data)
            if is_processed:
                result_str = self.motion_database.replace_preprocessed_data(input_data["motion_id"],
                                                                collection,
                                                                skeleton_name,
                                                                name,
                                                                motion_data,
                                                                meta_data)
            else:
                result_str = self.motion_database.replace_motion(input_data["motion_id"],
                                                                collection,
                                                                skeleton_name,
                                                                name,
                                                                motion_data,
                                                                meta_data)

            if result_str is not None:
                self.write(result_str)
            else:
                self.write("Done")

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DeleteMotionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
    
            input_data = json.loads(input_str)
            if "clip_id" in input_data and "token" in input_data:
                m_id = input_data["clip_id"]
                token = input_data["token"]
                owner_id = self.motion_database.get_owner_of_motion(m_id)
                request_user_id = self.motion_database.get_user_id_from_token(token)
                role = self.app.motion_database.get_user_role(request_user_id)
                if request_user_id != owner_id and role != USER_ROLE_ADMIN:
                    print("Error: has no access rights")
                    self.write("Done")
                    return
                is_processed = False
                if "is_processed" in input_data:
                    is_processed = input_data["is_processed"]
                print("delete",m_id, is_processed)
                if is_processed:
                    self.motion_database.delete_preprocessed_data(m_id)
                else:
                    self.motion_database.delete_motion_by_id(m_id)
            self.write("Done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class GetMotionListHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            motions = []
            skeleton_name = input_data.get("skeleton","")
            collection_id = None
            if "collection" in input_data:
                collection_id = input_data["collection_id"]
            elif "collection_id" in input_data:
                collection_id = input_data["collection_id"]
            if collection_id is not None:
                is_processed = input_data.get("is_processed", 0)
                if is_processed:
                    motions = self.motion_database.get_preprocessed_data_list_by_collection(collection_id, skeleton_name)
                else:
                    motions = self.motion_database.get_motion_list_by_collection(collection_id, skeleton_name)
                    
            motions_str = json.dumps(motions)
            self.write(motions_str)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class NewCollectionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            success = False
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            if "token" in input_data and "name" in input_data and "type" in input_data and "parent_id" in input_data:
                token = input_data["token"]
                request_user_id = self.motion_database.get_user_id_from_token(token)
                response_dict = dict()
                if request_user_id >= 0:
                    name = input_data["name"]
                    collection_type = input_data["type"]
                    parent_id = input_data["parent_id"]
                    owner = request_user_id
                    if "owner" in input_data:
                        owner = input_data["owner"]
                    response_dict["id"] = self.motion_database.add_new_collection_by_id(name, collection_type, parent_id, owner)
                    success = True
                else:
                    print("Error: no access rights")
            else:
                print("Error: not all parameters were provided to create a collection entry")
            
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class GetCollectionListHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            owner, public = self.motion_database.get_access_rights_to_collections(input_data)
            col_str = "[]"
            if "parent_id" in input_data:
                parent_id = input_data["parent_id"]
                cols = self.motion_database.get_collection_list_by_id(parent_id, owner, public)
                cols_str = json.dumps(cols)
            self.write(cols_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetCollectionTreeHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            owner, public = self.motion_database.get_access_rights_to_collections(input_data)
            cols_str = "{}"
            if "parent_id" in input_data:
                parent_id = input_data["parent_id"]
                col_tree = self.motion_database.get_collection_tree(parent_id, owner, public)
                cols_str = json.dumps(col_tree)
            self.write(cols_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetCollectionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("get collection", input_str)
            input_data = json.loads(input_str)
            if "id" in input_data:
                collection_id = input_data["id"]
                collection = self.motion_database.get_collection_by_id(collection_id)
                collection_str = ""
                if collection is not None:
                    collection_str = json.dumps(collection)
                self.write(collection_str)
            else:
                self.write("Missing name or id parameter")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class ReplaceCollectionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            success = False
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            if "id" in input_data and "token" in input_data:
                collection_id = input_data["id"]
                token = input_data["token"]
                owner_id = self.motion_database.get_owner_of_motion(collection_id)
                request_user_id = self.motion_database.get_user_id_from_token(token)
                role = self.motion_database.get_user_role(request_user_id)
                if request_user_id == owner_id or role == USER_ROLE_ADMIN:
                    collection_id = input_data["id"]
                    self.motion_database.replace_collection(input_data, collection_id)
                    success = True
            else:
                print("Error: has no access rights")
            
            response_dict = dict()
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class RemoveCollectionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            success = False
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            if "id" in input_data and "token" in input_data:
                collection_id = input_data["id"]
                token = input_data["token"]
                owner_id = self.motion_database.get_owner_of_motion(collection_id)
                request_user_id = self.motion_database.get_user_id_from_token(token)
                role = self.motion_database.get_user_role(request_user_id)
                if request_user_id == owner_id or role == USER_ROLE_ADMIN:
                    self.motion_database.remove_collection_by_id(input_data["id"])
                    success = True
                else:
                    print("Error: has no access rights")
            response_dict = dict()
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()      


class GetCollectionsByNameHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("get collection", input_str)
            input_data = json.loads(input_str)
            if "name" in input_data:
                name = input_data["name"]
                exact_match = input_data.get("exact_match", False)
                collection = self.motion_database.get_collection_by_name(name, exact_match=exact_match)
                collection_str = ""
                if collection is not None:
                    collection_str = json.dumps(collection)
                self.write(collection_str)
            else:
                self.write("Missing name parameter")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetMotionListByNameHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("get motion list", input_str)
            input_data = json.loads(input_str)
            if "name" in input_data:
                name = input_data["name"]
                skeleton = input_data.get("skeleton", "")
                exact_match = input_data.get("exact_match", False)
                collection = self.motion_database.get_motion_list_by_name(name, skeleton, exact_match)
                collection_str = ""
                if collection is not None:
                    collection_str = json.dumps(collection)
                self.write(collection_str)
            else:
                self.write("Missing name parameter")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



MOTION_DB_HANDLER_LIST = [(r"/get_motion_list", GetMotionListHandler),
                            (r"/get_collection_list", GetCollectionListHandler),
                            (r"/get_motion", GetMotionHandler),
                            (r"/get_motion_info", GetMotionInfoHandler),
                            (r"/download_bvh", DownloadBVHHandler), 
                            (r"/download_annotation", DownloadAnnotationHandler),
                            (r"/get_collection", GetCollectionHandler),
                            (r"/replace_motion", ReplaceMotionHandler),
                            (r"/replace_collection", ReplaceCollectionHandler),
                            (r"/upload_motion", UploadMotionHandler),
                            (r"/upload_bvh_clip", UploadBVHClipHandler),
                            (r"/delete_motion", DeleteMotionHandler),
                            (r"/create_new_collection", NewCollectionHandler),
                            (r"/remove_collection", RemoveCollectionHandler),
                            (r"/get_time_function", GetTimeFunctionHandler),
                            (r"/get_meta_data", GetMetaHandler),
                            (r"/get_collections_by_name", GetCollectionsByNameHandler),
                            (r"/get_motion_list_by_name", GetMotionListByNameHandler),
                            (r"/get_collection_tree", GetCollectionTreeHandler)]