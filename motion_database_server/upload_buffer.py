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

class UploadBuffer:
    def __init__(self) -> None:
        self.buffer = dict()

    def is_complete(self, name):
        return self.buffer[name]["n_parts"] == len(self.upload_buffer[name]["parts"])

    def get_data(self, name):
        b_data= None
        for idx in range(self.buffer[name]["n_parts"]):
            if b_data is None:
                b_data =  self.buffer[name]["parts"][idx]
            else:
                b_data += self.buffer[name]["parts"][idx]
        data = b_data
        return data

    def delete_data(self, name):
        if name in self.buffer:
            del self.buffer[name]


    def update_buffer(self, name, part_idx, n_parts, base64_data_str):
        if name not in self.upload_buffer:
            state = dict()
            state["parts"] = dict()
            state["n_parts"] = n_parts
            self.buffer[name] = state
        self.buffer[name]["parts"][part_idx] = base64_data_str

