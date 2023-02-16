
import json
import tornado.web
from motion_database_server.base_handler import BaseDBHandler

class FileDBHandler(BaseDBHandler):
    def has_access(self, data):
        f_id = data.get("file_id", None)
        if m_id is None:
            return False
        token = data.get("token", None)
        if token is None:
            return False
        owner_id = self.motion_database.get_owner_of_file(f_id)
        request_user_id = self.motion_database.get_user_id_from_token(token)
        role = self.app.motion_database.get_user_role(request_user_id)
        return request_user_id == owner_id or role == USER_ROLE_ADMIN

class GetFileList(FileDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            collection = input_data.get("collection", None)
            data_type = input_data.get("data_type", None)
            skeleton = input_data.get("skeleton", None)
            files = []
            if collection is not None:
                files = self.motion_database.get_file_list_by_collection(collection, skeleton, data_type)
                print(files)
            files_str = json.dumps(files)
            self.write(files_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class AddFileHandler(FileDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            response_dict = dict()
            success = False
            if "collection" in input_data and "data" in input_data and self.motion_database.check_rights(input_data):
                input_data["data"] = base64.b64decode(input_data["data"])
                new_id = self.motion_database.upload_file(input_data)
                response_dict["id"] = new_id
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


class RemoveFileHandler(FileDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            success = False
            response_dict = dict()
            if self.has_access(input_data):
                m_id = input_data["file_id"]
                print("Error: has no access rights")
                self.motion_database.delete_file_by_id(m_id)
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


class DownloadFileHandler(FileDBHandler):

    def set_default_headers(self):
        super(DownloadFileHandler, self).set_default_headers()
        self.set_header('Content-Type', 'application/octet-stream')

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)

            input_data = json.loads(input_str)
            data = self.motion_database.get_file_by_id(input_data["file_id"])
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


class ReplaceFileHandler(FileDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            response_dict = dict()
            success = False
            if self.has_access(input_data):
                success = True
                m_id = input_data["file_id"]
                if "data" in input_data:
                    input_data["data"] = base64.b64decode(input_data["data"])
                if "metaData" in input_data:
                    input_data["metaData"] = base64.b64decode(input_data["metaData"])
                self.motion_database.replace_file(m_id, input_data)
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)

        except Exception as e:
            print("caught exception in post")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class GetDataTypeList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        exp_list = self.app.motion_database.get_data_type_list()
        response = json.dumps(exp_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        data_types = self.app.motion_database.get_data_type_list()
        response = json.dumps(data_types)
        self.write(response)


class AddDataTypeHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               new_id = self.app.motion_database.create_data_type(input_data)
               response_dict["id"] = new_id
               response_dict["success"] = True
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class EditDataTypeHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           data_type = input_data["data_type"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_data_type(data_type, input_data)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()
     
class RemoveDataTypeHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           data_type = input_data["data_type"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.remove_data_type(data_type)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class GetDataTypeInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            data_type = input_data["data_type"]
            info = self.app.motion_database.get_data_type_info(data_type)
            response_dict = dict()
            success = False
            if info is not None:
                response_dict.update(info)
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




FILE_DB_HANDLER_LIST = [(r"/files", GetFileList),
                            (r"/files/add", AddFileHandler),
                            (r"/files/replace", ReplaceFileHandler),
                            (r"/files/remove", RemoveFileHandler),
                            (r"/files/download", DownloadFileHandler)
                            ]
                        
FILE_DB_HANDLER_LIST += [(r"/data_types", GetDataTypeList),
                            (r"/data_types/add", AddDataTypeHandler),
                            (r"/data_types/edit", EditDataTypeHandler),
                            (r"/data_types/remove", RemoveDataTypeHandler),
                            (r"/data_types/info", GetDataTypeInfoHandler)]

class GetDataLoaderList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        data_loader_list = self.app.motion_database.get_data_loader_list()
        response = json.dumps(data_loader_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        data_loader_list = self.app.motion_database.get_data_loader_list()
        response = json.dumps(data_loader_list)
        self.write(response)




class AddDataLoaderHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               new_id = self.app.motion_database.create_data_loader(input_data)
               response_dict["id"] = new_id
               response_dict["success"] = True
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class EditDataLoaderHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           data_type = input_data["data_type"]
           engine = input_data["engine"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_data_loader(data_type, engine, input_data)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()
     

class RemoveDataLoaderHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           data_type = input_data["data_type"]
           engine = input_data["engine"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.remove_data_loader(data_type, engine)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetDataLoaderInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            data_type = input_data["data_type"]
            engine = input_data["engine"]
            info = self.app.motion_database.get_data_loader_info(data_type, engine)
            response_dict = dict()
            success = False
            if info is not None:
                response_dict.update(info)
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

FILE_DB_HANDLER_LIST += [
                            (r"/data_loaders", GetDataLoaderList),
                            (r"/data_loaders/add", AddDataLoaderHandler),
                            (r"/data_loaders/edit", EditDataLoaderHandler),
                            (r"/data_loaders/remove", RemoveDataLoaderHandler),
                            (r"/data_loaders/info", GetDataLoaderInfoHandler)
                            ]

class GetDataTransformList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        data_loader_list = self.app.motion_database.get_data_transform_list()
        response = json.dumps(data_loader_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        data_loader_list = self.app.motion_database.get_data_transform_list()
        response = json.dumps(data_loader_list)
        self.write(response)




class AddDataTransformHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               new_id = self.app.motion_database.create_data_transform(input_data)
               response_dict["id"] = new_id
               response_dict["success"] = True
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class EditDataTransformHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           dt_id = input_data["data_transform_id"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_data_transform(dt_id, input_data)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()
     

class RemoveDataTransformHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print("delete",input_str)
           input_data = json.loads(input_str)
           dt_id = input_data["data_transform_id"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           print("delete",input_data)
           if role == "admin":
                print("delete",input_data)
                self.app.motion_database.remove_data_transform(dt_id)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetDataTransformInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            dt_id = input_data["data_transform_id"]
            info = self.app.motion_database.get_data_transform_info(dt_id)
            response_dict = dict()
            success = False
            if info is not None:
                response_dict.update(info)
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

FILE_DB_HANDLER_LIST += [
                            (r"/data_transforms", GetDataTransformList),
                            (r"/data_transforms/add", AddDataTransformHandler),
                            (r"/data_transforms/edit", EditDataTransformHandler),
                            (r"/data_transforms/remove", RemoveDataTransformHandler),
                            (r"/data_transforms/info", GetDataTransformInfoHandler)
                            ]
class GetDataTransformInputList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self): 
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            dt_id = input_data["data_transform_id"]
            data_loader_list = self.app.motion_database.get_data_transform_input_list(dt_id)
            response = json.dumps(data_loader_list)
            self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class AddDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               new_id = self.app.motion_database.create_data_transform_input(input_data)
               response_dict["id"] = new_id
               response_dict["success"] = True
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class EditDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           dti_id = input_data["data_transform_input_id"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_data_transform_input(dti_id, input_data)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()
     

class RemoveDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           dti_id = input_data["data_transform_input_id"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.remove_data_transform_input(dti_id)
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class RemoveAllDataTransformInputHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           dt_id = input_data["data_transform_id"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                input_list = self.app.motion_database.get_data_transform_input_list(dt_id)
                for di in input_list:
                    self.app.motion_database.remove_data_transform_input(di[0])
                success = True
           response_dict = dict()
           response_dict["success"] = success
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class GetDataTransformInputInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            dti_id = input_data["data_transform_input_id"]
            info = self.app.motion_database.get_data_transform_input_info(dti_id)
            response_dict = dict()
            success = False
            if info is not None:
                response_dict.update(info)
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


FILE_DB_HANDLER_LIST += [
                            (r"/data_transforms/inputs", GetDataTransformInputList),
                            (r"/data_transforms/inputs/add", AddDataTransformInputHandler),
                            (r"/data_transforms/inputs/edit", EditDataTransformInputHandler),
                            (r"/data_transforms/inputs/remove", RemoveDataTransformInputHandler),
                            (r"/data_transforms/inputs/removeall", RemoveAllDataTransformInputHandler),
                            (r"/data_transforms/inputs/info", GetDataTransformInputInfoHandler)
                            ]