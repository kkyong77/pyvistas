import os

import wx

from vistas.core.utils import get_platform


def get_builtin_plugins_directory():
    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), '..', 'plugins')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'plugins')


def get_resources_directory():
    if get_platform() == 'windows':
        return os.path.join(os.getcwd(), '..', 'resources')
    else:
        return os.path.join(os.path.dirname(wx.StandardPaths.Get().ExecutablePath), '..', 'resources')


def get_resource_bitmap(name):
    return wx.Image(os.path.join(get_resources_directory(), 'images', name)).ConvertToBitmap()


def get_icon(name):
	return wx.Icon(wx.IconLocation(os.path.join(get_resources_directory(), 'images', name)))
