import json
import tornado.web
from motion_database_server.base_handler import BaseHandler


class GetCharacterModelListHandler(BaseHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(
            self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

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


class UploadCharacterModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

    @tornado.gen.coroutine
    def post(self):
        try:
            
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
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


class DeleteCharacterModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

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

class DownloadCharacterModelHandler(BaseHandler):
    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.app = application
        self.motion_database = application.motion_database

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