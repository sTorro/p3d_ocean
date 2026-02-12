# -*- coding: utf-8 -*-

"""
Filename: ocean_displacement.py
Author: storro
Date: 2026-02-11
Description: Generates displacement and slope/normal textures from the IFFT output
"""

from dataclasses import dataclass

from panda3d.core import ComputeNode, SamplerState, Shader, Texture

from src.util.assets_path import assets_path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


@dataclass
class OceanMapsConfig:
    resolution: int = 512
    ocean_size: int = 1024


class OceanDisplacement:
    def __init__(
        self,
        app: "OceanApp", 
        ifft_output: Texture, 
        config: OceanMapsConfig, 
        bin_start: int = 100
    ) -> None:
        self._app = app
        self.config = config
        self.ifft_output = ifft_output

        self.displacement_map = self._make_rgba32_texture("ocean_displacement")
        self.slope_map = self._make_rgba32_texture("ocean_slope")

        self._sh_unpack = Shader.load_compute(
            Shader.SL_GLSL, assets_path("shaders", "unpack_displacement.comp.glsl")
        )
        self._sh_slope = Shader.load_compute(
            Shader.SL_GLSL, assets_path("shaders", "slope_map.comp.glsl")
        )

        # duplicated in ocean_time_spectrum.py, consider refactoring
        groups = (
            int((self.config.resolution + 31) // 32),
            int((self.config.resolution + 31) // 32),
            1
        )

        unpack_node = ComputeNode("ocean_unpack_displacement")
        unpack_node.add_dispatch(*groups)
        self.unpack_np = self._app.render.attach_new_node(unpack_node)
        self.unpack_np.set_bin("fixed", bin_start)
        self.unpack_np.set_shader(self._sh_unpack)
        self.unpack_np.set_shader_input("u_resolution", int(self.config.resolution))
        self.unpack_np.set_shader_input("u_ifft", self.ifft_output)
        self.unpack_np.set_shader_input("u_displacement", self.displacement_map)

        slope_node = ComputeNode("ocean_slope_map")
        slope_node.add_dispatch(*groups)
        self.slope_np = self._app.render.attach_new_node(slope_node)
        self.slope_np.set_bin("fixed", bin_start + 1)
        self.slope_np.set_shader(self._sh_slope)
        self.slope_np.set_shader_input("u_resolution", int(self.config.resolution))
        self.slope_np.set_shader_input("u_ocean_size", int(self.config.ocean_size))
        self.slope_np.set_shader_input("u_displacement", self.displacement_map)
        self.slope_np.set_shader_input("u_slope_map", self.slope_map)

    def _make_rgba32_texture(self, name: str) -> Texture:
        tex = Texture(name)
        tex.setup_2d_texture(self.config.resolution, 
                             self.config.resolution, 
                             Texture.T_float, 
                             Texture.F_rgba32)
        tex.set_clear_color((0.0, 0.0, 0.0, 0.0))
        # Bilinear filtering — without this, compute-written textures default
        # to nearest-neighbor, which looks blocky/pixelated up close.
        tex.set_minfilter(SamplerState.FT_linear)
        tex.set_magfilter(SamplerState.FT_linear)
        tex.set_wrap_u(SamplerState.WM_repeat)
        tex.set_wrap_v(SamplerState.WM_repeat)
        return tex
