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
import bson
import numpy as np
import hashlib
import jwt
from motion_database_server.database_wrapper import DatabaseWrapper
import rstr
import string

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
        self.table_descs = TABLES
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
        for t_name in self.table_descs:
            self.create_table(t_name, self.table_descs[t_name], replace=True)
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
        records = [[name, password, email, role, sharedAccessGroups]]
        self.insert_records(self.user_table, ["name", "password", "email","role", "sharedAccessGroups"], records)
        return True
    
    def edit_user(self, user_id, data):
        print("upder user",user_id)
        filter_conditions = [("ID",user_id)]
        r = self.query_table(self.user_table, ["name"], filter_conditions)
        if len(r) > 0:
            try:
                new_data = dict()
                for e in TABLES["users"]:
                    if e[0] in data:
                       new_data[e[0]] = data[e[0]]
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
                print("data", data)
                print("data", new_data)
                if len(new_data) > 0:
                    self.update_entry(self.user_table, new_data, "ID", user_id)
                else:
                    print("Warning: no data to update")
                return True
            except Exception as e:
                print("Error", e.args)
                return False
        return False
        
    def create_group(self, name, owner):
        users = "[]"
        records = [[name, owner, users]]
        self.insert_records(self.groups_table, ["name", "owner", "users"], records)

    def add_user_to_group(self, user_id, group_id):
        filter_conditions = [("ID",group_id)]
        r = self.query_table(self.groups_table, ["users"], filter_conditions)
        if len(r) > 0:
            users_str = r[0][0]
            print("group str",users_str)
            try:
                users = json.loads(users_str)
                users = set(users)
                users.add(user_id)
                users = list(users)
                data = dict()
                data["users"] = json.dumps(users)
                self.update_entry(self.groups_table, data, "ID", user_id)
                print("update", data)
            except Exception as e:
                print("Error", e.args)

    def remove_user_from_group(self, user_id, group_id):
        filter_conditions = [("ID",group_id)]
        r = self.query_table(self.groups_table, ["users"], filter_conditions)
        if len(r) > 0:
            users_str = r[0][0]
            print("group str",users_str)
            try:
                users = json.loads(users_str)
                users = set(users)
                users.discard(user_id)
                users = list(users)
                data = dict()
                data["users"] = json.dumps(users)
                self.update_entry(self.user_table, data, "ID", user_id)
                print("update", data)
            except Exception as e:
                print("Error", e.args)

    def grant_group_access_to_user_data(self, group_id, user_id):
        filter_conditions = [("ID",user_id)]
        r = self.query_table(self.user_table, ["sharedAccessGroups"], filter_conditions)
        if len(r) > 0:
            groups_str = r[0][0]
            print("group str",groups_str)
            try:
                groups = json.loads(groups_str)
                groups = set(groups)
                groups.add(group_id)
                groups = list(groups)
                data = dict()
                data["sharedAccessGroups"] = json.dumps(groups)
                self.update_entry(self.user_table, data, "ID", user_id)
                print("update", data)
            except Exception as e:
                print("Error", e.args)

    def remove_group_access_to_user_data(self, group_id, user_id):
        filter_conditions = [("ID",user_id)]
        r = self.query_table(self.user_table, ["sharedAccessGroups"], filter_conditions)
        if len(r) > 0:
            groups_str = r[0][0]
            print("group str",groups_str)
            try:
                groups = json.loads(groups_str)
                groups = set(groups)
                groups.discard(group_id)
                groups = list(groups)
                data = dict()
                data["sharedAccessGroups"] = json.dumps(groups)
                self.update_entry(self.user_table, data, "ID", user_id)
                print("update", data)
            except Exception as e:
                print("Error", e.args)

    def remove_user(self, user_id):
        self.delete_entry_by_id(self.user_table, user_id)

    def remove_group(self, group_id):
        self.delete_entry_by_id(self.groups_table, group_id)

    def edit_group(self, group_id, name, user_list):
        filter_conditions = [("ID",group_id)]
        r = self.query_table(self.groups_table, ["name"], filter_conditions)
        if len(r) > 0:
            try:
                data = dict()
                data["name"] = name
                data["users"] = json.dumps(user_list)
                self.update_entry(self.groups_table, data, "ID", group_id)
            except Exception as e:
                print("Error", e.args)

    def get_group_id(self, group_name, owner_id=None):
        filter_conditions = [("name",group_name)]
        filter_conditions += [("owner",owner_id)]
        r = self.query_table(self.groups_table, ["ID"], filter_conditions)
        if len(r) > 0:
            return r[0][0]
        else:
            return -1

    def get_group_owner(self, group_id):
        filter_conditions = [("ID",group_id)]
        r = self.query_table(self.groups_table, ["owner"], filter_conditions)
        if len(r) > 0:
            return r[0][0]
        else:
            return -1
        return

    def is_user_in_group(self, group_id, user_id):
        success = False
        filter_conditions = [("ID",group_id)]
        r = self.query_table(self.groups_table, ["users"], filter_conditions)
        if len(r) > 0:
            users_str = r[0][0]
            try:
                users = json.loads(users_str)
                success = user_id in users
            except:
                pass
        return success

    def has_access(self, group_id, owner_user_id):
        """ check if request_user is in a group that has access to host shared by owner_user"""
        
        success = False
        # get all groups with access to user data
        filter_conditions = [("ID",owner_user_id)]
        results = self.query_table(self.user_table, ["sharedAccessGroups"], filter_conditions)
        if len(results) > 0:
            shared_groups = results[0][0]
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
        filter_conditions = []
        results = self.query_table(self.user_table, ["ID", "name"], filter_conditions)
        return results
    
    def get_group_list(self):
        filter_conditions = []
        results = self.query_table(self.groups_table, ["ID", "name"], filter_conditions)
        return results
    
    def get_group_member_list(self, group_id):
        filter_conditions = [("ID",group_id)]
        results = self.query_table(self.groups_table, ["users"], filter_conditions)
        users = []
        if len(results) > 0:
            users = json.loads(results[0][0])
        return users

    def get_user_access_group_list(self, user_id):
        filter_conditions = [("ID",user_id)]
        results = self.query_table(self.user_table, ["sharedAccessGroups"], filter_conditions)
        users = []
        if len(results) > 0:
            users = json.loads(results[0][0])
        return users

    def get_user_info(self, user_id):
        filter_conditions = [("ID",user_id)]
        results = self.query_table(self.user_table,  ["name", "email", "role", "sharedAccessGroups"], filter_conditions)
        info = None
        if len(results) > 0:
            info = results[0]
        return info

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
        
    def send_email(self, user, reciever, subject, message_text):
        """TODO """
        return

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
        filter_conditions = [("ID",user_id)]
        results = self.query_table(self.user_table,  ["role"], filter_conditions)
        if len(results) > 0:
            return results[0][0]
        else:
            return ""

