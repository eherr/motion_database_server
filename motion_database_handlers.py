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
import time
import numpy as np
import json
import bson
import bz2
import threading
import subprocess
from multiprocessing import Process
import tornado.web
from motion_database import  get_bvh_string
from anim_utils.animation_data import BVHReader, MotionVector, BVHWriter
from kubernetes_interface import load_kube_config, start_kube_job, stop_kube_job
from base_handler import BaseHandler

DEFAULT_SKELETON = "custom"
USER_ROLE_ADMIN = "admin"

class GetMotionHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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


class GetMotionInfoHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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


class GetSampleHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        motion_vector, skeleton_type = self.motion_database.get_motion_vector_from_random_sample(input_data["model_id"])
        result_object = motion_vector.to_db_format()
        result_object["skeletonModel"] = skeleton_type
        #self.write(json.dumps(result_object))
        self.write(bson.dumps(result_object))


class GetMetaHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application

    def post(self):
        result_object = dict(id=str(self.app.idCounter), server_port=str(self.app.port),
                             activate_port_forwarding=self.app.activate_port_forwarding,
                             enable_download=self.app.enable_download)

        self.write(json.dumps(result_object))


class AuthenticateHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        user_id = -1
        if "username" in input_data and "password" in input_data:
            user = input_data["username"]
            password = input_data["password"]
            user_id = self.motion_database.authenticate_user(user, password)
        else:
            print("missing required fields")
        
        result_object = dict()
        result_object["user_id"] = user_id
        if user_id > -1:
            print("aunticated user", user_id)
            result_object["username"] = input_data["username"]
            playload = {"user_id": user_id, "username": input_data["username"]}
            result_object["token"] = self.app.motion_database.generate_token(playload)
            result_object["role"] = self.app.motion_database.get_user_role(user_id)
        else:
            print("failed to authenticate user")
        self.write(json.dumps(result_object))

class GetSkeletonHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        
        skeleton_name = DEFAULT_SKELETON # default skeleton
        if "skeleton_type" in input_data:
            skeleton_name = input_data["skeleton_type"]
        elif "skeleton_name" in input_data:
            skeleton_name = input_data["skeleton_name"]
        print("get skeleton", skeleton_name)
        skeleton = self.motion_database.get_skeleton(skeleton_name)
        if skeleton is not None:
            result_object = skeleton.to_unity_format()
            result_object["name"] = skeleton_name
            self.write(json.dumps(result_object))
        else:
            print("Error: Could not find skeleton ", skeleton_name)
            self.write("Error")

class GetSkeletonModelHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        skeleton_name = DEFAULT_SKELETON # default skeleton
        if "skeleton_type" in input_data:
            skeleton_name = input_data["skeleton_type"]
        elif "skeleton_name" in input_data:
            skeleton_name = input_data["skeleton_name"]
        if skeleton_name is not None:
            skeleton = self.motion_database.get_skeleton(skeleton_name)
            result_object = skeleton.skeleton_model
            self.write(json.dumps(result_object))
        else:
            print("Error: Could not find skeleton ", skeleton_name)
            self.write("Error")



class UploadMotionModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            # print(input_str)
            input_data = json.loads(input_str)
            output_str = "done"
            print("upload motion primitive model")
            if "collection" in input_data and "data" in input_data and self.motion_database.check_rights(input_data):
                mm_data_str = bson.dumps(input_data["data"])
                mm_data_str = bz2.compress(mm_data_str)
                data = dict()
                data["id"] = self.motion_database.upload_motion_model(input_data["name"],
                                                        input_data["collection"], 
                                                        input_data["skeleton_name"], 
                                                        mm_data_str)
                output_str = json.dumps(data)
            else:
                print("Error: did not find expected input data")
            self.write(output_str)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class UploadClusterTreeHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            # print(input_str)
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            print("upload cluster tree")
            if "model_id" in input_data and "cluster_tree_data" in input_data:
                cluster_tree_data_str = bson.dumps(json.loads(input_data["cluster_tree_data"]))
                cluster_tree_data_str = bz2.compress(cluster_tree_data_str)
                self.motion_database.upload_cluster_tree(input_data["model_id"],
                                                        cluster_tree_data_str)
            else:
                print("Error: did not find expected input data")
            self.write("done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



def load_bvh_str(filepath):
    bvh_str = ""
    with open(filepath, "r") as infile:
        for line in infile.readlines():
            bvh_str += line
    return bvh_str


class DownloadBVHHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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


class DownloadSampleHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        if "model_id" in input_data:
            model_id = input_data["model_id"]
            motion_vector, skeleton_type = self.motion_database.get_motion_vector_from_random_sample(model_id)
            skeleton = self.motion_database.get_skeleton(skeleton_type)
            if skeleton is not None:
                bvh_str = get_bvh_string(skeleton, motion_vector.frames)
                self.write(bvh_str)
            else:
                error_msg = "Error: did not find model"+str(model_id)
                print(error_msg)
                self.write(error_msg)
        else:
            error_msg = "Error: model id not specified"
            print(error_msg)
            self.write(error_msg)

class DownloadMotionModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)

            input_data = json.loads(input_str)
            data, cluster_tree_data, skeleton_name = self.motion_database.get_model_by_id(input_data["model_id"])
            if data is not None:
                self.write(data)
            else:
                self.write("")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadClusterTreeHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            data, cluster_tree_data, skeleton_name = self.motion_database.get_model_by_id(input_data["model_id"])
            result_str = ""
            if cluster_tree_data is not None and cluster_tree_data != b'\x00':
                result_str = cluster_tree_data
            self.write(result_str)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class DownloadAnnotationHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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


class GetTimeFunctionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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

class UploadMotionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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

class UploadBVHClipHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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


class ReplaceMotionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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
                    meta_data = bson.dumps(json.loads(input_data["meta_data"]))
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


class DeleteMotionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

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



class DeleteModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            m_id = input_data["model_id"]
            token = input_data["token"]
            owner_id = self.motion_database.get_owner_of_model(m_id)
            request_user_id = self.motion_database.get_user_id_from_token(token)
            role = self.app.motion_database.get_user_role(request_user_id)
            has_access = self.motion_database.check_rights(input_data)
            if request_user_id != owner_id and role != USER_ROLE_ADMIN:
                 print("Error: has no access rights")
            self.motion_database.delete_model_by_id(input_data["model_id"])
            self.write("Done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class DownloadMotionPrimitiveSampleHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            bvh_str = self.app.get_current_motion_primitive_sample(input_data["model_id"])
            print("bvh_str", bvh_str)
            # bvh_str = motion_record["BVHString"]
            if bvh_str is not None:
                self.write(bvh_str)
            else:
                self.write("Not found")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class GetMotionListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            skeleton_name = ""
            if "skeleton" in input_data:
                skeleton_name = input_data["skeleton"]
            if "collection" in input_data:
                collection = input_data["collection"]
                is_processed = 0
                if "is_processed" in input_data:
                    is_processed = input_data["is_processed"]
                if is_processed:
                    motions = self.motion_database.get_preprocessed_data_list_by_collection(collection, skeleton_name)
                else:
                    motions = self.motion_database.get_motion_list_by_collection(collection, skeleton_name)
                motions_str = json.dumps(motions)
                self.write(motions_str)
            if "collection_id" in input_data:
                collection_id = input_data["collection_id"]
                is_processed = 0
                if "is_processed" in input_data:
                    is_processed = input_data["is_processed"]
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


        
class GetSkeletonListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            skeletons = self.motion_database.get_skeleton_list()
            skeletons_str = json.dumps(skeletons)
            self.write(skeletons_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetModelListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database


    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            collection = None
            if "collection" in input_data:
                collection = input_data["collection"]
            if "collection_id" in input_data:
                collection = input_data["collection_id"]
            skeleton_name = ""
            if "skeleton" in input_data:
                skeleton_name = input_data["skeleton"]
            models = []
            if collection is not None:
                models = self.motion_database.get_model_list_by_collection(collection, skeleton_name)
            models_str = json.dumps(models)
            self.write(models_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class NewCollectionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.db_path = self.app.db_path
        self.motion_database = application.motion_database

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


class GetCollectionListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.db_path = self.app.db_path
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            # set public access
            owner = -1
            public = 1
            # give access to collections owned by user
            if "token" in input_data:
                owner = self.motion_database.get_user_id_from_token(input_data["token"])
                role = self.motion_database.get_user_role(owner)
                # allow admin to specify custom filter
                if role == USER_ROLE_ADMIN:
                    public = -1
                    owner = -1
                    if "public" in input_data:
                        public = input_data["public"]
                    if "owner" in input_data:
                        owner = input_data["owner"]
            cols_str = "[]"
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


class GetCollectionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.db_path = self.app.db_path
        self.motion_database = self.app.motion_database

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


class ReplaceCollectionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.db_path = self.app.db_path
        self.motion_database = self.app.motion_database

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

class RemoveCollectionHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.db_path = self.app.db_path
        self.motion_database = self.app.motion_database

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
            

class NewSkeletonHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            success = False
            if "name" in input_data and "data" in input_data and "token" in input_data:
                token = input_data["token"]
                request_user_id = self.app.motion_database.get_user_id_from_token(token)
                if request_user_id > -1:
                    data = None
                    if "data_type" in input_data and input_data["data_type"] == "bvh":
                        skeleton = self.motion_database.load_skeleton_from_bvh_str(input_data["data"])
                        data = bson.dumps(skeleton.to_unity_format(animated_joints=skeleton.animated_joints))
                        data = bz2.compress(data)
                    else:
                        data = bson.dumps(json.loads(input_data["data"]))
                        data = bz2.compress(data)
                    
                    meta_data = b"x00"
                    if "meta_data" in input_data:
                        meta_data = bson.dumps(json.loads(input_data["meta_data"]))
                        meta_data = bz2.compress(meta_data)
                    if data is not None:
                        success = self.motion_database.add_new_skeleton(input_data["name"], data, meta_data, request_user_id)
                else:
                    print("Error: not all parameters were provided to create a skeleton entry")
            else:
                print("Error: Not enough access rights")
            data = dict()
            data["success"] = success
            self.write(json.dumps(data))

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class ReplaceSkeletonHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            success = False
            if "name" in input_data and "token" in input_data:
                skeleton_name = input_data["name"]
                token = input_data["token"]
                owner_id = self.motion_database.get_owner_of_skeleton(skeleton_name)
                request_user_id = self.motion_database.get_user_id_from_token(token)
                user_role = self.app.motion_database.get_user_role(request_user_id)
                if request_user_id == owner_id or user_role.lower() == "admin":
                    data = b"x00"
                    meta_data = b"x00"
                    if "data" in input_data:
                        data = json.loads(input_data["data"])
                        data = bson.dumps(data)
                        data = bz2.compress(data)
                    if "meta_data" in input_data:
                        meta_data = bson.dumps(json.loads(input_data["meta_data"]))
                        meta_data = bz2.compress(meta_data)
                    if data != b"x00" or meta_data != b"x00":
                        self.motion_database.replace_skeleton(skeleton_name, data, meta_data)
                        success = True
                else:
                    print("Error: not enough access rights to modify skeleton entry")
            else:
                print("Error: not all parameters were provided to modify a skeleton entry")
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


class RemoveSkeletonHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            success = False
            input_data = json.loads(input_str)
            if "name" in input_data and "token" in input_data:
                skeleton_name = input_data["name"]
                token = input_data["token"]
                owner_id = self.motion_database.get_owner_of_skeleton(skeleton_name)
                request_user_id = self.motion_database.get_user_id_from_token(token)
                user_role = self.app.motion_database.get_user_role(request_user_id)
                if request_user_id == owner_id or user_role.lower() == "admin":
                    self.motion_database.remove_skeleton(skeleton_name)
                    success = True
                else:
                    print("Error: not enough access rights to delete skeleton entry")
            else:
                print("Error: not all parameters were provided to delete skeleton entry")
            
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



class GetGraphListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            skeleton = None
            if "skeleton" in input_data:
                skeleton = input_data["skeleton"]
            result = self.motion_database.get_graph_list(skeleton)
            if result is not None:
                result_str = json.dumps(result)
                self.write(result_str)
            else:
                self.write("Not found")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class UploadGraphHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            result_id = None
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            if "name" in input_data and "skeleton" in input_data and "data" in input_data:
                name = input_data["name"]
                skeleton = input_data["skeleton"]
                data = bson.dumps(input_data["data"])
                data = bz2.compress(data)
                result_id = self.motion_database.add_new_graph(name, skeleton, data)
            if result_id is not None:
                result_data = {"id": result_id}
                result_str = json.dumps(result_data)
                self.write(result_str)
            else:
                self.write("Error")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class ReplaceGraphHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            result_id = None
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            if "id" in input_data:
                graph_id = input_data["id"]
                data = bz2.compress(data)
                self.motion_database.replace_graph(graph_id, input_data)
            self.write("Done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadGraphHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            result = None
            input_data = json.loads(input_str)
            if "id" in input_data:
                graph_id = input_data["id"]
                records = self.motion_database.get_graph_by_id(graph_id)
                if len(records) > 0:
                    data = bz2.decompress(records[0][1])
                    result = bson.loads(data)
                    result = json.dumps(result)
            if result is not None:
                self.write(result)
            else:
                self.write("Not found")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class RemoveGraphHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            
           input_str = self.request.body.decode("utf-8")
           result = None
           input_data = json.loads(input_str)
           has_access = self.motion_database.check_rights(input_data)
           if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
           if "id" in input_data:
               graph_id = input_data["id"]
               result = self.motion_database.remove_graph_by_id(graph_id)
           if result is not None:
               result_str = json.dumps(result)
               self.write(result_str)
           else:
               self.write("Done")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class StartServerHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           has_access = self.motion_database.check_rights(input_data)
           if not has_access:
                print("Error: no access rights")
                self.write("Error: no access right")
           if "graph_id" in input_data:
               graph_id = input_data["graph_id"]
               p = Process(target=subprocess.call, args=("python run_websocket_server.py ",))
               p.start()
               
               print("start server")
           self.write("start server")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class StartClusterJobHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = self.app.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           has_access = self.motion_database.check_rights(input_data)
           if not has_access:
               print("Error: no access rights")
               self.write("Error: no access right")
            
           namespace = self.app.k8s_namespace
           image_name = input_data["image_name"]
           job_name = input_data["job_name"]
           job_desc = input_data["job_desc"]
           resources = input_data["resources"]
           try:
               stop_kube_job(namespace, job_name)
           except:
               pass
           start_kube_job(namespace, job_name, image_name, job_desc, resources)
           print("start job", job_name)
           self.write("start job")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class UploadCharacterModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            success = False
            if has_access:
                if "name" in input_data and "skeleton_type" in input_data and "data" in input_data:
                    name = input_data['name']
                    skeleton_type = input_data['skeleton_type'] 
                    data = input_data['data']
                    data = bytearray(data) # https://www.w3resource.com/python-exercises/python-basic-exercise-118.php
                    success = self.motion_database.store_character_model(name, skeleton_type, data)
                else:
                    print("Error: Not all parameters provided")
            else:
                print("Error: Not enough access rights")
            response_dict = dict()
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)
        except Exception as e:
            print("caught exception in %s", e)
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DeleteCharacterModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    @tornado.gen.coroutine
    def post(self):
        print("Post method for deleting GLB file from server")
        try:
            input_str = self.request.body.decode("utf-8")
            input_json = json.loads(input_str)
            name = input_json['name']
            skeleton_type = input_json['skeleton_type'] 
            self.motion_database.delete_character_model(name, skeleton_type)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class DownloadCharacterModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    @tornado.gen.coroutine
    def post(self):
        print("Post method for binary file loading")
        try:
            input_str = self.request.body.decode("utf-8")
            input_json = json.loads(input_str)
            name = input_json['name']
            skeleton_type = input_json['skeleton_type'] 
            data = self.motion_database.get_character_model_data(name, skeleton_type)
            if data is not None:
                self.write(data)
            else:
                print("Error: could not read file")
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetCharacterModelListHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_json = json.loads(input_str)
            skeleton_type = input_json['skeleton_type']
            characters = self.motion_database.get_character_model_list(skeleton_type)
            characters_str = json.dumps(characters)
            self.write(characters_str)
        except Exception as e:
            print("caught exception in post method")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetCollectionsByNameHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database


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

class GetMotionListByNameHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database


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
                            (r"/get_skeleton_list", GetSkeletonListHandler),
                            (r"/get_model_list", GetModelListHandler),
                            (r"/get_collection_list", GetCollectionListHandler),
                            (r"/get_graph_list", GetGraphListHandler),
                            (r"/get_motion", GetMotionHandler),
                            (r"/get_motion_info", GetMotionInfoHandler),
                            (r"/get_skeleton", GetSkeletonHandler),
                            (r"/get_skeleton_model", GetSkeletonModelHandler),
                            (r"/download_bvh", DownloadBVHHandler), 
                            (r"/download_sample_as_bvh", DownloadSampleHandler), 
                            (r"/download_motion_model", DownloadMotionModelHandler),
                            (r"/download_cluster_tree", DownloadClusterTreeHandler),
                            (r"/download_annotation", DownloadAnnotationHandler),
                            (r"/get_collection", GetCollectionHandler),
                            (r"/replace_motion", ReplaceMotionHandler),
                            (r"/replace_collection", ReplaceCollectionHandler),
                            (r"/upload_motion", UploadMotionHandler),
                            (r"/upload_bvh_clip", UploadBVHClipHandler),
                            (r"/delete_motion", DeleteMotionHandler),
                            (r"/create_new_collection", NewCollectionHandler),
                            (r"/remove_collection", RemoveCollectionHandler),
                            (r"/create_new_skeleton", NewSkeletonHandler),
                            (r"/replace_skeleton", ReplaceSkeletonHandler),
                            (r"/upload_motion_model", UploadMotionModelHandler),
                            (r"/delete_model", DeleteModelHandler),
                            (r"/remove_skeleton", RemoveSkeletonHandler),
                            (r"/upload_cluster_tree", UploadClusterTreeHandler),
                            (r"/upload_graph", UploadGraphHandler),
                            (r"/replace_graph", ReplaceGraphHandler),
                            (r"/download_graph", DownloadGraphHandler),
                            (r"/remove_graph", RemoveGraphHandler),                            
                            (r"/get_sample", GetSampleHandler),
                            (r"/download_motion_primitive_sample", DownloadMotionPrimitiveSampleHandler),
                            (r"/get_time_function", GetTimeFunctionHandler),
                            (r"/start_mg_state_server", StartServerHandler),
                            (r"/start_cluster_job", StartClusterJobHandler),
                            (r"/get_meta_data", GetMetaHandler),
                            (r"/authenticate", AuthenticateHandler),
                            (r"/get_character_model_list", GetCharacterModelListHandler),
                            (r"/upload_character_model", UploadCharacterModelHandler),
                            (r"/delete_character_model", DeleteCharacterModelHandler),
                            (r"/download_character_model", DownloadCharacterModelHandler),
                            (r"/get_collections_by_name", GetCollectionsByNameHandler),
                            (r"/get_motion_list_by_name", GetMotionListByNameHandler)]