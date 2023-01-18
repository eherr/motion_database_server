
import json
import bson
import bz2
import tornado.web
from motion_database_server.utils import get_bvh_string
from motion_database_server.base_handler import BaseDBHandler
USER_ROLE_ADMIN = "admin"

class GetModelListHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            collection = None
            if "collection" in input_data:
                collection = input_data["collection"]
            if "collection_id" in input_data:
                collection = input_data["collection_id"]
            skeleton_name = ""
            if "skeleton" in input_data:
                skeleton_name = input_data["skeleton"]
            models = []
            if collection is not None:
                models = self.motion_database.get_model_list_by_collection(collection, skeleton_name)
            models_str = json.dumps(models)
            self.write(models_str)
        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class UploadMotionModelHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            # print(input_str)
            input_data = json.loads(input_str)
            output_str = "done"
            print("upload motion primitive model")
            if "collection" in input_data and "data" in input_data and self.motion_database.check_rights(input_data):
                mm_data_str = bson.dumps(input_data["data"])
                mm_data_str = bz2.compress(mm_data_str)
                data = dict()
                data["id"] = self.motion_database.upload_motion_model(input_data["name"],
                                                        input_data["collection"], 
                                                        input_data["skeleton_name"], 
                                                        mm_data_str)
                output_str = json.dumps(data)
            else:
                print("Error: did not find expected input data")
            self.write(output_str)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()



class DeleteModelHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            m_id = input_data["model_id"]
            token = input_data["token"]
            owner_id = self.motion_database.get_owner_of_model(m_id)
            request_user_id = self.motion_database.get_user_id_from_token(token)
            role = self.app.motion_database.get_user_role(request_user_id)
            has_access = self.motion_database.check_rights(input_data)
            if request_user_id != owner_id and role != USER_ROLE_ADMIN:
                 print("Error: has no access rights")
            self.motion_database.delete_model_by_id(input_data["model_id"])
            self.write("Done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()

class UploadClusterTreeHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            # print(input_str)
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
            if not has_access:
                print("Error: has no access rights")
                self.write("Done")
                return
            print("upload cluster tree")
            if "model_id" in input_data and "cluster_tree_data" in input_data:
                cluster_tree_data_str = bson.dumps(json.loads(input_data["cluster_tree_data"]))
                cluster_tree_data_str = bz2.compress(cluster_tree_data_str)
                self.motion_database.upload_cluster_tree(input_data["model_id"],
                                                        cluster_tree_data_str)
            else:
                print("Error: did not find expected input data")
            self.write("done")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadMotionModelHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print(input_str)

            input_data = json.loads(input_str)
            data, cluster_tree_data, skeleton_name = self.motion_database.get_model_by_id(input_data["model_id"])
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


class DownloadClusterTreeHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            data, cluster_tree_data, skeleton_name = self.motion_database.get_model_by_id(input_data["model_id"])
            result_str = ""
            if cluster_tree_data is not None and cluster_tree_data != b'\x00':
                result_str = cluster_tree_data
            self.write(result_str)

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class DownloadMotionPrimitiveSampleHandler(BaseDBHandler):

    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            bvh_str = self.app.get_current_motion_primitive_sample(input_data["model_id"])
            print("bvh_str", bvh_str)
            # bvh_str = motion_record["BVHString"]
            if bvh_str is not None:
                self.write(bvh_str)
            else:
                self.write("Not found")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


class SampleToBVHHandler(BaseDBHandler):

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        if "model_id" in input_data:
            model_id = input_data["model_id"]
            motion_vector, skeleton_type = self.motion_database.get_motion_vector_from_random_sample(model_id)
            skeleton = self.motion_database.get_skeleton(skeleton_type)
            if skeleton is not None:
                bvh_str = get_bvh_string(skeleton, motion_vector.frames)
                self.write(bvh_str)
            else:
                error_msg = "Error: did not find model"+str(model_id)
                print(error_msg)
                self.write(error_msg)
        else:
            error_msg = "Error: model id not specified"
            print(error_msg)
            self.write(error_msg)


class GetSampleHandler(BaseDBHandler):
    """Handles HTTP POST Requests to a registered server url."""

    def post(self):
        input_str = self.request.body.decode("utf-8")
        input_data = json.loads(input_str)
        motion_vector, skeleton_type = self.motion_database.get_motion_vector_from_random_sample(input_data["model_id"])
        result_object = motion_vector.to_db_format()
        result_object["skeletonModel"] = skeleton_type
        self.write(bson.dumps(result_object))


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
            has_access = self.motion_database.check_rights(input_data)
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
            result_id = None
            input_str = self.request.body.decode("utf-8")
            input_data = json.loads(input_str)
            has_access = self.motion_database.check_rights(input_data)
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
           has_access = self.motion_database.check_rights(input_data)
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


class GetTimeFunctionHandler(BaseDBHandler):
    @tornado.gen.coroutine
    def post(self):
        try:
            input_str = self.request.body.decode("utf-8")
            print("get_time_function",input_str)

            input_data = json.loads(input_str)
            m_id = input_data["clip_id"]
            data, meta_data, skeleton_name = self.motion_database.get_preprocessed_data_by_id(m_id)
            if meta_data is not None and meta_data != b"x00" and meta_data != "":
                meta_data = bz2.decompress(meta_data)
                meta_data = bson.loads(meta_data)
                if "time_function" in meta_data:
                    time_function_str = json.dumps(meta_data["time_function"])
                    self.write(time_function_str)
                else:
                    self.write("")
            else:
                self.write("")

        except Exception as e:
            print("caught exception in get")
            self.write("Caught an exception: %s" % e)
            raise
        finally:
            self.finish()


MG_MODEL_HANDLER_LIST = [ (r"/get_model_list", GetModelListHandler),
                            (r"/get_graph_list", GetGraphListHandler),
                            (r"/upload_motion_model", UploadMotionModelHandler),
                            (r"/delete_model", DeleteModelHandler),
                            (r"/upload_cluster_tree", UploadClusterTreeHandler),
                            (r"/upload_graph", UploadGraphHandler),
                            (r"/replace_graph", ReplaceGraphHandler),
                            (r"/download_graph", DownloadGraphHandler),
                            (r"/remove_graph", RemoveGraphHandler),
                            (r"/get_time_function", GetTimeFunctionHandler),
                            (r"/download_motion_model", DownloadMotionModelHandler),
                            (r"/download_cluster_tree", DownloadClusterTreeHandler),
                            (r"/download_motion_primitive_sample", DownloadMotionPrimitiveSampleHandler),
                             (r"/download_sample_as_bvh", SampleToBVHHandler),
                            (r"/get_sample", GetSampleHandler)]