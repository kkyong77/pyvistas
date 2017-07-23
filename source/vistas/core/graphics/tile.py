import asyncio
import os
import sys

import mercantile
import numpy
from OpenGL.GL import *
from pyproj import Proj
from pyrr import Vector3, Matrix44
from pyrr.vector3 import generate_vertex_normals

from vistas.core.gis.elevation import ElevationService
from vistas.core.graphics.bounds import BoundingBox
from vistas.core.graphics.mesh import Mesh
from vistas.core.graphics.renderable import Renderable
from vistas.core.graphics.shader import ShaderProgram
from vistas.core.paths import get_resources_directory
from vistas.core.task import Task
from vistas.core.threading import Thread
from vistas.ui.utils import post_redisplay


class TileShaderProgram(ShaderProgram):
    """
    A simple shader program that is applied across all tiles. Subclasses of this should be constructed to implement
    specific shader effects.
    Usage: TileShaderProgram.get()
    """

    _tile_shader = None

    @classmethod
    def get(cls):
        if cls._tile_shader is None:
            cls._tile_shader = TileShaderProgram()
        return cls._tile_shader

    def __init__(self):
        super().__init__()
        self.current_tile = None
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'tile_vert.glsl'), GL_VERTEX_SHADER)
        self.attach_shader(os.path.join(get_resources_directory(), 'shaders', 'tile_frag.glsl'), GL_FRAGMENT_SHADER)
        self.link_program()

    def pre_render(self, camera):
        if self.current_tile is not None:
            super().pre_render(camera)
            glBindVertexArray(self.current_tile.vertex_array_object)

    def post_render(self, camera):
        if self.current_tile is not None:
            glBindVertexArray(0)
            super().post_render(camera)


class TileMesh(Mesh):
    """ Base tile mesh, contains all VAO/VBO objects """

    def __init__(self, tile: mercantile.Tile, cellsize=30):

        self.grid_size = 256
        vertices = self.grid_size ** 2
        indices = 6 * (self.grid_size - 1) ** 2
        super().__init__(indices, vertices, True, mode=Mesh.TRIANGLES)
        self.mtile = tile
        self.cellsize = cellsize

    def set_buffers(self, vertices, indices, normals):

        # Now allocate everything
        vert_buf = self.acquire_vertex_array()
        vert_buf[:] = vertices.ravel()
        self.release_vertex_array()

        norm_buf = self.acquire_normal_array()
        norm_buf[:] = normals.ravel()
        self.release_normal_array()

        index_buf = self.acquire_index_array()
        index_buf[:] = indices.ravel()
        self.release_index_array()

        self.bounding_box = BoundingBox(0, -10, 0, 256 * self.cellsize, 10, 256 * self.cellsize)


class TileRenderThread(Thread):

    def __init__(self, grid):
        super().__init__()
        self.grid = grid
        self.task = Task("Generating Terrain Mesh")

    def run(self):
        if sys.platform == 'win32':
            asyncio.set_event_loop(asyncio.ProactorEventLoop())
        else:
            asyncio.set_event_loop(asyncio.SelectorEventLoop())

        e = ElevationService()
        e.zoom = self.grid.zoom
        wgs84 = self.grid.extent.project(Proj(init='EPSG:4326'))
        self.grid.tiles = list(e.tiles(wgs84))
        e.get_tiles(wgs84)
        self.grid._ul = self.grid.tiles[0]
        self.grid._br = self.grid.tiles[-1]
        cellsize = self.grid.cellsize
        grid_size = 256

        self.task.target = len(self.grid.tiles)
        self.task.status = Task.RUNNING
        for t in self.grid.tiles:
            data = e.get_grid(t.x, t.y).T

            # Setup vertices
            height, width = data.shape
            indices = numpy.indices(data.shape)
            heightfield = numpy.zeros((height, width, 3))
            heightfield[:, :, 0] = indices[0] * cellsize
            heightfield[:, :, 2] = indices[1] * cellsize
            heightfield[:, :, 1] = data

            # Setup indices
            index_array = []
            for i in range(grid_size - 1):
                for j in range(grid_size - 1):
                    a = i + grid_size * j
                    b = i + grid_size * (j + 1)
                    c = (i + 1) + grid_size * (j + 1)
                    d = (i + 1) + grid_size * j
                    index_array += [a, b, d]
                    index_array += [b, c, d]

            # Setup normals
            normals = generate_vertex_normals(
                heightfield.reshape(-1, heightfield.shape[-1]),                             # vertices
                numpy.array([index_array[i:i + 3] for i in range(len(index_array) - 2)])    # faces
            ).reshape(heightfield.shape)

            indices = numpy.array(index_array)
            self.sync_with_main(self.grid.add_tile, (t, heightfield, indices, normals), block=True)
            self.task.inc_progress()

        self.sync_with_main(self.grid.refresh_bounding_box)
        self.sync_with_main(self.grid.resolve_seams, block=True)
        self.grid._can_render = True
        self.sync_with_main(post_redisplay, kwargs={'reset': True})

        self.task.status = Task.COMPLETE
        self.sync_with_main(post_redisplay)


class TileGridRenderable(Renderable):
    """ Rendering interface for a collection of TileMesh's """

    def __init__(self, extent=None):
        super().__init__()
        self._extent = extent
        self._wgs84 = extent.project(Proj(init='EPSG:4326'))
        self.tiles = []
        self._ul = None
        self._br = None
        self._meshes = []
        self._can_render = False
        self.cellsize = 30
        self.zoom = 10
        self.bounding_box = BoundingBox()
        self.shader = TileShaderProgram.get()
        TileRenderThread(self).start()

    @property
    def extent(self):
        return self._extent

    @extent.setter
    def extent(self, extent):
        self._extent = extent
        # Todo - reset? Clear house? We should probably look at the tiles that we need and see what needs to be removed

    def add_tile(self, t, vertices, indices, normals):
        tile = TileMesh(t, self.cellsize)
        tile.set_buffers(vertices, indices, normals)
        self._meshes.append(tile)

    def resolve_seams(self):
        """ Resolves seems to eliminate weird looking edges """
        pass

    def refresh_bounding_box(self):
        width = (self._br.x - self._ul.x + 1) * 256 * self.cellsize
        height = (self._br.y - self._ul.y + 1) * 256 * self.cellsize

        self.bounding_box = BoundingBox(0, -10, 0, width, 10, height)

    def render(self, camera):
        if self._can_render:
            for tile in self._meshes:
                camera.push_matrix()
                camera.matrix *= Matrix44.from_translation(
                    Vector3([(tile.mtile.x - self._ul.x) * 255 * tile.cellsize, 0,
                             (tile.mtile.y - self._ul.y) * 255 * tile.cellsize])
                    )
                self.shader.current_tile = tile
                self.shader.pre_render(camera)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, tile.index_buffer)
                glDrawElements(tile.mode, tile.num_indices, GL_UNSIGNED_INT, None)
                self.shader.post_render(camera)
                self.shader.current_tile = None
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
                camera.pop_matrix()
