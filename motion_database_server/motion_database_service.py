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
import requests
from motion_database_server.motion_file_database import MotionFileDatabase
from motion_database_server.kubernetes_interface import load_kube_config
from motion_database_server.skeleton_database_handlers import SKELETON_DB_HANDLER_LIST
from motion_database_server.model_graph_database_handlers import MODEL_GRAPH_HANDLER_LIST
from motion_database_server.mg_model_handlers import MG_MODEL_HANDLER_LIST
from motion_database_server.character_storage_handlers import CHARACTER_HANDLER_LIST
from motion_database_server.files_database_handlers import FILE_DB_HANDLER_LIST
from motion_database_server.motion_database_handlers import MOTION_DB_HANDLER_LIST
from motion_database_server.model_database_handlers import MODEL_DB_HANDLER_LIST
from motion_database_server.collection_database_handlers import COLLECTION_DB_HANDLER_LIST
from motion_database_server.service_base import ServiceBase



class MotionDatabaseService(ServiceBase):
    """ Wrapper for the MotionDatabase class that can be registered as a service
    """
    service_name = "MOTION_DB"
    def __init__(self, **kwargs):
        self.db_path = kwargs.get("db_path", r"./motion.db")
        kube_config = kwargs.get("kube_config", None)
        if kube_config is not None:
            load_kube_config(kube_config["config_file"])
            self.k8s_namespace = kube_config["namespace"]
        else:
            self.k8s_namespace = ""
        self.motion_database = MotionFileDatabase(data_dir="data",port=8888)
        self.motion_database.connect_to_database(self.db_path)
        self.motion_database.load_skeletons()
        self.request_handler_list = []
        self.request_handler_list += SKELETON_DB_HANDLER_LIST
        self.request_handler_list += COLLECTION_DB_HANDLER_LIST
        self.request_handler_list += FILE_DB_HANDLER_LIST
        self.request_handler_list += MODEL_GRAPH_HANDLER_LIST

        # legacy
        self.request_handler_list += CHARACTER_HANDLER_LIST
        self.request_handler_list += MG_MODEL_HANDLER_LIST
        self.request_handler_list += MOTION_DB_HANDLER_LIST
        self.request_handler_list += MODEL_DB_HANDLER_LIST
        
        
        self.server_registry = dict()

    def get_server_status(self, name):
        result = dict()
        if name not in self.server_registry:
            return result
        server_address = self.server_registry[name]["address"]
        server_port = self.server_registry[name]["port"]
        url_str = "http://" + server_address + ":" + str(server_port)+'/status'
        try:
            r = requests.get(url_str)
            r_dict = json.loads(r.text)
            if "success" in r_dict:
                result = r_dict
            else:
                print("Failed to register server")
        except Exception as e:
            print("Exception during registration", e.args)
        return result
