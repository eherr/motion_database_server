
import json
import tornado.web
from motion_database_server.base_handler import BaseDBHandler

class GetModelTypeList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        exp_list = self.app.motion_database.get_model_type_list()
        response = json.dumps(exp_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        model_types = self.app.motion_database.get_model_type_list()
        response = json.dumps(model_types)
        self.write(response)


class AddModelTypeHandler(BaseDBHandler):
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
               new_id = self.app.motion_database.create_model_type(input_data)
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


class EditModelTypeHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           model_type = input_data["model_type"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_model_type(model_type, input_data)
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
     
class RemoveModelTypeHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           model_type = input_data["model_type"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.remove_model_type(model_type)
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


class GetModelTypeInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            model_type = input_data["model_type"]
            info = self.app.motion_database.get_model_type_info(model_type)
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


class GetEvalScriptList(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        eval_script_list = self.app.motion_database.get_eval_script_list()
        response = json.dumps(eval_script_list)
        self.write(response)

    @tornado.gen.coroutine
    def get(self):
        eval_script_list = self.app.motion_database.get_eval_script_list()
        response = json.dumps(eval_script_list)
        self.write(response)




class AddEvalScriptHandler(BaseDBHandler):
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
               new_id = self.app.motion_database.create_eval_script(input_data)
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

class EditEvalScriptHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           print(input_str)
           input_data = json.loads(input_str)
           model_type = input_data["model_type"]
           engine = input_data["engine"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.edit_eval_script(model_type, engine, input_data)
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
     

class RemoveEvalScriptHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
           input_str = self.request.body.decode("utf-8")
           input_data = json.loads(input_str)
           model_type = input_data["model_type"]
           engine = input_data["engine"]
           token = input_data["token"]
           request_user_id = self.app.motion_database.get_user_id_from_token(token) 
           role = self.app.motion_database.get_user_role(request_user_id)
           success = False
           if role == "admin":
                self.app.motion_database.remove_eval_script(model_type, engine)
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

class GetEvalScriptInfoHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)
            input_data = json.loads(input_str)
            model_type = input_data["model_type"]
            engine = input_data["engine"]
            info = self.app.motion_database.get_eval_script_info(model_type, engine)
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


MODEL_TYPE_DB_HANDLER_LIST = [(r"/model_types", GetModelTypeList),
                            (r"/model_types/add", AddModelTypeHandler),
                            (r"/model_types/edit", EditModelTypeHandler),
                            (r"/model_types/remove", RemoveModelTypeHandler),
                            (r"/model_types/info", GetModelTypeInfoHandler),

                            (r"/eval_scripts", GetEvalScriptList),
                            (r"/eval_scripts/add", AddEvalScriptHandler),
                            (r"/eval_scripts/edit", EditEvalScriptHandler),
                            (r"/eval_scripts/remove", RemoveEvalScriptHandler),
                            (r"/eval_scripts/info", GetEvalScriptInfoHandler)
                            ]