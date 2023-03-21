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
from motion_database_server.schema import DBSchema, TABLES
from motion_database_server.table import Table

JWT_ALGORITHM = 'HS256'


USER_ROLE_ADMIN = "admin"

INT_T = "INTERGER"
BLOB_T = "BLOB"
TEXT_T = "TEXT"

USER_TABLES = dict()
USER_TABLES["users"] = [("name",TEXT_T),
                    ("password",TEXT_T), 
                    ("email",TEXT_T), 
                    ("role",TEXT_T)] # is admin or user

RESET_PASSWORD_EMAIL_MESSAGE = """Dear %s
Here is your new password:
%s
"""

class UserDatabase(DatabaseWrapper):
    user_table = "users"
    def __init__(self, schema, server_secret=None):
        if schema is None:
            schema = DBSchema(TABLES)
        self.schema =schema
        self.tables = dict()
        for name in self.schema.tables:
            self.tables[name] = Table(self, name, self.schema.tables[name])
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
    
    def create_user(self, name, password, email, role, projects):
        if self.get_user_id_by_name(name) != -1:
            print("Error: user %s already exists"%name)
            return False
        if self.get_user_id_by_email(email) != -1:
            print("Error: email %s already exists"%email)
            return False
        m = hashlib.sha256()
        m.update(bytes(password,"utf-8"))
        password = m.digest()
        data = dict()
        data["name"] = name
        data["password"] = password
        data["email"] = email
        data["role"] = role
        new_id = self.tables[self.user_table].create_record(data)
        return new_id
    
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

            self.tables[self.user_table].update_record(user_id, new_data)
            return True
        except Exception as e:
            print("Error", e.args)
            return False

    def remove_user(self, user_id):
        self.delete_entry_by_id(self.user_table, user_id)


    def get_user_list(self):
        return self.tables[self.user_table].get_record_list(["ID", "name", "role"])

    def get_user_info(self, user_id):
        data = dict()
        record = self.tables[self.user_table].get_record_by_id(user_id, ["name", "email", "role"])
        data["name"] = record[0]
        data["email"] = record[1]
        data["role"] = record[2]
        return data

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
        message = RESET_PASSWORD_EMAIL_MESSAGE%(username, new_password)
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

    def check_rights(self, session):
        if self.enforce_access_rights and "user" in session and "token" in session:
            print(session["user"])
            token = session["token"]
            #role = self.get_user_role(session["user"])
            payload = self.jwt.decode(token, self.server_secret)
            print(payload)
            if "username" in payload:
                return payload["username"] == session["user"]
            elif "user_name" in payload:
                return payload["user_name"] == session["user"]
            else:
                return False
        else:
            return not self.enforce_access_rights
    
    def send_email(self, user, reciever, subject, message_text):
        """TODO """
        return