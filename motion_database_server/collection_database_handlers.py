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
import tornado.web
from motion_database_server.base_handler import BaseDBHandler

class MotionDBHandler(BaseDBHandler):
    def has_access_to_collection(self, data):
        collection_id = data.get("id", None)
        if collection_id is None:
            return False
        token = data.get("token", None)
        if token is None:
            return False
        owner_id = self.motion_database.get_owner_of_collection(collection_id)
        request_user_id = self.project_database.get_user_id_from_token(token)
        role = self.motion_database.get_user_role(request_user_id)
        return request_user_id == owner_id or role == USER_ROLE_ADMIN



class NewCollectionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            success = False
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            if "token" in input_data and "name" in input_data and "type" in input_data and "parent_id" in input_data:
                token = input_data["token"]
                request_user_id = self.project_database.get_user_id_from_token(token)
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
            owner, public = self.project_database.get_user_access_rights(input_data)
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
            owner, public = self.project_database.get_user_access_rights(input_data)
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


class ReplaceCollectionHandler(MotionDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            success = False
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            if self.has_access_to_collection(input_data):
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



class RemoveCollectionHandler(MotionDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            success = False
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            if self.has_access_to_collection(input_data):
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


LEGACY_COLLECTION_DB_HANDLER_LIST = [(r"/get_collection_list", GetCollectionListHandler),
                            (r"/get_collection", GetCollectionHandler),
                            (r"/replace_collection", ReplaceCollectionHandler),
                            (r"/create_new_collection", NewCollectionHandler),
                            (r"/remove_collection", RemoveCollectionHandler),
                            (r"/get_collections_by_name", GetCollectionsByNameHandler),
                            (r"/get_collection_tree", GetCollectionTreeHandler)]


COLLECTION_DB_HANDLER_LIST = LEGACY_COLLECTION_DB_HANDLER_LIST+ [
                            (r"/collections", GetCollectionListHandler),
                            (r"/collections/info", GetCollectionHandler),
                            (r"/collections/replace", ReplaceCollectionHandler),
                            (r"/collections/add", NewCollectionHandler),
                            (r"/collections/remove", RemoveCollectionHandler),
                            (r"/collections/tree", GetCollectionTreeHandler)]