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
from motion_database_server.base_handler import BaseDBHandler


class GetCharacterModelListHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_json = json.loads(input_str)
            skeleton_type = input_json['skeleton_type']
            characters = self.motion_database.get_character_model_list(skeleton_type)
            characters_str = json.dumps(characters)
            self.write(characters_str)
        except Exception as e:
            print("caught exception in post method")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class UploadCharacterModelHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.project_database.check_rights(input_data)
            success = False
            if has_access:
                if "name" in input_data and "skeleton_type" in input_data and "data" in input_data:
                    name = input_data['name']
                    skeleton_type = input_data['skeleton_type'] 
                    data = input_data['data']
                    data = bytearray(data) # https://www.w3resource.com/python-exercises/python-basic-exercise-118.php
                    success = self.motion_database.store_character_model(name, skeleton_type, data)
                else:
                    print("Error: Not all parameters provided")
            else:
                print("Error: Not enough access rights")
            response_dict = dict()
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)
        except Exception as e:
            print("caught exception in %s", e)
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DeleteCharacterModelHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        print("Post method for deleting GLB file from server")
        try:
            input_str = self.request.body.decode("utf-8")
            input_json = json.loads(input_str)
            name = input_json['name']
            skeleton_type = input_json['skeleton_type'] 
            self.motion_database.delete_character_model(name, skeleton_type)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class DownloadCharacterModelHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        print("Post method for binary file loading")
        try:
            input_str = self.request.body.decode("utf-8")
            input_json = json.loads(input_str)
            name = input_json['name']
            skeleton_type = input_json['skeleton_type'] 
            data = self.motion_database.get_character_model_data(name, skeleton_type)
            if data is not None:
                self.write(data)
            else:
                print("Error: could not read file")
        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


CHARACTER_HANDLER_LIST = [(r"/get_character_model_list", GetCharacterModelListHandler),
                            (r"/upload_character_model", UploadCharacterModelHandler),
                            (r"/delete_character_model", DeleteCharacterModelHandler),
                            (r"/download_character_model", DownloadCharacterModelHandler)]
