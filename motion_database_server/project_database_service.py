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

from motion_database_server.project_database import ProjectDatabase
from motion_database_server.user_database_handlers import USER_DB_HANDLER_LIST
from motion_database_server.project_database_handlers import PROJECT_DB_HANDLER_LIST
from motion_database_server.service_base import ServiceBase
from motion_database_server.schema_v2 import DBSchema, TABLES


class ProjectDatabaseService(ServiceBase):
    """ Wrapper for the Project Service class that can be registered as a service
    """
    service_name = "PROJECT_DB"
    def __init__(self, **kwargs):
        self.db_path = kwargs.get("db_path", r"./motion.db")
        self.server_secret = kwargs.get("server_secret", None)
        self.activate_port_forwarding = kwargs.get("activate_port_forwarding", False)
        self.activate_user_authentification = kwargs.get("activate_user_authentification", True)
        schema = DBSchema(TABLES)
        self.project_database = ProjectDatabase(schema, server_secret=self.server_secret)
        self.project_database.connect(self.db_path)
        self.request_handler_list = USER_DB_HANDLER_LIST + PROJECT_DB_HANDLER_LIST

