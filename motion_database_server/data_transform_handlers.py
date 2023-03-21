

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
import sys
from sys import platform
import json
import tornado.web
from motion_database_server.base_handler import BaseDBHandler
from motion_database_server.utils import save_json_file
import subprocess
from datetime import datetime
from paramiko.client import SSHClient
import shutil
import stat

IS_WINDOWS = platform.startswith("win")

SHELL_SCRIPT_SUFFIX = "sh" 
if IS_WINDOWS:
    SHELL_SCRIPT_SUFFIX = "bat"

PYTHON_SCRIPT_SUFFIX = """ 
from motion_db_interface import parse_arguments
if __name__ == "__main__":
    main(**parse_arguments())
"""

os.environ["WANDB_API_KEY"] = "3195d8372135da1ac5afa1cef7fa2cb9787fc43b"
partition = "RTX6000,RTX3090,RTXA6000,batch" 
memory = "64000M"
n_cpus = 64 # 32
use_gpu = False

def create_python_command(script_filename, work_dir, body_data,output_type, db_url, db_port, db_user, db_token, hparams_file=None):
    input_skeleton = body_data["input_skeleton"]
    output_skeleton = body_data["output_skeleton"]
    output_id = body_data["output_id"]
    input_data = body_data["input_data"]
    input_ids, input_types = [], []
    if len(input_data) > 0:
        input_ids, input_types,_ = list(map(list,zip(*input_data)))    
    store_log = body_data["store_log"]
    exp_name = body_data["exp_name"]
    cmd = ["python"]
    cmd += [script_filename]
    cmd += ["--work_dir", work_dir]
    cmd += ["--input_skeleton", input_skeleton]
    cmd += ["--output_skeleton", output_skeleton]
    cmd += ["--output_id", str(output_id)]
    cmd += ["--output_type", output_type]
    cmd += ["--input_ids" ] +list(map(str,input_ids))
    cmd += ["--input_types"] +list(map(str,input_types))
    cmd += ["--store_log", str(store_log)]
    cmd += ["--exp_name", exp_name]
    cmd += ["--url", db_url]
    cmd += ["--port", str(db_port)]
    cmd += ["--user", db_user]
    cmd += ["--token", db_token]
    if hparams_file is not None:
        cmd += ["--hparams_file", hparams_file]
    return cmd

def create_remote_txt_file(sftp, text, local_filename, remote_filename, make_executable=False):
    with open(local_filename, "wt") as file:
        file.write(text)
    sftp.put(local_filename, remote_filename)
    if make_executable:
        sftp.chmod(remote_filename, stat.S_IEXEC)
    
    

def run_data_transform_on_cluster(cluster_config, tmp_dir, data_transform_name, body_data, script, output_type, db_url, db_port, db_user, db_token, hparams=None, requirements=None):
    
    client = SSHClient()
    client.load_system_host_keys()
    cluster_url = cluster_config["url"]
    cluster_user = cluster_config["user"]
    cluster_password = cluster_config["password"]
    client.connect(cluster_url, username=cluster_user, password=cluster_password)
    root_home = "/home/"+cluster_user
    sftp = client.open_sftp()
    
    local_tmp_dir = tmp_dir + os.sep +  data_transform_name + datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    remote_work_dir = root_home + os.sep +  data_transform_name + datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    os.makedirs(tmp_dir, exist_ok=True)
    sftp.mkdir(remote_work_dir)
    client.exec_command("cd "+remote_work_dir)


    #copy python script
    script_filename = local_tmp_dir + os.sep+ data_transform_name +".py"
    remote_script_filename = remote_work_dir + os.sep+ data_transform_name +".py"
    create_remote_txt_file(sftp, script, script_filename, remote_script_filename, True)

    remote_hparams_file = None
    if hparams is not None:
        hparams_file = local_tmp_dir+os.sep+"hparams.json"
        remote_hparams_file = remote_work_dir+os.sep+"hparams.json"
        create_remote_txt_file(sftp, json.dumps(hparams), hparams_file, remote_hparams_file, False)

    shutil.rmtree(local_tmp_dir, ignore_errors=True)
    
  
    # create shell script with requirements and call to python script
    local_shell_script = local_tmp_dir+os.sep+"job.sh"
    remote_shell_script = remote_work_dir+os.sep+"job.sh"
    job_script = "#!/bin/bash + \n"
    if requirements is not None and requirements != "":
        job_script += requirements + "\n"
    python_cmd = create_python_command(remote_script_filename, remote_work_dir, body_data, output_type, db_url, db_port, db_user, db_token, remote_hparams_file)
    job_script += " ".join(python_cmd)
    create_remote_txt_file(sftp, job_script, local_shell_script, remote_shell_script, True)

    mounts = "/netscratch/"+cluster_user+":/netscratch/"+cluster_user+",/ds:/ds:ro,"+remote_work_dir+":"+remote_work_dir

    cmd = "srun --container-workdir="+remote_work_dir + \
            " --container-mounts="+mounts + \
            " --container-image="+cluster_config["image"] +  \
            " --mem="+memory +  \
            " -p "+partition +\
            " --cpus-per-task=" + str(n_cpus) + \
            " --gres=gpu:"+str(int(use_gpu)) + \
            " job.sh"
    stdin, stdout, stderr = client.exec_command(cmd)
    #sftp.close()

