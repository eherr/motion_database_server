import os
import json
import bz2
import bson
import numpy as np
from anim_utils.animation_data.bvh import BVHReader, BVHWriter

def save_json_file(data, file_path, indent=4):
    with open(file_path, "w") as out_file:
        return json.dump(data, out_file, indent=indent)


def load_json_file(file_path):
    if os.path.isfile(file_path):
        with open(file_path, "r") as in_file:
            return json.load(in_file)

def get_bvh_from_str(bvh_str):
    bvh_reader = BVHReader("")
    lines = bvh_str.split('\\n')
    lines = [l for l in lines if len(l) > 0]
    bvh_reader.process_lines(lines)
    return bvh_reader

def get_bvh_string(skeleton, frames):
    print("generate bvh string", len(skeleton.animated_joints))
    frames = np.array(frames)
    frames = skeleton.add_fixed_joint_parameters_to_motion(frames)
    frame_time = skeleton.frame_time
    bvh_writer = BVHWriter(None, skeleton, frames, frame_time, True)
    return bvh_writer.generate_bvh_string()


def extract_compressed_bson(data):
    try:
        data = bson.loads(bz2.decompress(data))
    except:
        data = bson.loads(data)
        print("Warning: data was not compressed")
        pass
    return data
