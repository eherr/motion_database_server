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

import os
from motion_database_server.data_transform_database import DataTransformDatabase
from motion_database_server.experiment_database import ExperimentDatabase
from motion_database_server.experiment_database_handlers import EXPERIMENT_DB_HANDLER_LIST
from motion_database_server.data_transform_handlers import DATA_TRANSFORM_HANDLER_LIST
from motion_database_server.service_base import ServiceBase
from motion_database_server.database_wrapper import DatabaseWrapper
from motion_database_server.schema_v2 import DBSchema, TABLES
from motion_database_server.table import Table
from motion_database_server.utils import load_json_file


class DataTransformDatabaseService(ServiceBase, DatabaseWrapper, DataTransformDatabase, ExperimentDatabase):
    """ Wrapper for the DataTransformDatabase class that can be registered as a service
    """
    service_name = "DATA_TRANSFORM_DB"
    def __init__(self, **kwargs):
        self.db_path = kwargs.get("db_path", r"./motion.db")
        self.data_dir = kwargs.get("data_dir","data")
        self.port = kwargs.get("port", 8888)
        self.cluster_url = kwargs.get("cluster_url", None)
        self.cluster_image  = kwargs.get("cluster_image", None)
        self.db_url = kwargs.get("db_url", "localhost")        
        session_file = kwargs.get("session_file", "session.json")
        self.session = dict()
        if os.path.isfile(session_file):
            self.session = load_json_file(session_file)
        self.schema = DBSchema(TABLES)
        self.tables = dict()
        for name in self.schema.tables:
            self.tables[name] = Table(self, name, self.schema.tables[name])
        DataTransformDatabase.__init__(self)
        ExperimentDatabase.__init__(self)
        self.connect_to_database(self.db_path)
        self.request_handler_list = []
        self.request_handler_list += DATA_TRANSFORM_HANDLER_LIST
        self.request_handler_list += EXPERIMENT_DB_HANDLER_LIST