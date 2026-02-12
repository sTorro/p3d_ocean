# -*- coding: utf-8 -*-

"""
Filename: ocean_time_spectrum.py
Author: storro
Date: 2026-02-11
Description: Advances phases and builds a time-varying frequency spectrum.
"""

import math
import random

from dataclasses import dataclass
from array import array
from panda3d.core import ComputeNode, Shader, Texture

from src.util.assets_path import assets_path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


@dataclass
class OceanTimeConfig:
    resolution: int = 512
    ocean_size: int = 1024
    choppiness: float = 1.5


class OceanTimeSpectrum:
    """Advances phases and builds a time-varying frequency spectrum."""

    def __init__(self,
                 app: "OceanApp",
                 initial_spectrum: Texture,
                 config: OceanTimeConfig) -> None:
        self._app = app
        self.config = config
        self.initial_spectrum = initial_spectrum

        self.phase_ping = self._make_phase_texture("phase_ping", seed_random=True)
        self.phase_pong = self._make_phase_texture("phase_pong", seed_random=False)
        self._phase_is_ping = True

        self.spectrum = self._make_spectrum_texture("time_spectrum")

        self._phase_shader = Shader.load_compute(
            Shader.SL_GLSL, assets_path("shaders", "phase.comp.glsl")
        )
        self._spectrum_shader = Shader.load_compute(
            Shader.SL_GLSL, assets_path("shaders", "time_spectrum.comp.glsl")
        )

        # duplicated in ocean_displacement.py, consider refactoring
        groups = (
            int((self.config.resolution + 31) // 32),
            int((self.config.resolution + 31) // 32),
            1
        )

        phase_node = ComputeNode("ocean_phase")
        phase_node.add_dispatch(*groups)
        self.phase_np = self._app.render.attach_new_node(phase_node)
        self.phase_np.set_bin("fixed", 0)
        self.phase_np.set_shader(self._phase_shader)

        spectrum_node = ComputeNode("ocean_spectrum")
        spectrum_node.add_dispatch(*groups)
        self.spectrum_np = self._app.render.attach_new_node(spectrum_node)
        self.spectrum_np.set_bin("fixed", 1)
        self.spectrum_np.set_shader(self._spectrum_shader)

        self.phase_np.set_shader_input("u_resolution", int(self.config.resolution))
        self.phase_np.set_shader_input("u_ocean_size", int(self.config.ocean_size))

        self.spectrum_np.set_shader_input("u_resolution", int(self.config.resolution))
        self.spectrum_np.set_shader_input("u_ocean_size", int(self.config.ocean_size))
        self.spectrum_np.set_shader_input("u_choppiness", float(self.config.choppiness))
        self.spectrum_np.set_shader_input("u_initial_spectrum", self.initial_spectrum)
        self.spectrum_np.set_shader_input("u_spectrum", self.spectrum)

        self._apply_phase_bindings(delta_time=0.0)

    def _make_phase_texture(self, name: str, seed_random: bool) -> Texture:
        tex = Texture(name)
        tex.setup_2d_texture(self.config.resolution,
                             self.config.resolution,
                             Texture.T_float,
                             Texture.F_r32)
        tex.set_clear_color((0.0, 0.0, 0.0, 0.0))

        if seed_random:
            count = self.config.resolution * self.config.resolution
            phases = array("f", (random.random() * (2.0 * math.pi) for _ in range(count)))
            tex.set_ram_image(phases.tobytes())

        return tex

    def _make_spectrum_texture(self, name: str) -> Texture:
        tex = Texture(name)
        tex.setup_2d_texture(self.config.resolution,
                             self.config.resolution,
                             Texture.T_float,
                             Texture.F_rgba32)
        tex.set_clear_color((0.0, 0.0, 0.0, 0.0))
        return tex

    def _apply_phase_bindings(self, delta_time: float) -> None:
        if self._phase_is_ping:
            src = self.phase_ping
            dst = self.phase_pong
        else:
            src = self.phase_pong
            dst = self.phase_ping

        self.phase_np.set_shader_input("u_phases", src)
        self.phase_np.set_shader_input("u_delta_phases", dst)
        self.phase_np.set_shader_input("u_delta_time", float(delta_time))

        self.spectrum_np.set_shader_input("u_phases", dst)

    def step(self, delta_time: float) -> None:
        """Call once per frame."""
        self._apply_phase_bindings(delta_time=delta_time)
        self._phase_is_ping = not self._phase_is_ping

    def debug_current_phase_texture(self) -> Texture:
        return self.phase_ping if self._phase_is_ping else self.phase_pong
