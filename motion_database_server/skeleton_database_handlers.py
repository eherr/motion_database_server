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
import json
import bson
import bz2
import tornado.web
from motion_database_server.base_handler import BaseHandler

DEFAULT_SKELETON = "custom"


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


SKELETON_DB_HANDLER_LIST = [(r"/get_skeleton_list", GetSkeletonListHandler),
                            (r"/get_skeleton", GetSkeletonHandler),
                            (r"/get_skeleton_model", GetSkeletonModelHandler),
                            (r"/create_new_skeleton", NewSkeletonHandler),
                            (r"/replace_skeleton", ReplaceSkeletonHandler),
                            (r"/remove_skeleton", RemoveSkeletonHandler)]