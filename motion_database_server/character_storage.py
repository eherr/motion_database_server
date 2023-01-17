#!/usr/bin/env python
#
# Copyright 2019 DFKI GmbH.
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

import os

class CharacterStorage:
    def __init__(self, character_dir):
        self.character_dir = character_dir

    def store_character_model(self, name, skeleton_type, data):
        if name[-4:] == ".glb":
            name = name[:-4]
        out_dir = self.character_dir + os.sep + skeleton_type 
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        out_filename = out_dir+ os.sep + name + ".glb"
        with open(out_filename, 'wb') as f:
            f.write(data)
        return True
    
    def delete_character_model(self, name, skeleton_type):
        if name[-4:] == ".glb":
            name = name[:-4]
        filename = self.character_dir + os.sep + skeleton_type + os.sep + name + ".glb"
        if os.path.isfile(filename):
            os.remove(filename)
        return True

    def get_character_model_list(self, skeleton_type):
        path_ = self.character_dir + os.sep + skeleton_type
        file_list = []
        if os.path.isdir(path_):
            file_list = [f for f in os.listdir(path_) if f.endswith('.glb')]
        print("model data", skeleton_type, file_list)
        return file_list
    
    def get_character_model_data(self, name, skeleton_type):
        if name[-4:] == ".glb":
            name = name[:-4]
        in_filename = self.character_dir + os.sep + skeleton_type + os.sep + name + ".glb"
        data = None
        if os.path.isfile(in_filename):
            with open(in_filename, 'rb') as f:
                data = f.read()
        else:
            print(in_filename,"is not a file")
        return data
