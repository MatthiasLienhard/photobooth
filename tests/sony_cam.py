import pysony
import cStringIO
import flask
api=pysony.SonyAPI()
search = pysony.ControlPoint()
cameras = search.discover(1)

# python3 ~/projects/downloads/sony_camera_api/src/example/dump_camera_capabilities.py