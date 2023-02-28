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
import json
import bson
import bz2
import tornado.web
from motion_database_server.base_handler import BaseDBHandler
import base64
USER_ROLE_ADMIN = "admin"

class ModelDBHandler(BaseDBHandler):
    def has_access(self, data):
        m_id = data.get("model_id", None)
        if m_id is None:
            return False
        token = data.get("token", None)
        if token is None:
            return False
        owner_id = self.motion_database.get_owner_of_file(m_id)
        request_user_id = self.motion_database.get_user_id_from_token(token)
        role = self.app.motion_database.get_user_role(request_user_id)
        return request_user_id == owner_id or role == USER_ROLE_ADMIN

class GetModelList(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            collection = input_data.get("collection", None)
            data_type = input_data.get("format", None)
            skeleton = input_data.get("skeleton", None)
            models = []
            if collection is not None:
                tags = ["model"]
                models = self.motion_database.get_file_list(collection, skeleton, data_type, tags=tags)
                print(models)
            models_str = json.dumps(models)
            self.write(models_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class AddModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            response_dict = dict()
            success = False
            if "collection" in input_data and "data" in input_data and self.motion_database.check_rights(input_data):
                input_data["data"] = base64.b64decode(input_data["data"])
                if "format" in input_data:
                    input_data["dataType"] = input_data["format"]
                new_id = self.motion_database.create_file(input_data)
                response_dict["id"] = new_id
                success = True
            else:
                print("Error: did not find expected input data")
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class RemoveModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            success = False
            response_dict = dict()
            if self.has_access(input_data):
                m_id = input_data["model_id"]
                print("Error: has no access rights")
                self.motion_database.delete_file_by_id(m_id)
                success = True

            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadModelHandler(ModelDBHandler):

    def set_default_headers(self):
        super(DownloadModelHandler, self).set_default_headers()
        self.set_header('Content-Type', 'application/octet-stream')

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)

            input_data = json.loads(input_str)
            data = self.motion_database.get_file_by_id(input_data["model_id"])
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


class ReplaceModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            response_dict = dict()
            success = False
            if self.has_access(input_data):
                success = True
                m_id = input_data["model_id"]
                if "data" in input_data:
                    input_data["data"] = base64.b64decode(input_data["data"])
                if "metaData" in input_data:
                    input_data["metaData"] = base64.b64decode(input_data["metaData"])
                self.motion_database.replace_file(m_id, input_data)
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


MODEL_DB_HANDLER_LIST = [(r"/models", GetModelList),
                            (r"/models/add", AddModelHandler),
                            (r"/models/replace", ReplaceModelHandler),
                            (r"/models/remove", RemoveModelHandler),
                            (r"/models/download", DownloadModelHandler)
                            ]