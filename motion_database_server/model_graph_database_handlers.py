
import json
import bson
import bz2
import tornado.web
from motion_database_server.base_handler import BaseDBHandler
USER_ROLE_ADMIN = "admin"


class GetGraphListHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            skeleton = None
            if "skeleton" in input_data:
                skeleton = input_data["skeleton"]
            result = self.motion_database.get_graph_list(skeleton)
            if result is not None:
                result_str = json.dumps(result)
                self.write(result_str)
            else:
                self.write("Not found")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class UploadGraphHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            result_id = None
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.project_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            if "name" in input_data and "skeleton" in input_data and "data" in input_data:
                name = input_data["name"]
                skeleton = input_data["skeleton"]
                data = bson.dumps(input_data["data"])
                data = bz2.compress(data)
                result_id = self.motion_database.add_new_graph(name, skeleton, data)
            if result_id is not None:
                result_data = {"id": result_id}
                result_str = json.dumps(result_data)
                self.write(result_str)
            else:
                self.write("Error")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class ReplaceGraphHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.project_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            if "id" in input_data:
                graph_id = input_data["id"]
                data = bz2.compress(data)
                self.motion_database.replace_graph(graph_id, input_data)
            self.write("Done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadGraphHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            result = None
            input_data = json.loads(input_str)
            if "id" in input_data:
                graph_id = input_data["id"]
                result = self.motion_database.get_graph_by_id(graph_id)
            if result is not None:
                result = json.dumps(result)
                self.write(result)
            else:
                self.write("Not found")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class RemoveGraphHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            
           input_str = self.request.body.decode("utf-8")
           result = None
           input_data = json.loads(input_str)
           has_access = self.project_database.check_rights(input_data)
           if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
           if "id" in input_data:
               graph_id = input_data["id"]
               result = self.motion_database.remove_graph_by_id(graph_id)
           if result is not None:
               result_str = json.dumps(result)
               self.write(result_str)
           else:
               self.write("Done")
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



MODEL_GRAPH_HANDLER_LIST = [ (r"/get_graph_list", GetGraphListHandler),
                        (r"/upload_graph", UploadGraphHandler),
                        (r"/replace_graph", ReplaceGraphHandler),
                        (r"/download_graph", DownloadGraphHandler),
                        (r"/remove_graph", RemoveGraphHandler),]