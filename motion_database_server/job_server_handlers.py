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
import tornado.web
import requests
import subprocess
from multiprocessing import Process
from motion_database_server.base_handler import BaseDBHandler
from motion_database_server.kubernetes_interface import start_kube_job, stop_kube_job


class StartClusterJobHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           has_access = self.project_database.check_rights(input_data)
           if not has_access:
               print("Error: no access rights")
               self.write("Error: no access right")
            
           namespace = self.app.k8s_namespace
           image_name = input_data["image_name"]
           job_name = input_data["job_name"]
           job_desc = input_data["job_desc"]
           resources = input_data["resources"]
           try:
               stop_kube_job(namespace, job_name)
           except:
               pass
           start_kube_job(namespace, job_name, image_name, job_desc, resources)
           print("start job", job_name)
           self.write("start job")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class StartMGServerHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           has_access = self.project_database.check_rights(input_data)
           if not has_access:
                print("Error: no access rights")
                self.write("Error: no access right")
           if "graph_id" in input_data:
               graph_id = input_data["graph_id"]
               p = Process(target=subprocess.call, args=("python run_websocket_server.py ",))
               p.start()
               
               print("start server")
           self.write("start server")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class StartJobHandler(BaseDBHandler):
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
                    request_user_id = self.project_database.get_user_id_from_token(token)
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

class GetJobServerListHandler(BaseDBHandler):
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

class RegisterJobServerHandler(BaseDBHandler):
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
               data["owner_id"] = self.project_database.get_user_id_from_token(token)
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


class UnregisterJobServerHandler(BaseDBHandler):
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


JOB_SERVER_HANDLER_LIST = [(r"/start_cluster_job", StartClusterJobHandler),
                            (r"/start_mg_state_server", StartMGServerHandler),
                            (r"/servers/start", StartJobHandler),       
                            (r"/servers/add", RegisterJobServerHandler),
                            (r"/servers/remove", UnregisterJobServerHandler),
                            (r"/servers", GetJobServerListHandler)]