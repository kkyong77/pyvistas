from vistas.core.graphics.camera import Camera, ViewMatrix
from vistas.core.graphics.vector import Vector
# Todo: consider having a default viewmatrix state that does not change between scenes.


class CameraInteractor:

    SPHERE = 'sphere'
    FREELOOK = 'freelook'
    PAN = 'pan'

    camera_type = None

    def __init__(self, camera=None, interactor=None):    # , point=None, object=None): Todo: are these ever used?

        self.left_down = False
        self.right_down = False

        # camera inherits from scene or interactor
        if issubclass(type(interactor), CameraInteractor):
            self.camera = interactor.camera
        elif camera is not None:
            self.camera = camera.scene
        else:
            raise ValueError("No valid scene or interactor provided.")

        # set camera matrix position to default position, capture it
        self.camera.matrix = ViewMatrix()
        bounds = self.camera.scene.bounding_box
        center = bounds.center
        self.camera.set_position(Vector(center.x, center.y, bounds.max_z + bounds.diameter))
        self.camera.set_up_vector(Vector(0, 1, 0))
        self.camera.set_point_of_interest(center)
        self.default_matrix = self.camera.matrix

        self._distance = 0
        self._forward = 0
        self._strafe = 0
        self._shift_x = 0
        self._shift_y = 0
        self._angle_x = 0
        self._angle_y = 0
        self.friction_coeff = bounds.diameter / 500

        self.reset_position()

    def key_down(self, key):
        pass  # implemented by subclasses

    def key_up(self, key):
        pass  # implemented by subclasses

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        pass  # implemented by subclasses

    def mouse_wheel(self, value, shift, alt, ctrl):
        pass  # implemented by subclasses

    def refresh_position(self):
        pass  # implemented by subclasses

    def reset_position(self):
        pass  # implemented by subclasses


class SphereInteractor(CameraInteractor):

    def __init__(self, camera=None, interactor=None):
        self.camera_type = CameraInteractor.SPHERE
        super().__init__(*[camera, interactor])

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        friction = 100
        center_dist = self.camera.distance_to_point(self.camera.scene.bounding_box.center)
        if shift is True:
            self._distance = self._distance + dy / friction * center_dist
        elif ctrl is True:
            self._shift_x = self._shift_x + dx * center_dist / friction
            self._shift_y = self._shift_y + dy * center_dist / friction
        elif alt is True:
            z_near = self.camera.z_near_plane
            if z_near + dy / friction > 0.0:
                self.camera.z_near_plane = self.camera.z_near_plane + dy / friction
        else:
            self._angle_x = self._angle_x + dx / friction * 10
            self._angle_y = self._angle_y + dy / friction * 10
        self.refresh_position()

    def mouse_wheel(self, value, shift, alt, ctrl):
        wheel_delta = 120 # Todo: Take windows/linux delta value?
        bbox = self.camera.scene.bounding_box
        diameter = bbox.diameter
        orig_dist = bbox.max_z + diameter
        curr_dist = self.camera.distance_to_point(bbox.center)
        dist_ratio = 1 - (orig_dist - curr_dist) / orig_dist
        scene_size_mult = 0.8 * diameter / 2
        zoom_amt = value / wheel_delta * scene_size_mult * dist_ratio
        if value < 0 and zoom_amt <= 0:
            zoom_amt = zoom_amt - 1
        if shift is True:
            zoom_amt = zoom_amt * 2
        elif ctrl is True:
            zoom_amt = zoom_amt * 0.25

        self._distance = self._distance + zoom_amt
        self.refresh_position()

    def refresh_position(self):
        center = self.camera.scene.bounding_box.center
        dummy_cam = Camera()
        dummy_cam.matrix = self.default_matrix
        z_shift = dummy_cam.distance_to_point(center)
        self.camera.matrix = ViewMatrix.translate(self._shift_x, self._shift_y, self._distance) * \
                             ViewMatrix.translate(0, 0, -z_shift) * \
                             ViewMatrix.rotate_x(self._angle_y) * \
                             ViewMatrix.rotate_y(self._angle_x) * \
                             ViewMatrix.translate(0, 0, z_shift) * self.default_matrix
        # Todo: UIPostRedisplay?

    def reset_position(self):
        self.camera.matrix = self.default_matrix
        self._distance = 0
        self._forward = 0
        self._strafe = 0
        self._shift_x = 0
        self._shift_y = 0
        self._angle_x = 0
        self._angle_y = 0
        self.refresh_position()


class FreelookInteractor(CameraInteractor):

    def __init__(self, camera=None, interactor=None):
        self.camera_type = CameraInteractor.FREELOOK
        super().__init__(*[camera, interactor])

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        friction = 5.0
        self._forward = 0.0
        self._strafe = 0.0
        self._angle_x = dy / friction
        self._angle_y = dx / friction
        self.refresh_position()

    def key_down(self, key):
        self._forward = 0.0
        self._strafe = 0.0
        if key == "W":
            self._forward = self._forward - self.friction_coeff
        elif key == "S":
            self._forward = self._forward + self.friction_coeff
        elif key == "A":
            self._strafe = self._strafe - self.friction_coeff
        elif key == "D":
            self._strafe = self._strafe + self.friction_coeff
        self.refresh_position()

    def refresh_position(self):
        self.camera.move_relative(Vector(self._strafe, 0.0, self._forward))
        pos = self.camera.get_position()
        self.camera.matrix = ViewMatrix.rotate_x(self._angle_x) * ViewMatrix.rotate_y(self._angle_y) \
                             * self.default_matrix
        self.camera.set_position(pos)
        # Todo: UIPostRedisplay?


class PanInteractor(SphereInteractor):

    def __init__(self, camera=None, interactor=None):
        super().__init__(*[camera, interactor])
        self.camera_type = CameraInteractor.PAN

    def mouse_motion(self, dx, dy, shift, alt, ctrl):
        friction = 200
        dist = self.camera.distance_to_point(self.camera.scene.bounding_box.center) / friction
        self._shift_x = self._shift_x + dx * dist
        self._shift_y = self._shift_y + dy * dist
        self.refresh_position()
