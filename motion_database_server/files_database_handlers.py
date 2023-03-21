
import json
import base64
import tornado.web
from motion_database_server.base_handler import BaseDBHandler

class FileDBHandler(BaseDBHandler):
    def has_access(self, data):
        f_id = data.get("file_id", None)
        if f_id is None:
            return False
        token = data.get("token", None)
        if token is None:
            return False
        owner_id = self.motion_database.get_owner_of_file(f_id)
        request_user_id = self.project_database.get_user_id_from_token(token)
        role = self.project_database.get_user_role(request_user_id)
        return request_user_id == owner_id or role == "admin"

class GetFileList(FileDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            collection = input_data.get("collection", None)
            data_type = input_data.get("data_type", None)
            skeleton = input_data.get("skeleton", None)
            tags = input_data.get("tags", None)
            files = self.motion_database.get_file_list(collection, skeleton, data_type, tags=tags)
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
            if "collection" in input_data and "data" in input_data and self.project_database.check_rights(input_data):
                input_data["data"] = base64.b64decode(input_data["data"])
                new_id = self.motion_database.create_file(input_data)
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
                self.motion_database.delete_file_by_id(m_id)
                success = True
            else:
                print("Error: has no access rights")
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
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        tags = input_data.get("tags", None)
        exp_list = self.app.motion_database.get_data_type_list(tags)
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
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           
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
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_data_type(data_type, input_data)
                if "name" in input_data:
                    self.data_transform_service.rename_data_type(data_type, input_data["name"])
                
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
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
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



class DataTypeExportHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def get(self):
        try:
            data = self.motion_database.data_types_to_dict()
            response_dict = dict()
            success = False
            if data is not None:
                response_dict.update(data)
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


class DataTypeImportHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            token = input_data["token"]
            request_user_id = self.project_database.get_user_id_from_token(token)
            role = self.project_database.get_user_role(request_user_id)
            success = False
            response_dict = dict()
            if role == "admin":
                self.motion_database.data_types_from_dict(input_data)
                success = True
            response_dict["success"] = success
            response = json.dumps(response_dict)
            self.write(response)
        except Exception as e:
            print("caught exception in post")
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
                            (r"/data_types/info", GetDataTypeInfoHandler),
                             (r"/data_types/import", DataTypeImportHandler),
                             (r"/data_types/export", DataTypeExportHandler)]

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
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           
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
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
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
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
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



class GetTagList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        tag_list = self.app.motion_database.get_tag_list()
        response = json.dumps(tag_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        tag_list = self.app.motion_database.get_tag_list()
        response = json.dumps(tag_list)
        self.write(response)


class AddTagHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               tag = input_data["tag"]
               new_id = self.app.motion_database.create_tag(tag)
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


class RenameTagHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               old_tag = input_data["old_tag"]
               new_tag = input_data["new_tag"]
               self.app.motion_database.rename_tag(old_tag, new_tag)
               response_dict["success"] = True
           response = json.dumps(response_dict)
           self.write(response)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class RemoveTagHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print("delete",input_str)
           input_data = json.loads(input_str)
           tag = input_data["tag"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           print("delete",input_data)
           if role == "admin":
                print("delete",input_data)
                self.app.motion_database.remove_tag(tag)
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


FILE_DB_HANDLER_LIST += [
                            (r"/tags", GetTagList),
                            (r"/tags/add", AddTagHandler),
                            (r"/tags/rename", RenameTagHandler),
                            (r"/tags/remove", RemoveTagHandler),
                            ]

class GetDataTypeTagList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        data_type = input_data["data_type"]
        tag_list = self.app.motion_database.get_data_type_tag_list(data_type)
        response = json.dumps(tag_list)
        self.write(response)




class AddDataTypeTagHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           response_dict = dict()
           response_dict["success"] = False
           if role == "admin":
               tag = input_data["tag"]
               data_type = input_data["data_type"]
               print("add", input_data)
               new_id = self.app.motion_database.add_data_type_tag(data_type, tag)
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

class RemoveDataTypeTagHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print("delete",input_str)
           input_data = json.loads(input_str)
           tag = input_data["tag"]
           data_type = input_data["data_type"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           print("delete",input_data)
           if role == "admin":
                print("delete",input_data)
                self.app.motion_database.remove_data_type_tag(data_type, tag)
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


class RemoveAllDataTypeTagsHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print("delete",input_str)
           input_data = json.loads(input_str)
           data_type = input_data["data_type"]
           token = input_data["token"]
           request_user_id = self.project_database.get_user_id_from_token(token) 
           role = self.project_database.get_user_role(request_user_id)
           success = False
           print("delete",input_data)
           if role == "admin":
                print("delete",input_data)
                self.app.motion_database.remove_data_type_tag(data_type)
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
FILE_DB_HANDLER_LIST += [
                            (r"/data_types/tags", GetDataTypeTagList),
                            (r"/data_types/tags/add", AddDataTypeTagHandler),
                            (r"/data_types/tags/remove", RemoveDataTypeTagHandler),
                            (r"/data_types/tags/removeall", RemoveAllDataTypeTagsHandler),
                            ]