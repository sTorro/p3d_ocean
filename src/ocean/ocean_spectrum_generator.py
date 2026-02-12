# -*- coding: utf-8 -*-

"""
Filename: ocean_spectrum_generator.py
Author: storro
Date: 2026-02-11
Description: Generates the initial ocean spectrum texture using a compute shader
"""

from dataclasses import dataclass

from panda3d.core import NodePath, Shader, ShaderAttrib, Texture

from src.util.assets_path import assets_path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


@dataclass
class OceanSpectrumConfig:
    resolution: int = 512
    ocean_size: int = 1024
    wind_x: float = 60.0
    wind_y: float = 30.0


class OceanSpectrumGenerator:
    """Generates the initial ocean spectrum texture using a compute shader."""

    def __init__(self, shader_path: str | None = None) -> None:
        if shader_path is None:
            shader_path = assets_path("shaders", "initial_spectrum.comp.glsl")
        self._shader = Shader.load_compute(Shader.SL_GLSL, shader_path)

    def create_texture(self, resolution: int) -> Texture:
        tex = Texture("initial_spectrum")
        tex.setup_2d_texture(resolution,
                             resolution,
                             Texture.T_float,
                             Texture.F_r32)
        tex.set_clear_color((0.0, 0.0, 0.0, 0.0))
        return tex

    def generate(self,
                 app: "OceanApp",
                 config: OceanSpectrumConfig,
                 target_tex: Texture | None = None) -> Texture:
        """Dispatch the compute shader immediately and return the filled texture."""

        if target_tex is None:
            target_tex = self.create_texture(resolution=config.resolution)

        dummy = NodePath("spectrum_dummy")
        dummy.set_shader(self._shader)
        dummy.set_shader_input("u_initial_spectrum", target_tex)
        dummy.set_shader_input("u_resolution", int(config.resolution))
        dummy.set_shader_input("u_ocean_size", int(config.ocean_size))
        dummy.set_shader_input("u_wind", (float(config.wind_x), float(config.wind_y)))

        sattr = dummy.get_attrib(ShaderAttrib)
        groups = (int((config.resolution + 31) // 32), int((config.resolution + 31) // 32), 1)
        app.graphics_engine.dispatch_compute(groups, sattr, app.win.get_gsg()) # type: ignore
        return target_tex
