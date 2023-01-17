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
from hashlib import sha512

MAX_FILENAME_LENGTH = 40

class FileStorage:
    def __init__(self, data_dir) -> None:
        self.data_dir = data_dir

    def save_hashed_file(self, directory, data_type, data):
        if data == "":
            return ""
        hash_filename = self.generate_filename(data) + "." + data_type
        self.save_data_file(directory, hash_filename, data)
        return hash_filename

    def generate_filename(self, data):
        #salt = file_id.to_bytes(4, byteorder='big')
        hash = sha512(data)
        hash_filename = hash.hexdigest()[:MAX_FILENAME_LENGTH]
        return hash_filename

    def save_data_file(directory, name, data):
        filename = directory+os.sep+name
        with open(filename, "wb") as file:
            file.write(data)

    def load_data_file(self, table_name, name):
        filename = self.data_dir + os.sep + table_name + os.sep + name
        
        if not os.path.isfile(filename):
            return None
        with open(filename, "rb") as file:
            data = file.read()
        return data

    def delete_data_file(self, table_name, name):
        filename = self.data_dir + os.sep + table_name + os.sep + name
        if not os.path.isfile(filename):
            return
        os.remove(filename)