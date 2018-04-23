#object oriented
import gphoto2 as gp
import time

context = gp.Context()
camera = gp.Camera()
camera.init(context)
text = camera.get_summary(context)
print('Summary')
print('=======')
print(str(text))
#camera.exit(context)

#with error checking


config=camera.get_config()
preview=gp.check_result(gp.gp_widget_get_child_by_name(config, 'viewfinder'))
gp.check_result(gp.gp_widget_set_value(preview, 1))
gp.gp_widget_get_choice(preview, 1)
gp.gp_widget_


time.sleep(0.5)

for i in range(0, 100):
    param = 'manualfocusdrive'
    choice = 6
    widget = gp.check_result(gp.gp_widget_get_child_by_name(config, param))
    value = gp.check_result(gp.gp_widget_get_choice(widget, choice))
    gp.gp_widget_set_value(widget, value)
    gp.gp_camera_set_config(camera, config, context)
    choice = 3
    widget = gp.check_result(gp.gp_widget_get_child_by_name(config, param))
    value = gp.check_result(gp.gp_widget_get_choice(widget, choice))
    gp.gp_widget_set_value(widget, value)
    gp.gp_camera_set_config(camera, config, context)
