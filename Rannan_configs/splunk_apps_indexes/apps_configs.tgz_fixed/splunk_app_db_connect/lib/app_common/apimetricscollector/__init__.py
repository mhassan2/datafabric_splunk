# Copyright 2016 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

'''
REST API to collect indexed data volumes.
'''

__version__ = '1.0.0'
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../bin/splunk_sdk-1.5.0-py2.7.egg'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../bin'))

