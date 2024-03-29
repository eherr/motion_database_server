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


class MotionDBHandler(BaseDBHandler):
    def has_access(self, data):
        collection_id = data.get("collection", None)
        if collection_id is None:
            return False
        token = data.get("token", None)
        if token is None:
            return False
        return self.has_access_to_collection(collection_id, token)

class GetMotionHandler(BaseDBHandler):
    def post(self):
        input_str = self.request.body.decode("utf-8")
        start = time.time()
        input_data = json.loads(input_str)
        data = self.motion_database.get_motion_from_file(input_data["clip_id"])
        
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
        columns = []
        clip_ids = []
        is_processed = int(input_data.get("is_processed",0))
        if "columns" in input_data:
            columns = input_data["columns"]
        if "clip_ids" in input_data:
            clip_ids = input_data["clip_ids"]
        if len(clip_ids) > 0 and len(columns):
            data = self.motion_database.get_motion_info(columns, clip_ids)
            json_str = json.dumps(data)
            self.write(json_str)
        delta = time.time()- start
        print("processed query in", delta, "seconds")


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


class UploadMotionHandler(MotionDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            if not self.has_access(input_data):
                print("Error: has no access rights")
                self.write("Done")
                return
            collection = input_data["collection"]
            res_str = ""
            is_processed = int(input_data.get("is_processed",0))
            print("upload motion", is_processed)
            meta_data = None
            if "meta_data" in input_data:
                try:
                    meta_data = json.loads(input_data["meta_data"])
                    if is_processed and "time_function" in meta_data:
                        is_processed = 1
                    else:
                        is_processed = 0
                except:
                    print("Warning: could not read meta data of",input_data["name"])
                    meta_data = None
                    is_processed = 0
            if "data" in input_data:
                n_parts = input_data["n_parts"]
                part_idx = input_data["part_idx"]
            if meta_data is not None:
                meta_data = bson.dumps(meta_data)
                meta_data = bz2.compress(meta_data)
            data = input_data["data"]
            #data = base64.decodebytes(data.encode('utf-8'))
            new_id = self.motion_database.upload_motion(part_idx, n_parts, collection,
                                                input_data["skeleton_name"],
                                                input_data["name"],
                                                data,
                                                meta_data, is_processed)
            if new_id is not None:
                response = {"id":new_id}
                res_str = json.dumps(response)
                self.write(res_str)
            else:
                self.write("done")

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class UploadBVHClipHandler(MotionDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("call upload from bvh")
            input_data = json.loads(input_str)
            if not self.has_access(input_data):
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
            motion_id = input_data.get("motion_id", None)
            token = input_data.get("token", None)
            if not self.has_access_to_file(motion_id, token):
                print("Error: has no access rights")
                self.write("Done")
                return
            result_str = ""
            is_processed = int(input_data.get("is_processed",0))
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
            
            result_str = self.motion_database.replace_motion(motion_id,
                                                                collection,
                                                                skeleton_name,
                                                                name,
                                                                motion_data,
                                                                meta_data, 
                                                                is_processed)

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
            clip_id = input_data.get("clip_id", None)
            token = input_data.get("token", None)
            if self.has_access_to_file(clip_id, token):
                print("delete",clip_id)
                self.motion_database.delete_file_by_id(clip_id)
            else:
                print("Error: has no access rights")
                self.write("Done")
                return
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
            skeleton_name = input_data.get("skeleton",None)
            collection_id = None
            if "collection" in input_data:
                collection_id = input_data["collection_id"]
            elif "collection_id" in input_data:
                collection_id = input_data["collection_id"]
            if collection_id is not None:
                is_processed = int(input_data.get("is_processed", 0))
                motions = self.motion_database.get_motion_list_by_collection(collection_id, skeleton_name, is_processed)
                    
            motions_str = json.dumps(motions)
            self.write(motions_str)

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
                skeleton = input_data.get("skeleton", None)
                exact_match = input_data.get("exact_match", False)
                is_processed = int(input_data.get("is_processed", None))
                collection = self.motion_database.get_motion_list_by_name(name, skeleton, is_processed, exact_match)
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
                            (r"/get_motion", GetMotionHandler),
                            (r"/get_motion_info", GetMotionInfoHandler),
                            (r"/download_bvh", DownloadBVHHandler), 
                            (r"/download_annotation", DownloadAnnotationHandler),
                            (r"/replace_motion", ReplaceMotionHandler),
                            (r"/upload_motion", UploadMotionHandler),
                            (r"/upload_bvh_clip", UploadBVHClipHandler),
                            (r"/delete_motion", DeleteMotionHandler)]