def run_data_transform_script(tmp_dir, data_transform_name, body_data, script, output_type, db_url, db_port, db_user, db_token, hparams=None, requirements=None):
    tmp_dir = tmp_dir + os.sep +  data_transform_name + datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    os.makedirs(tmp_dir, exist_ok=True)

    if requirements is not None and requirements != "":
        req_file = tmp_dir+os.sep+"requirements." + SHELL_SCRIPT_SUFFIX
        with open(req_file, "wt") as file:
            file.write(requirements)
        if not IS_WINDOWS:
            os.chmod(req_file, stat.S_IEXEC)
        subprocess.call([req_file])

    script_filename = tmp_dir + os.sep+ data_transform_name +".py"
    with open(script_filename, "wt") as file:
        file.write(script)
    if not IS_WINDOWS:
        os.chmod(script_filename, stat.S_IEXEC)
    if hparams is not None:
        hparams_file = tmp_dir+os.sep+"hparams.json"
        save_json_file(hparams,hparams_file)
    print("start data transform", data_transform_name)
    python_cmd =  create_python_command(script_filename, tmp_dir, body_data, output_type, db_url, db_port, db_user, db_token, hparams_file)

    
    print(python_cmd)
    subprocess.Popen(python_cmd)


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
                    requirements = data_transform_info["requirements"]
                    data_transform_script = data_transform_script.replace("\r\n", "\n")
                    data_transform_script += PYTHON_SCRIPT_SUFFIX
                    output_type = data_transform_info["outputType"]
                    cluster_config = data_transform_info.get("cluster_config", None)
                    hparams = body_data.get("hparams",None)
                    tmp_dir = self.data_transform_service.data_dir
                    print("start data transform", data_transform_name)
                    db_user = self.data_transform_service.session.get("user", None)
                    db_token = self.data_transform_service.session.get("token", None)
                    db_url = self.data_transform_service.db_url
                    db_port = self.data_transform_service.port
                    if db_user is not None and db_token is not None:
                        if cluster_config is not None:
                            cluster_config["url"] =  self.data_transform_service.cluster_url
                            cluster_config["image"] = self.data_transform_service.cluster_image
                            run_data_transform_on_cluster(cluster_config, tmp_dir, data_transform_name, body_data, 
                                              data_transform_script, output_type, db_url, db_port,
                                                db_user, db_token, hparams, requirements)
                        else:
                            run_data_transform_script(tmp_dir, data_transform_name, body_data, 
                                              data_transform_script, output_type, db_url, db_port,
                                                db_user, db_token, hparams, requirements)
                    
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



class DataTransformExportHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def get(self):
        try:
            data = self.data_transform_service.data_transforms_to_dict()
            response_dict = dict()
            success = False
            if data is not None:
                response_dict.update(data)
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
                            (r"/data_transforms/inputs/info", GetDataTransformInputInfoHandler),
                            (r"/data_transforms/export", DataTransformExportHandler)
                            ]

