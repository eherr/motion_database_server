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
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LaABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import json
import hashlib
import jwt
import rstr
import string
from motion_database_server.user_database import UserDatabase
from motion_database_server.schema import DBSchema
from motion_database_server.table import Table

JWT_ALGORITHM = 'HS256'

INT_T = "INTERGER"
BLOB_T = "BLOB"
TEXT_T = "TEXT"

TABLES = dict()
TABLES["projects"] = [("name",TEXT_T), # need to be unique
                    ("owner",INT_T),     # user id
                    ("public",INT_T)     # user id
                    ]
TABLES["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("email",TEXT_T), 
                    ("role",TEXT_T)] # is admin or user

TABLES["project_members"] = [("user",INT_T), ("project",INT_T)]



class ProjectDatabase(UserDatabase):
    projects_table = "projects"
    project_members_table = "project_members"
    def __init__(self, schema, server_secret=None):
        super().__init__(schema, server_secret)
    
    def create_project(self, name, owner, public):
        collection_type = "root"
        parent_id = 0
        new_id = self.add_new_collection_by_id(name, collection_type, parent_id, owner, public)
        data = dict()
        data["name"] = name
        data["owner"] = owner
        data["public"] = public
        data["collection"] = new_id
        new_id = self.tables[self.projects_table].create_record(data)
        self.add_project_membership(owner, new_id)

    def add_project_membership(self, user_id, project_id):
        data = dict()
        data["user"] = user_id
        data["project"] = project_id
        self.tables[self.project_members_table].create_record(data)

    def remove_project(self, project_id):
        self.tables[self.projects_table].delete_record_by_id(project_id)
        self.tables[self.project_members_table].delete_record_by_id(project_id)

    def edit_project(self, project_id, name, public, new_user_list):
        data = dict()
        if name is not None:
            data["name"] = name
        if public is not None:
            data["public"] = public
        self.tables[self.projects_table].update_record(project_id, data)
        existing_user_list = self.get_project_member_list(project_id)
        new_user_list = [user[0] for user in new_user_list]
        existing_user_list = [user[0] for user in existing_user_list]
        added_users = [user for user in new_user_list if user not in existing_user_list]
        removed_users = [user for user in existing_user_list if user not in new_user_list]
        for user_id in added_users:
            self.add_project_membership(user_id, project_id)
        for user_id in removed_users:
            self.remove_user_from_project(user_id, project_id)

    def get_project_id(self, project_name, owner_id=None):
        filter_conditions = [("name",project_name)]
        if owner_id is not None:
            filter_conditions += [("owner",owner_id)]
        r = self.query_table(self.projects_table, ["ID"], filter_conditions)
        if len(r) > 0:
            return r[0][0]
        else:
            return -1

    def get_project_owner(self, project_id):
        owner = self.tables[self.projects_table].get_value_of_column_by_id(project_id, "owner")
        if owner is None:
            return -1
        else:
            return owner

    def is_user_in_project(self, project_id, user_id):
        success = False
        users = self.get_project_member_list(project_id)
        success = user_id in users
        return success

    def get_project_list(self, user_id=None):
        #select project list 
        join_statement = None
        intersection_list = []
        if user_id is not None:
            # select cols where id in select id where user is user_id
            intersection_list += [("public", True) ]
            intersection_list += [(self.project_members_table+".user", user_id) ]
            join_statement = " LEFT JOIN "+self.project_members_table+" ON  projects.ID = "+self.project_members_table+".project"

        #query_str = "select distinct p.ID, p.name from projects p left join project_members m ON  p.ID = m.project where m.user == %s or p.public == True;".format(user_id)
        
        return self.tables[self.projects_table].get_record_list(["projects.ID", "name"], intersection_list=intersection_list,join_statement=join_statement, distinct=True)
    
    def get_project_member_list(self, project_id):
        filter_conditions = [("project", project_id)]
        user_records = self.tables[self.project_members_table].get_record_list(["user"], filter_conditions)
        return [(int(ur[0]), self.tables[self.user_table].get_value_of_column_by_id(ur[0], "name")) for ur in user_records]

    def get_user_project_list(self, user_id):
        filter_conditions = [("user", user_id)]
        project_records = self.tables[self.project_members_table].get_record_list(["project"], filter_conditions)

        return [(int(pr[0]), self.tables[self.projects_table].get_value_of_column_by_id(pr[0], "name")) for pr in project_records]

    def add_user_to_project(self, user_id, project_id):
        print("add user to project")
        users = self.get_project_member_list(project_id)
        if user_id in users:
            return
        self.add_project_membership(user_id, project_id)

    def remove_user_from_project(self, user_id, project_id):
        filter_conditions = [("user", user_id), ("project", project_id)]
        self.tables[self.project_members_table].delete_record_by_condition(filter_conditions)
    
    def edit_user(self, user_id, data):
        success = super().edit_user(user_id, data)
        print("edit user", data["project_list"])
        if "project_list" in data:
            for project_entry in data["project_list"]:
                project_id, project_name = project_entry
                self.add_user_to_project(user_id, project_id)
        return success
        
    def remove_user(self, user_id):
        self.delete_entry_by_id(self.user_table, user_id)
        self.delete_entry_by_id(self.project_members_table, user_id)

    def get_user_info(self, user_id):
        data = super().get_user_info(user_id)
        data["project_list"] = self.get_user_project_list(user_id)
        return data

    def get_project_info(self, project_id):
        cols = ["name", "owner", "public", "collection"]
        record = self.tables[self.projects_table].get_record_by_id(project_id, cols)
        if record is None:
            return None
        data = dict()
        for i, k in enumerate(cols):
            data[k] = record[i]
        return data