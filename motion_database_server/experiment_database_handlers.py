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



class JSONHandler(BaseDBHandler):
    def __init__(self, method, application, request, **kwargs):
        self.method = method
        super().__init__(application, request, **kwargs)

    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_dict = json.loads(input_str)
           response_dict = self.method(self, input_dict)
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetExperimentList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           project = input_data.get("project",None)
           collection = input_data.get("collection",None)
           skeleton = input_data.get("skeleton",None)
           exp_list = self.data_transform_service.get_experiment_list(project, collection, skeleton)
           response = json.dumps(exp_list)
           self.write(response)
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class AddExperimentHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           owner_id = self.project_database.get_user_id_from_token(token)
           success = False
           response_dict = dict()
           if owner_id > -1:
               input_data["owner"] = owner_id
               new_id = self.data_transform_service.create_experiment(input_data)
               response_dict["id"] = new_id
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

class EditExperimentHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           experiment_id = input_data["experiment_id"]
           token = input_data["token"]
           user_id = self.project_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.data_transform_service.get_experiment_owner(experiment_id)
               if user_id == owner_id:
                   self.data_transform_service.edit_experiment(experiment_id, input_data)
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
    
class AppendExperimentLogHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           experiment_id = input_data["experiment_id"]
           token = input_data["token"]
           log_entry = input_data["log_entry"]
           user_id = self.project_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.data_transform_service.get_experiment_owner(experiment_id)
               if user_id == owner_id:
                   self.data_transform_service.append_experiment_log(experiment_id, log_entry)
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
    
class RemoveExperimentHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           exp_id = input_data["experiment_id"]
           token = input_data["token"]
           user_id = self.project_database.get_user_id_from_token(token)
           success = False
           if user_id > -1:
               owner_id = self.data_transform_service.get_experiment_owner(exp_id)
               if user_id == owner_id:
                    self.data_transform_service.remove_experiment(exp_id)
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
    

class GetExperimentInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            exp_id = int(input_data["experiment_id"])
            exp_info = self.data_transform_service.get_experiment_info(exp_id)
            response_dict = dict()
            success = False
            if exp_info is not None:
                response_dict.update(exp_info)
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


class GetExperimentLogHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            exp_id = int(input_data["experiment_id"])
            result = self.data_transform_service.get_experiment_log(exp_id)
            response_dict = dict()
            success = False
            if result is not None:
                field_names, log_data = result
                response_dict["log_data"] = log_data
                response_dict["field_names"] = field_names
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



EXPERIMENT_DB_HANDLER_LIST = [(r"/experiments", GetExperimentList),
                            (r"/experiments/add", AddExperimentHandler),
                            (r"/experiments/append_log", AppendExperimentLogHandler),
                            (r"/experiments/edit", EditExperimentHandler),
                            (r"/experiments/remove", RemoveExperimentHandler),
                            (r"/experiments/info", GetExperimentInfoHandler),
                             (r"/experiments/log", GetExperimentLogHandler),
                            ]

                 
class GetExperimentInputList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            experiment = input_data["experiment"]
            data_loader_list = self.data_transform_service.get_experiment_input_list(experiment)
            response = json.dumps(data_loader_list)
            self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()




class AddExperimentInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               new_id = self.data_transform_service.create_experiment_input(input_data)
               response_dict["id"] = new_id
               response_dict["success"] = True
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class EditExperimentInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           dti_id = input_data["experiment_input_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.data_transform_service.edit_experiment_input(dti_id, input_data)
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
     

class RemoveExperimentInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           dti_id = input_data["experiment_input_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.data_transform_service.remove_experiment_input(dti_id)
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

class GetExperimentInputInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            dti_id = input_data["experiment_input_id"]
            info = self.data_transform_service.get_experiment_input_info(dti_id)
            response_dict = dict()
            success = False
            if info is not None:
                response_dict.update(info)
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


EXPERIMENT_DB_HANDLER_LIST += [
                            (r"/experiments/inputs", GetExperimentInputList),
                            (r"/experiments/inputs/add", AddExperimentInputHandler),
                            (r"/experiments/inputs/edit", EditExperimentInputHandler),
                            (r"/experiments/inputs/remove", RemoveExperimentInputHandler),
                            (r"/experiments/inputs/info", GetExperimentInputInfoHandler)
                            ]