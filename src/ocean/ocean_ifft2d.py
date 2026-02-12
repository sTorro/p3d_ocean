# -*- coding: utf-8 -*-

"""
Filename: ocean_ifft2d.py
Author: storro
Date: 2026-02-11
Description: Converts the time spectrum to spatial domain using a 2D Inverse Fast Fourier Transform (IFFT)
"""

import math

from dataclasses import dataclass
from panda3d.core import ComputeNode, Shader, Texture
from src.util.assets_path import assets_path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


@dataclass
class OceanFFTConfig:
    resolution: int = 512


class OceanIFFT2D:
    def __init__(
            self,
            app: "OceanApp",
            input_spectrum: Texture,
            config: OceanFFTConfig,
            bin_start: int = 10
    ) -> None:
        self._app = app
        self.config = config
        self.input_spectrum = input_spectrum

        n = int(self.config.resolution)
        if n <= 0 or (n & (n - 1)) != 0:
            raise ValueError("resolution must be a power of two")

        # The compute shaders use a fixed local_size_x (currently 256) and we dispatch
        # enough work groups to cover (n/2) butterfly threads per row/column
        self._workgroup_size_x = 256
        self._thread_count = n // 2
        self._groups_x = (self._thread_count + self._workgroup_size_x - 1) // self._workgroup_size_x

        self._stages = int(math.log2(n))

        self.ping = self._make_rgba32_texture("fft_ping")
        self.pong = self._make_rgba32_texture("fft_pong")
        self._sh_horizontal = Shader.load_compute(
            Shader.SL_GLSL, assets_path("shaders", "fft_horizontal.comp.glsl")
        )
        self._sh_vertical = Shader.load_compute(
            Shader.SL_GLSL, assets_path("shaders", "fft_vertical.comp.glsl")
        )

        current_in = self.input_spectrum
        current_out = self.ping
        order = bin_start

        for stage in range(self._stages):
            p = 1 << stage
            node = ComputeNode(f"ocean_fft_h_{p}")
            # Dispatch: X covers butterfly threads, Y selects the row
            node.add_dispatch(self._groups_x, n, 1)
            np = self._app.render.attach_new_node(node)
            np.set_bin("fixed", order)
            np.set_shader(self._sh_horizontal)
            np.set_shader_input("u_total_count", n)
            np.set_shader_input("u_subseq_count", p)
            np.set_shader_input("u_input", current_in)
            np.set_shader_input("u_output", current_out)
            order += 1
            current_in, current_out = current_out, (
                self.pong if current_out is self.ping else self.ping
            )

        for stage in range(self._stages):
            p = 1 << stage
            node = ComputeNode(f"ocean_fft_v_{p}")
            # Dispatch: X covers butterfly threads, Y selects the column
            node.add_dispatch(self._groups_x, n, 1)
            np = self._app.render.attach_new_node(node)
            np.set_bin("fixed", order)
            np.set_shader(self._sh_vertical)
            np.set_shader_input("u_total_count", n)
            np.set_shader_input("u_subseq_count", p)
            np.set_shader_input("u_input", current_in)
            np.set_shader_input("u_output", current_out)
            order += 1
            current_in, current_out = current_out, (
                self.pong if current_out is self.ping else self.ping
            )

        self.displacement = current_in

    def _make_rgba32_texture(self, name: str) -> Texture:
        tex = Texture(name)
        tex.setup_2d_texture(self.config.resolution,
                             self.config.resolution,
                             Texture.T_float,
                             Texture.F_rgba32)
        tex.set_clear_color((0.0, 0.0, 0.0, 0.0))
        return tex
