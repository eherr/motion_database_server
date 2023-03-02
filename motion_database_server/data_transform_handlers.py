

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
import os
import json
import tornado.web
from motion_database_server.base_handler import BaseDBHandler
from motion_database_server.utils import save_json_file
import subprocess
from datetime import datetime



def run_data_transform_script(tmp_dir, data_transform_name, body_data, script, output_type, url, port, user, token, hparams=None):
    tmp_dir = tmp_dir + os.sep +  data_transform_name + datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    os.makedirs(tmp_dir, exist_ok=True)
    script_filename = tmp_dir + os.sep+ data_transform_name +".py"
    with open(script_filename, "wt") as file:
        file.write(script)
    skeleton_type = body_data["skeleton_type"]
    output_id = body_data["output_id"]
    input_data = body_data["input_data"]
    input_ids, input_types,_ = list(map(list,zip(*input_data)))
    store_log = body_data["store_log"]
    exp_name = body_data["exp_name"]
   # kwargs = body_data["kwargs"]
    print("start data transform", data_transform_name,)
    cmd = ["python"]
    cmd += [script_filename]
    cmd += ["--work_dir", tmp_dir]
    cmd += ["--skeleton_type", skeleton_type]
    cmd += ["--output_id", str(output_id)]
    cmd += ["--output_type", output_type]
    cmd += ["--input_ids" ] +list(map(str,input_ids))
    cmd += ["--input_types"] +list(map(str,input_types))
    cmd += ["--store_log", str(store_log)]
    cmd += ["--exp_name", exp_name]
    cmd += ["--url", url]
    cmd += ["--port", str(port)]
    cmd += ["--user", user]
    cmd += ["--token", token]
    if hparams is not None:
        hparams_file = tmp_dir+os.sep+"hparams.json"
        save_json_file(hparams,hparams_file)
        cmd += ["--hparams_file", hparams_file]
    
    print(cmd)
    subprocess.Popen(cmd)


class RunDataTransformHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           body_data = json.loads(input_str)
           success = False
           token = body_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           if role == "admin":
                data_transform_id = str(body_data["data_transform_id"])
                data_transform_info = self.data_transform_service.get_data_transform_info(data_transform_id)
                if data_transform_info is not None:
                    
                    data_transform_name = data_transform_info["name"]
                    data_transform_script = data_transform_info["script"]
                    data_transform_script = data_transform_script.replace("\r\n", "\n")
                    output_type = data_transform_info["outputType"]
                    hparams = body_data.get("hparams",None)
                    tmp_dir = self.data_transform_service.data_dir
                    print("start data transform", data_transform_name)
                    user = self.data_transform_service.session.get("user", None)
                    token = self.data_transform_service.session.get("token", None)
                    url = "localhost"
                    if user is not None and token is not None:
                        port = self.data_transform_service.port
                        run_data_transform_script(tmp_dir, data_transform_name, body_data, 
                                              data_transform_script, output_type, url, port,
                                                user, token, hparams)
                    
                        success = True
                    else:
                        print("Error: missing session")

                else:
                    print("Error: data transform was not registered", data_transform_id)
           else:
               print("Error: no access rights")
           result = dict()
           result["success"] = success
           models_str = json.dumps(result)
           self.write(models_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()




DATA_TRANSFORM_HANDLER_LIST = [(r"/data_transforms/run", RunDataTransformHandler),
]


class GetDataTransformList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        data_loader_list = self.data_transform_service.get_data_transform_list()
        response = json.dumps(data_loader_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        data_loader_list = self.data_transform_service.get_data_transform_list()
        response = json.dumps(data_loader_list)
        self.write(response)




class AddDataTransformHandler(BaseDBHandler):
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
               new_id = self.data_transform_service.create_data_transform(input_data)
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

class EditDataTransformHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           dt_id = input_data["data_transform_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.data_transform_service.edit_data_transform(dt_id, input_data)
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
     

class RemoveDataTransformHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print("delete",input_str)
           input_data = json.loads(input_str)
           dt_id = input_data["data_transform_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           print("delete",input_data)
           if role == "admin":
                print("delete",input_data)
                self.data_transform_service.remove_data_transform(dt_id)
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

class GetDataTransformInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            dt_id = input_data["data_transform_id"]
            info = self.data_transform_service.get_data_transform_info(dt_id)
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

DATA_TRANSFORM_HANDLER_LIST += [
                            (r"/data_transforms", GetDataTransformList),
                            (r"/data_transforms/add", AddDataTransformHandler),
                            (r"/data_transforms/edit", EditDataTransformHandler),
                            (r"/data_transforms/remove", RemoveDataTransformHandler),
                            (r"/data_transforms/info", GetDataTransformInfoHandler)
                            ]
class GetDataTransformInputList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self): 
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            dt_id = input_data["data_transform_id"]
            data_loader_list = self.data_transform_service.get_data_transform_input_list(dt_id)
            response = json.dumps(data_loader_list)
            self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class AddDataTransformInputHandler(BaseDBHandler):
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
               new_id = self.data_transform_service.create_data_transform_input(input_data)
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

class EditDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           dti_id = input_data["data_transform_input_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.data_transform_service.edit_data_transform_input(dti_id, input_data)
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
     

class RemoveDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           dti_id = input_data["data_transform_input_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.data_transform_service.remove_data_transform_input(dti_id)
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

class RemoveAllDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           dt_id = input_data["data_transform_id"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                input_list = self.data_transform_service.get_data_transform_input_list(dt_id)
                for di in input_list:
                    self.data_transform_service.remove_data_transform_input(di[0])
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

class GetDataTransformInputInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            dti_id = input_data["data_transform_input_id"]
            info = self.data_transform_service.get_data_transform_input_info(dti_id)
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


DATA_TRANSFORM_HANDLER_LIST += [
                            (r"/data_transforms/inputs", GetDataTransformInputList),
                            (r"/data_transforms/inputs/add", AddDataTransformInputHandler),
                            (r"/data_transforms/inputs/edit", EditDataTransformInputHandler),
                            (r"/data_transforms/inputs/remove", RemoveDataTransformInputHandler),
                            (r"/data_transforms/inputs/removeall", RemoveAllDataTransformInputHandler),
                            (r"/data_transforms/inputs/info", GetDataTransformInputInfoHandler)
                            ]

