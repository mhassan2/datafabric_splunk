# SPL-115359, add APP_HOME/bin into sys.path for scripted REST endpoint
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))