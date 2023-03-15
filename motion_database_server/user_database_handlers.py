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
import tornado.web
from motion_database_server.base_handler import BaseDBHandler


class GetUserListHandler(BaseDBHandler):
    def get(self):
        user_list = self.project_database.get_user_list()
        response = json.dumps(user_list)
        self.write(response)

class AddUserHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           user_name = input_data["name"]
           password = input_data["password"]
           email = input_data["email"]
           role = input_data["role"] # maybe limit the role
           shared_access_groups = "[]"
           new_id = self.project_database.create_user(user_name, password, email, role, shared_access_groups)

           response_dict = dict()
           response_dict["success"] = new_id > -1
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class EditUserHandler(BaseDBHandler):
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token)
           user_id = request_user_id
           if "user_id" in input_data:
               user_id = int(input_data["user_id"])
           request_user_role = self.project_database.get_user_role(request_user_id)
           success = False
           if user_id > -1 and (user_id == request_user_id or request_user_role.lower()=="admin"):
               if "role" in input_data and input_data["role"] == "admin" and request_user_role.lower() != "admin":
                   del input_data["role"]
                   print("Error: Cannot elevate role.")
                
               self.project_database.edit_user(user_id, input_data)
               success = True
           response = dict()
           response["success"] = success
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class RemoveUserHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           print("Delete user")
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           user_id = input_data["user_id"]
           requesting_user_id = self.project_database.get_user_id_from_token(token)
           success = False
           if requesting_user_id > -1:
               is_admin = self.project_database.get_user_role(requesting_user_id) == "admin"
               if is_admin or requesting_user_id == user_id:
                   self.project_database.remove_user(user_id)
                   success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class ResetUserPasswordHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           email = input_data["email"]
           success = self.project_database.reset_user_password(email)
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetUserInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token)
           user_id = request_user_id
           if "user_id" in input_data:
               user_id = int(input_data["user_id"])
           request_user_role = self.project_database.get_user_role(request_user_id)
           if user_id > -1 and (user_id == request_user_id or request_user_role.lower()=="admin"):
               response_dict = dict()
               response_dict["success"] = True
               user_info = self.project_database.get_user_info(user_id)
               response_dict.update(user_info)
               response = json.dumps(response_dict)
               self.write(response)
               success = True
           else:
               response_dict = dict()
               response_dict["success"] = False
               response = json.dumps(response_dict)
               self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class LoginHandler(BaseDBHandler):
    """ Check if user and password exist and returns token"""
    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        user_id = -1
        if "username" in input_data and "password" in input_data:
            user = input_data["username"]
            password = input_data["password"]
            user_id = self.project_database.authenticate_user(user, password)
        else:
            print("missing required fields")
        
        result_object = dict()
        result_object["user_id"] = user_id
        if user_id > -1:
            print("aunticated user", user_id)
            result_object["username"] = input_data["username"]
            playload = {"user_id": user_id, "username": input_data["name"]}
            result_object["token"] = self.project_database.generate_token(playload)
            result_object["role"] = self.project_database.get_user_role(user_id)
        else:
            print("failed to authenticate user")
        self.write(json.dumps(result_object))

class AuthenticateHandler(BaseDBHandler):
    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        user_id = -1
        if "username" in input_data and "password" in input_data:
            user = input_data["username"]
            password = input_data["password"]
            user_id = self.project_database.authenticate_user(user, password)
        else:
            print("missing required fields")
        
        result_object = dict()
        result_object["user_id"] = user_id
        if user_id > -1:
            print("aunticated user", user_id)
            result_object["username"] = input_data["username"]
            playload = {"user_id": user_id, "username": input_data["username"]}
            result_object["token"] = self.project_database.generate_token(playload)
            result_object["role"] = self.project_database.get_user_role(user_id)
        else:
            print("failed to authenticate user")
        self.write(json.dumps(result_object))


USER_DB_HANDLER_LIST = [(r"/users", GetUserListHandler),
                            (r"/users/info", GetUserInfoHandler),
                            (r"/users/edit", EditUserHandler),
                            (r"/users/reset_password", ResetUserPasswordHandler),
                            (r"/users/add", AddUserHandler),
                            (r"/users/remove", RemoveUserHandler),
                            (r"/users/verify", LoginHandler),
                            (r"/authenticate", AuthenticateHandler)
                            ]