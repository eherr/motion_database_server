import json
import bson
import bz2
import tornado.web
from motion_database_server.base_handler import BaseDBHandler
import base64
USER_ROLE_ADMIN = "admin"

class ModelDBHandler(BaseDBHandler):
    def has_access(self, data):
        m_id = data.get("model_id", None)
        if m_id is None:
            return False
        token = data.get("token", None)
        if token is None:
            return False
        owner_id = self.motion_database.get_owner_of_model(m_id)
        request_user_id = self.motion_database.get_user_id_from_token(token)
        role = self.app.motion_database.get_user_role(request_user_id)
        return request_user_id == owner_id or role == USER_ROLE_ADMIN

class GetModelList(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            collection = None
            collection = input_data.get("collection", None)
            model_format = input_data.get("format", "mm")
            skeleton = input_data.get("skeleton", "")
            models = []
            if collection is not None:
                models = self.motion_database.get_model_list_by_collection(collection, skeleton, model_format)
            models_str = json.dumps(models)
            self.write(models_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class AddModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            response_dict = dict()
            success = False
            if "collection" in input_data and "data" in input_data and self.motion_database.check_rights(input_data):
                new_id = self.motion_database.upload_model(input_data)
                response_dict["id"] =new_id
                success = True
            else:
                print("Error: did not find expected input data")
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class RemoveModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            success = False
            response_dict = dict()
            if self.has_access(input_data):
                m_id = input_data["model_id"]
                print("Error: has no access rights")
                self.motion_database.delete_model_by_id(m_id)
                success = True

            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)

            input_data = json.loads(input_str)
            data = self.motion_database.get_model_by_id(input_data["model_id"])
            if data is not None:
                self.write(data)
            else:
                self.write("")
                        
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class ReplaceModelHandler(ModelDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            response_dict = dict()
            success = False
            if self.has_access(input_data):
                success = True
                m_id = input_data["model_id"]
                self.motion_database.replace_model(m_id, input_data)
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


MODEL_DB_HANDLER_LIST = [(r"/models", GetModelList),
                            (r"/models/add", AddModelHandler),
                            (r"/models/replace", ReplaceModelHandler),
                            (r"/models/remove", RemoveModelHandler),
                            (r"/models/download", DownloadModelHandler)
                            ]