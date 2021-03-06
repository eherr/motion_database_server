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
import requests
from base_handler import BaseHandler


class StartJobHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
            print("try to start job")
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            name = input_data["name"]
            print("try to start", name, input_data["cmd"])
            success = False
            if name in self.app.server_registry:
                server_info = self.app.server_registry[name]
                has_access = False
                if self.app.activate_user_authentification:
                    token = input_data["token"]
                    group_id = input_data["group_id"]
                    owner_id = server_info["owner_id"]
                    request_user_id = self.app.motion_database.get_user_id_from_token(token)
                    if self.app.motion_database.is_user_in_group(group_id, request_user_id):
                        has_access = self.app.motion_database.has_access(group_id, owner_id)
                else:
                    has_access = True
                if has_access:
                    pload = dict()
                    pload["cmd"] = input_data["cmd"]
                    url_str = server_info["protocol"]+"://"+server_info["address"]+":"+str(server_info["port"])+"/start_job"
                    print(url_str)
                    r = requests.post(url_str, data = json.dumps(pload))
                    success = True
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

class GetJobServerListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    def get(self):
        print("get servers")
        server_registry_copy = list()
        for key in self.app.server_registry:
            data = self.app.server_registry[key]
            status = self.app.get_server_status(key)
            if "n_processes" in status:
                data["n_procesess"] = status["n_processes"]
            #server_registry_copy[key] = data
            server_registry_copy.append(data)
        response = json.dumps(server_registry_copy)
        self.write(response)

class RegisterJobServerHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           name = input_data["name"]
           data = dict()
           success = False
           has_access = False
           if self.app.activate_user_authentification:
               token = input_data["token"]
               data["owner_id"] = self.app.motion_database.get_user_id_from_token(token)
               has_access = True
           else:
                has_access = True
           if has_access:
               data["name"] = input_data["name"] # hostname
               data["user"] = input_data["user"]
               data["address"] = input_data["address"]
               data["port"] = input_data["port"]
               data["protocol"] = input_data["protocol"]
               data["os"] = input_data["os"]
               print("register server", input_data["name"], "for user", data["user"])
               self.app.server_registry[name] = data
               success = True
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


class UnregisterJobServerHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           success = False
           name = input_data["name"]
           if name in self.app.server_registry:
               print("unregister server", input_data["name"], "for user")
               del self.app.server_registry[name]
               success = True
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

class GetUserListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    def get(self):
        user_list = self.app.motion_database.get_user_list()
        response = json.dumps(user_list)
        self.write(response)

class GetUserAccessGroupListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           success = False
           response_dict = dict()
           if "user_id" in input_data:
               user_id = input_data["user_id"]
               group_list = self.app.motion_database.get_user_access_group_list(user_id)
               print("group list", group_list)
               success = True
               response_dict["group_list"] = group_list

           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetGroupListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    def get(self):
        group_list = self.app.motion_database.get_group_list()
        response = json.dumps(group_list)
        self.write(response)


class GetGroupMemberListHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           group_id = input_data["group_id"]
           group_list = self.app.motion_database.get_group_member_list(group_id)
           response = json.dumps(group_list)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()
        
class AddUserHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

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
           success = self.app.motion_database.create_user(user_name, password, email, role, shared_access_groups)

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

class EditUserHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token)
           user_id = request_user_id
           if "user_id" in input_data:
               user_id = int(input_data["user_id"])
           request_user_role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if user_id > -1 and (user_id == request_user_id or request_user_role.lower()=="admin"):
               if "role" in input_data and input_data["role"] == "admin" and request_user_role.lower() != "admin":
                   del input_data["role"]
                   print("Error: Cannot elevate role.")
                
               self.app.motion_database.edit_user(user_id, input_data)
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

class RemoveUserHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           print("Delete user")
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           user_id = input_data["user_id"]
           requesting_user_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if requesting_user_id > -1:
               is_admin = self.app.motion_database.get_user_role(requesting_user_id) == "admin"
               if is_admin or requesting_user_id == user_id:
                   self.app.motion_database.remove_user(user_id)
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

class ResetUserPasswordHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           email = input_data["email"]
           success = self.app.motion_database.reset_user_password(email)
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

class GetUserInfoHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token)
           user_id = request_user_id
           if "user_id" in input_data:
               user_id = int(input_data["user_id"])
           request_user_role = self.app.motion_database.get_user_role(request_user_id)
           if user_id > -1 and (user_id == request_user_id or request_user_role.lower()=="admin"):
               response_dict = dict()
               response_dict["success"] = True
               user_info = self.app.motion_database.get_user_info(user_id)
               response_dict["name"] = user_info[0]
               response_dict["email"] = user_info[1]
               response_dict["role"] = user_info[2]
               response_dict["shared_access_groups"] = user_info[3]
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


class AddGroupHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           group_name = input_data["group_name"]
           token = input_data["token"]
           owner_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if owner_id > -1:
               print("create group", group_name)
               self.app.motion_database.create_group(group_name, owner_id)
               success = True
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

class EditGroupHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           group_id = input_data["group_id"]
           group_name = input_data["group_name"]
           token = input_data["token"]
           users = input_data["users"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.app.motion_database.get_group_owner(group_id)
               if user_id == owner_id:
                   self.app.motion_database.edit_group(group_id, group_name, users)
                   success = True
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
    
class RemoveGroupHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           group_id = input_data["group_id"]
           token = input_data["token"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.app.motion_database.get_group_owner(group_id)
               if user_id == owner_id:
                   self.app.motion_database.remove_group(group_id)
                   success = True
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
    

class GriveAccessToGroupHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           group_name = input_data["group_name"]
           token = input_data["token"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           group_id = self.app.motion_database.get_group_id(group_name)
           success = False
           if user_id > -1 and group_id > -1:
               self.app.motion_database.grant_group_access_to_user_data(group_id, user_id)
               success = True
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


class RemoveAccessFromGroupHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           group_name = input_data["group_name"]
           token = input_data["token"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           group_id = self.app.motion_database.get_group_id(group_name)
           success = False
           if user_id > -1 and group_id > -1:
               self.app.motion_database.remove_group_access_to_user_data(group_id, user_id)
               success = True
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


class LoginHandler(BaseHandler):
    """ Check if user and password exist and returns token"""
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        user_id = -1
        if "name" in input_data and "password" in input_data:
            user = input_data["name"]
            password = input_data["password"]
            user_id = self.app.motion_database.authenticate_user(user, password)
        else:
            print("missing required fields")
        
        result_object = dict()
        result_object["username"] = input_data["name"]
        result_object["user_id"] = user_id
        if user_id > -1:
            print("aunticated user", user_id)
            playload = {"user_id": user_id, "user_name": input_data["name"]}
            result_object["token"] = self.app.motion_database.generate_token(playload)
            result_object["role"] = self.app.motion_database.get_user_role(user_id)
        else:
            print("failed to authenticate user")
        self.write(json.dumps(result_object))

USER_DB_HANDLER_LIST = [(r"/servers/start", StartJobHandler),       
                            (r"/servers/add", RegisterJobServerHandler),
                            (r"/servers/remove", UnregisterJobServerHandler),
                            (r"/servers", GetJobServerListHandler),
                            (r"/users", GetUserListHandler),
                            (r"/users/info", GetUserInfoHandler),
                            (r"/users/edit", EditUserHandler),
                            (r"/users/reset_password", ResetUserPasswordHandler),
                            (r"/users/add", AddUserHandler),
                            (r"/users/remove", RemoveUserHandler),
                            (r"/user_access_groups",GetUserAccessGroupListHandler),
                            (r"/groups", GetGroupListHandler),
                            (r"/group_members", GetGroupMemberListHandler),
                            (r"/groups/add", AddGroupHandler),
                            (r"/groups/edit", EditGroupHandler),
                            (r"/groups/remove", RemoveGroupHandler),
                            (r"/groups/give_access", GriveAccessToGroupHandler),
                            (r"/groups/remove_access", RemoveAccessFromGroupHandler),
                            (r"/users/verify", LoginHandler)
                            ]