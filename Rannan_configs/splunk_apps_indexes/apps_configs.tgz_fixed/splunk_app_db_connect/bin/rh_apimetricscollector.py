# Copyright (C) 2005-2016 Splunk Inc. All Rights Reserved.


"""
Shared Component - apimetricscollector

Rest api server stub for apimetricscollector

"""
import os.path as op
import sys
import splunk.rest.external as external

try:
    # Galaxy
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    # Ember and earlier releases
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

current_dir = op.dirname(op.abspath(__file__))
sys.path.insert(0, current_dir)
# Fixing code-clobbering issue in Splunk apps by overwriting rest.external's path variable to only this app.
external.__path__ = [current_dir]

# Finding current app.
app_path, current_app = op.split(op.dirname(current_dir))
# Ensure our libraries are always found first.
# Adding current app's lib/app_common to sys.path
sys.path.insert(1, make_splunkhome_path(['etc', 'apps', current_app, 'lib', 'app_common']))


from apimetricscollector.metricscollector import ApimetricscollectorRestHandler
