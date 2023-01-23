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



class GetProjectListHandler(BaseDBHandler):
    def get(self):
        project_list = self.app.motion_database.get_project_list()
        response = json.dumps(project_list)
        self.write(response)

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           project_list = self.app.motion_database.get_project_list(user_id)
           response = json.dumps(project_list)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetProjectMemberListHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           project_id = input_data["project_id"]
           project_list = self.app.motion_database.get_project_member_list(project_id)
           response = json.dumps(project_list)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()
        

class AddProjectHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           project_name = input_data["project_name"]
           is_public= input_data["is_public"]
           token = input_data["token"]
           owner_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if owner_id > -1:
               print("create project", project_name)
               self.app.motion_database.create_project(project_name, owner_id, is_public)
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

class EditProjectHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           project_id = input_data["project_id"]
           project_name = input_data["project_name"]
           public = input_data.get("is_public", None)
           token = input_data["token"]
           users = input_data["users"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.app.motion_database.get_project_owner(project_id)
               if user_id == owner_id:
                   self.app.motion_database.edit_project(project_id, project_name, public, users)
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
    
class RemoveProjectHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           project_id = input_data["project_id"]
           token = input_data["token"]
           user_id = self.app.motion_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.app.motion_database.get_project_owner(project_id)
               if user_id == owner_id:
                   self.app.motion_database.remove_project(project_id)
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
    

class GetUserProjectsHandler(BaseDBHandler):
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
               project_list = self.app.motion_database.get_user_project_list(user_id)
               response_dict["project_list"] = project_list
               print(response_dict)
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


class GetProjectInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            project_id = int(input_data["project_id"])
            project_info = self.app.motion_database.get_project_info(project_id)
            response_dict = dict()
            success = False
            if project_info is not None:
                response_dict.update(project_info)
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



PROJECT_DB_HANDLER_LIST = [(r"/projects", GetProjectListHandler),
                            (r"/project_members", GetProjectMemberListHandler),
                            (r"/projects/add", AddProjectHandler),
                            (r"/projects/edit", EditProjectHandler),
                            (r"/projects/remove", RemoveProjectHandler),
                            (r"/user/projects",GetUserProjectsHandler),
                            (r"/projects/info", GetProjectInfoHandler),
                            ]