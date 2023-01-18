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
from motion_database_server.database_wrapper import DatabaseWrapper
from motion_database_server.schema import DBSchema
from motion_database_server.table import Table

JWT_ALGORITHM = 'HS256'

INT_T = "INTERGER"
BLOB_T = "BLOB"
TEXT_T = "TEXT"

TABLES = dict()
TABLES["groups"] = [("name",TEXT_T), # need to be unique
                    ("owner",INT_T),     # user id
                     ("users",TEXT_T)]   #  list of user ids 

TABLES["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("email",TEXT_T), 
                    ("role",TEXT_T), # is admin or user
                    ("sharedAccessGroups",TEXT_T)] # list of group ids with shared access

# every user can be part of multiple groups
# users can share their servers with groups in sharedAccessGroups
# and every user in those groups can have access to it


class UserDatabase(DatabaseWrapper):
    user_table = "users"
    groups_table = "user_groups"
    def __init__(self, server_secret=None):
        self.schema = DBSchema(TABLES)
        self.tables = dict()
        for name in self.schema.tables:
            self.tables[name] = Table(self, name, self.schema[name])
        self.enforce_access_rights = server_secret is not None
        self.jwt = jwt.JWT()
        if server_secret is not None:
            self.server_secret = jwt.jwk.OctetJWK(bytes(server_secret, "utf-8"))
        else:
            self.server_secret = None
        print("set server secret", self.server_secret, self.enforce_access_rights)
    
    def connect(self, path):
        self.connect_to_database(path)

    def create_database(self, path):
        self.connect_to_database(path)
        self.schema.create_tables(self)
        print("created database",path)

    def init_database(self, path, recreate=False):
        create_db = not os.path.isfile(path)
        if create_db or recreate:
            self.create_database(path)
        else:
            self.connect_to_database(path)

    def get_user_id_from_token(self, token):
        user_id = -1
        try:
            payload = self.jwt.decode(token, self.server_secret)
            if "user_id" in payload:
                user_id = payload["user_id"]
        except:
            pass
        return user_id

    def authenticate_user(self, user_name, password):
        """ return user id """
        m = hashlib.sha256()
        m.update(bytes(password,"utf-8"))
        password = m.digest()
        filter_conditions = [("name",user_name)]
        r = self.query_table(self.user_table, ["ID","password"], filter_conditions)
        if  len(r) >0 and r[0][1] == password:
            return r[0][0]
        else:
            return -1

    def generate_token(self, payload):
        if self.server_secret is not None:  
            return self.jwt.encode(payload, self.server_secret, alg=JWT_ALGORITHM)#.decode("utf-8")
        else:
            return ""
    
    def create_user(self, name, password, email, role, sharedAccessGroups):
        if self.get_user_id_by_name(name) != -1:
            print("Error: user %s already exists"%name)
            return False
        if self.get_user_id_by_email(email) != -1:
            print("Error: email %s already exists"%email)
            return False
        m = hashlib.sha256()
        m.update(bytes(password,"utf-8"))
        password = m.digest()
        #records = [[name, password, email, role, sharedAccessGroups]]
        #self.insert_records(self.user_table, ["name", "password", "email","role", "sharedAccessGroups"], records)
       
        data = dict()
        data["name"] = name
        data["password"] = password
        data["email"] = email
        data["role"] = role
        data["sharedAccessGroups"] = sharedAccessGroups
        self.tables[self.user_table].create_record(data)
        return True
    
    def edit_user(self, user_id, data):
        print("update user",user_id)
        record = self.tables[self.user_table].get_record_by_id(user_id, ["name"])
        if record is None:
            return
        try:
            new_data = dict()
            for key in self.tables[self.user_table].cols:
                if key in data:
                    new_data[key] = data[key]
            # check if name change is possible
            if "name" in new_data and self.get_user_id_by_name(new_data["name"]) not in [-1, user_id]:
                print("Warning: user %s already exists and will be ignored"%new_data["name"])
                del new_data["name"]
            if "email" in new_data and self.get_user_id_by_email(new_data["email"]) not in [-1, user_id]:
                print("Warning: email %s already exists and will be ignored"%new_data["email"])
                del new_data["email"]

            if "password" in new_data:
                m = hashlib.sha256()
                m.update(bytes(data["password"],"utf-8"))
                new_data["password"] = m.digest()
            if "sharedAccessGroups" in new_data:
                new_data["sharedAccessGroups"] = json.dumps(data["sharedAccessGroups"])

            self.tables[self.user_table].update_record(user_id, new_data)
            return True
        except Exception as e:
            print("Error", e.args)
            return False
        
    def create_group(self, name, owner):
        data = dict()
        data["name"] = name
        data["owner"] = owner
        data["users"] = "[]"
        self.tables[self.groups_table].create_record(data)

    def add_user_to_group(self, user_id, group_id):
        record = self.tables[self.groups_table].get_record_by_id(group_id, ["users"])
        if record is None:
            return
        users_str = record[0]
        print("group str",users_str)
        try:
            users = json.loads(users_str)
            users = set(users)
            users.add(user_id)
            users = list(users)
            data = dict()
            data["users"] = json.dumps(users)
            self.tables[self.groups_table].update_record(group_id, data)
            print("update", data)
        except Exception as e:
            print("Error", e.args)

    def remove_user_from_group(self, user_id, group_id):
        record = self.tables[self.groups_table].get_record_by_id(group_id, ["users"])
        if record is None:
            return
        users_str = record[0]
        print("group str",users_str)
        try:
            users = json.loads(users_str)
            users = set(users)
            users.discard(user_id)
            users = list(users)
            data = dict()
            data["users"] = json.dumps(users)
            self.tables[self.groups_table].update_record(group_id, data)
            print("update", data)
        except Exception as e:
            print("Error", e.args)

    def grant_group_access_to_user_data(self, group_id, user_id):
        record = self.tables[self.user_table].get_record_by_id(user_id, ["sharedAccessGroups"])
        if record is None:
            return
        groups_str = record[0]
        print("group str",groups_str)
        try:
            groups = json.loads(groups_str)
            groups = set(groups)
            groups.add(group_id)
            groups = list(groups)
            data = dict()
            data["sharedAccessGroups"] = json.dumps(groups)
            self.tables[self.user_table].update_record(user_id, data)
            print("update", data)
        except Exception as e:
            print("Error", e.args)

    def remove_group_access_to_user_data(self, group_id, user_id):
        record = self.tables[self.user_table].get_record_by_id(user_id, ["sharedAccessGroups"])
        if record is None:
            return
        groups_str = record[0]
        print("group str",groups_str)
        try:
            groups = json.loads(groups_str)
            groups = set(groups)
            groups.discard(group_id)
            groups = list(groups)
            data = dict()
            data["sharedAccessGroups"] = json.dumps(groups)
            self.tables[self.user_table].update_record(user_id, data)
            print("update", data)
        except Exception as e:
            print("Error", e.args)

    def remove_user(self, user_id):
        self.delete_entry_by_id(self.user_table, user_id)

    def remove_group(self, group_id):
        self.delete_entry_by_id(self.groups_table, group_id)

    def edit_group(self, group_id, name, user_list):
        data = dict()
        data["name"] = name
        data["users"] = json.dumps(user_list)
        self.tables[self.groups_table].update_record(group_id, data)

    def get_group_id(self, group_name, owner_id=None):
        filter_conditions = [("name",group_name)]
        filter_conditions += [("owner",owner_id)]
        r = self.query_table(self.groups_table, ["ID"], filter_conditions)
        if len(r) > 0:
            return r[0][0]
        else:
            return -1

    def get_group_owner(self, group_id):
        owner = self.tables[self.groups_table].get_value_of_column_by_id(group_id, "owner")
        if owner is None:
            return -1
        else:
            return owner

    def is_user_in_group(self, group_id, user_id):
        success = False
        users = self.get_group_member_list(group_id)
        success = user_id in users
        return success

    def has_access(self, group_id, owner_user_id):
        """ check if request_user is in a group that has access to host shared by owner_user"""
        success = False
        # get all groups with access to user data
        shared_groups = self.get_user_access_group_list(owner_user_id)
        if group_id in shared_groups:
            success = True
        return success
                
    def is_valid_user(self, session):
        if self.enforce_access_rights and "user_id" in session and "token" in session:
            #token = bytes(session["token"], "utf-8")
            token = session["token"]
            payload = self.jwt.decode(token, self.server_secret)
            print("decoded", payload)
            if "user" in payload:
                return payload["user_id"] == session["user_id"]
            else:
                return False
        else:
            return not self.enforce_access_rights

    def get_user_list(self):
        return self.tables[self.user_table].get_record_list(["ID", "name"])
    
    def get_group_list(self):
        return self.tables[self.groups_table].get_record_list(["ID", "name"])
    
    def get_group_member_list(self, group_id):
        user_list_str = self.tables[self.groups_table].get_value_of_column_by_id(group_id, "users")
        users = []
        if user_list_str is not None:
            users = json.loads(user_list_str)
        return users

    def get_user_access_group_list(self, user_id):
        group_list_str = self.tables[self.user_table].get_value_of_column_by_id(user_id, "sharedAccessGroups")
        groups = []
        if group_list_str is not None:
            groups = json.loads(group_list_str)
        return groups

    def get_user_info(self, user_id):
        return self.tables[self.user_table].get_record_by_id(user_id, ["name", "email", "role", "sharedAccessGroups"])

    def get_user_info_by_email(self, email):
        filter_conditions = [("email",email)]
        results = self.query_table(self.user_table,  ["ID", "name"], filter_conditions)
        info = None
        if len(results) > 0:
            info = results[0]
        return info

    def reset_user_password(self, email):
        info = self.get_user_info_by_email(email)
        if info is None:
            print("Error: Did not find user with address", email)
            return False
        new_password = self.generate_new_password()
        user_id = info[0]
        username = info[1]
        data = {"password": new_password}

        if not self.edit_user(user_id, data):
            print("Error: Could not change password")
            return False

        subject = "motion.dfki.de: password reset"
        message = """Dear %s
Here is your new password:
%s
"""%(username, new_password)
        self.send_email(username, email, subject, message)
        return True

    def generate_new_password(self):
        return rstr.rstr(string.digits+string.ascii_letters, 6, 6)
    
    def get_user_id_by_name(self, user_name):
        filter_conditions = [("name",user_name)]
        results = self.query_table(self.user_table,  ["ID"], filter_conditions)
        if len(results) > 0:
            return results[0][0]
        else:
            return -1

    def get_user_id_by_email(self, email):
        filter_conditions = [("email",email)]
        results = self.query_table(self.user_table,  ["ID"], filter_conditions)
        if len(results) > 0:
            return results[0][0]
        else:
            return -1

    def get_user_role(self, user_id):
        role = self.tables[self.user_table].get_value_of_column_by_id(user_id, "role")
        if role is None:
            return ""
        return role

    def get_user_access_rights(self, input_data):
        # set public access
        owner = -1
        public = 1
        # give access to collections owned by user
        if "token" in input_data:
            owner = self.get_user_id_from_token(input_data["token"])
            role = self.get_user_role(owner)
            # allow admin to specify custom filter
            if role == "admin":
                public = -1
                owner = -1
                if "public" in input_data:
                    public = input_data["public"]
                if "owner" in input_data:
                    owner = input_data["owner"]
        return owner, public

    def send_email(self, user, reciever, subject, message_text):
        """TODO """
        return