import os
from typing import List, Dict, Optional, Union

import wx
from PIL import Image
from pyrr import Vector3
from shapely.geometry import LinearRing, Point

from vistas.core.plugins.data import DataPlugin
from vistas.core.plugins.interface import Plugin
from vistas.core.threading import Thread
from vistas.ui.utils import get_main_window

RenderEvent, EVT_VISUALIZATION_RENDERED = wx.lib.newevent.NewEvent()
VisualizationUpdateEvent, EVT_VISUALIZATION_UPDATED = wx.lib.newevent.NewEvent()


class VisualizationPlugin(Plugin):
    @property
    def can_visualize(self):
        """ Returns True if the visualization has the necessary data to be shown """

        raise NotImplemented

    @property
    def visualization_name(self):
        raise NotImplemented

    @property
    def data_roles(self):
        raise NotImplemented

    def role_supports_multiple_inputs(self, role):
        """ Returns whether the role can have multiple sub-roles """
        return False

    def role_size(self, role):
        """ Get the number of inputs for a specific role """
        return 1

    def set_data(self, data: Optional[DataPlugin], role):
        """ Set data in a specific role for the visualization """

        raise NotImplemented

    def get_data(self, role) -> DataPlugin:
        """ Get the data associated with a specific role """

        raise NotImplemented

    def get_multiple_data(self, role) -> list:
        """ Get a list of data plugins associated with a specific role """
        return []

    def remove_subdata(self, role, subrole):
        """ Removes a data plugin from a list data plugins associated with a specific role """

        raise NotImplemented

    def set_filter(self, min_value, max_value):
        """ Set the filter min/max for the visualization """

        pass

    def clear_filter(self):
        """ Clear any filter for this visualization """

        pass

    @property
    def is_filterable(self):
        """ Can the visualization be filtered? """

        return False

    @property
    def filter_histogram(self):
        """ A histogram representing data in the visualization which can be filtered """

        return None

    @property
    def is_filtered(self):
        return False

    @property
    def filter_min(self):
        return 0

    @property
    def filter_max(self):
        return 0

    def has_legend(self):
        """ Does the visualization have a legend? """

        return False

    def get_legend(self, width, height):
        """ A color legend for the visualization """

        return None


class VisualizationPlugin2D(VisualizationPlugin):
    class RenderThread(Thread):
        def __init__(self, plugin, width, height, handler=None):
            super().__init__()

            self.plugin = plugin
            self.width = width
            self.height = height
            self.handler = handler

        def run(self):
            event = RenderEvent(image=self.plugin.render(self.width, self.height))
            handler = self.handler if self.handler is not None else get_main_window()

            self.sync_with_main(self.post_render)

            wx.PostEvent(handler, event)

        def post_render(self):
            self.plugin.post_render()

    def visualize(self, width, height, back_thread=True, handler=None):
        """
        Actualize the visualization. Returns the visualization if `back_thread` is False, otherwise generates an event
        when the visualization is ready.
        """

        if not back_thread:
            im = self.render(width, height)
            self.post_render()
            return im


        self.RenderThread(self, width, height, handler).start()

    def render(self, width, height) -> Image:
        """ Implemented by plugins to render the visualization """

        raise NotImplemented

    def post_render(self):
        """
        Called after `render` completes to perform cleanup operations. This is guaranteed to run in the main thread.
        """

        pass


class VisualizationPlugin3D(VisualizationPlugin):
    @property
    def scene(self):
        raise NotImplemented

    @scene.setter
    def scene(self, scene):
        """ Set the scene the visualization exists in. The visualization won't appear until a scene has been set. """

        raise NotImplemented

    def get_shader_path(self, name):
        """ Returns an absolute path to a plugin shader by file name """

        return os.path.join(self.plugin_dir, 'shaders', name)

    def refresh(self):
        """
        Signals the visualization to refresh itself if needed. E.g., after changing the configuration or setting new
        data.
        """

        pass

    def get_identify_detail(self, point: Vector3) -> Optional[Dict]:
        """ Returns a dictionary of data specific to the point in question. """

        pass

    def get_zonal_stats_from_point(self, point: Vector3) -> List[Optional[Dict]]:
        """ Returns the zonal statistics at a point from predefined zones. """

        pass

    def get_zonal_stats_from_feature(self, feature: LinearRing) -> List[Optional[Dict]]:
        """ Returns the zonal statistics from a defined feature. """

        pass

    def update_zonal_boundary(self, feature: Union[LinearRing, Point]):
        """ Signals the visualization to update it's representation of a zonal/area boundary. """

        pass

    @property
    def geocoder_info(self):
        """ Returns geolocated items within a given scene. """

        return None
