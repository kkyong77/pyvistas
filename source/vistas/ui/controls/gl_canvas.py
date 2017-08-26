from PIL import Image

import os
import wx
import wx.glcanvas

from vistas.core.graphics.overlay import Button, Overlay
from vistas.core.observers.camera import CameraObservable
from vistas.core.paths import get_resources_directory
from vistas.core.utils import get_platform
from vistas.ui.controls.gl_camera import GLCameraControls
from vistas.ui.events import CameraSyncEvent


class GLCanvas(wx.glcanvas.GLCanvas):
    """
    A panel for rendering an OpenGL context. An OpenGL context is created when the first instance of this class is
    created, and is shared between all other instances.
    """

    initialized = False
    shared_gl_context = None

    def __init__(self, parent, id, camera, attrib_list=None, can_sync=False):
        super().__init__(parent, id, attribList=attrib_list)

        self.camera = camera
        self.camera_controls = GLCameraControls(self, camera)

        self.can_sync = can_sync    # Indicate whether this canvas can sync with global interactor

        self._x = self._y = -1

        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        if get_platform() == 'windows':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

        self.overlay = Overlay(self)

    def OnDestroy(self, event):
        CameraObservable.get().remove_observer(self.camera)
        self.camera_controls.Destroy()

    @property
    def camera_interactor(self):
        return self.camera_controls.camera_interactor

    @camera_interactor.setter
    def camera_interactor(self, interactor):
        self.camera_controls.camera_interactor = interactor

    def Sync(self):
        if self.can_sync and CameraObservable.get().is_sync:
            event = CameraSyncEvent(interactor=self.camera_interactor)
            event.SetEventObject(self)
            wx.PostEvent(self.GetParent().GetParent(), event)

    def OnPaint(self, event):
        if not GLCanvas.initialized:
            GLCanvas.initialized = True
            GLCanvas.shared_gl_context = wx.glcanvas.GLContext(self)
            self.SetCurrent(GLCanvas.shared_gl_context)
            self.SwapBuffers()

        self.SetCurrent(GLCanvas.shared_gl_context)
        self.camera.render(*self.GetSize().Get(), self.overlay)
        self.SwapBuffers()

    def OnEraseBackground(self, event: wx.EraseEvent):
        pass  # Ignore this event to prevent flickering on Windows

    def OnMotion(self, event: wx.MouseEvent):
        if event.LeftIsDown():
            x = event.GetX()
            y = event.GetY()
            if self._x > -1 and self._y > -1:
                self.camera_interactor.mouse_motion(x - self._x, y - self._y, event.ShiftDown(), event.AltDown(),
                                                    event.ControlDown())
            self._x = x
            self._y = y

            self.Sync()
            self.Refresh()
        else:
            self._x = self._y = -1
        event.Skip()

    def OnMouseWheel(self, event: wx.MouseEvent):
        self.camera_interactor.mouse_wheel(event.GetWheelRotation(), event.GetWheelDelta(), event.ShiftDown(),
                                           event.AltDown(), event.ControlDown())
        self._x = self._y = -1
        self.Sync()
        self.Refresh()

    def OnKey(self, event: wx.KeyEvent):
        keycode = event.GetUnicodeKey()
        if keycode != wx.WXK_NONE:
            self.camera_interactor.key_down("{:c}".format(keycode))
            self.Sync()
            self.Refresh()

    def OnPostRedisplay(self, event):
        self.Refresh()
