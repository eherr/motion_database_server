
import bson
import bz2
import numpy as np
from morphablegraphs.motion_model.motion_primitive_wrapper import MotionPrimitiveModelWrapper
from morphablegraphs.utilities import convert_to_mgrd_skeleton
from motion_database_server.utils import extract_compressed_bson
from anim_utils.animation_data.motion_vector import MotionVector

class MGModelDatabase: 
    def __init__(self) -> None:
        self._mp_buffer = dict()
        self._mp_skeleton_type = dict()

    def upload_motion_model(self, name, collection, skeleton, model_data, meta_data=None, model_format="mpm"):
        record_data = dict()
        record_data["name"] = name
        record_data["collection"] = collection
        record_data["skeleton"] = skeleton
        record_data["data"] = model_data
        record_data["dataType"] = model_format
        if meta_data is not None:
            record_data["metaData"] = meta_data
        return self.tables[self.files_table].create_record(record_data)
        
    def upload_cluster_tree(self, model_id, cluster_tree_data):
        record_data = dict()
        record_data["metaData"] = cluster_tree_data
        self.tables[self.files_table].update_record(model_id, record_data)


    def get_motion_primitive_model_by_id(self, m_id):
        r = self.tables[self.files_table].get_record_by_id(m_id, ["data", "metaData", "skeleton"])
        skeleton_name = ""
        data = None
        if r is not None:
            data = r[0]
            cluster_tree_data = r[1]
            skeleton_name = r[2]
        else:
            print("Error in get model data",m_id)
        return data, cluster_tree_data, skeleton_name

    def get_motion_primitive_sample(self, model_id):
        mv = None
        if model_id not in self._mp_buffer:
            data, cluster_tree_data, skeleton_name = self.get_motion_primitive_model_by_id(model_id)
            data = extract_compressed_bson(data)
            self._mp_buffer[model_id] = MotionPrimitiveModelWrapper()
            mgrd_skeleton = convert_to_mgrd_skeleton(self.skeletons[skeleton_name])
            self._mp_buffer[model_id]._initialize_from_json(mgrd_skeleton, data)
            self._mp_skeleton_type[model_id] = skeleton_name
        if self._mp_buffer[model_id] is not None:
            skeleton_name = self._mp_skeleton_type[model_id]
            mv = self._mp_buffer[model_id].sample(False).get_motion_vector()
            # mv = self._mp_buffer[action_name].skeleton.add_fixed_joint_parameters_to_motion(mv)
            animated_joints = self._mp_buffer[model_id].get_animated_joints()
            new_quat_frames = np.zeros((len(mv), self.skeletons[skeleton_name].reference_frame_length))
            for idx, reduced_frame in enumerate(mv):
                new_quat_frames[idx] = self.skeletons[skeleton_name].add_fixed_joint_parameters_to_other_frame(reduced_frame,
                                                                                            animated_joints)
            mv = new_quat_frames
        return mv

    def get_motion_vector_from_random_sample(self, model_id):
        frames = self.get_motion_primitive_sample(model_id)
        motion_vector = MotionVector()
        motion_vector.frames = frames
        motion_vector.n_frames = len(frames)
        skeleton_type = self._mp_skeleton_type[model_id]
        motion_vector.skeleton = self.skeletons[skeleton_type]
        return motion_vector, skeleton_type
