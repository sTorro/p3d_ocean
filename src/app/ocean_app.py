# -*- coding: utf-8 -*-

"""
Filename: ocean_app.py
Author: storro
Date: 2026-02-11
Description: Main application class, sets up the scene, ocean simulation and rendering
"""

import logging

from direct.showbase.ShowBase import ShowBase
from direct.task.Task import Task
from panda3d.core import (
    BitMask32,
    ClockObject,
    GraphicsOutput,
    NodePath,
    SamplerState,
    Shader,
    Texture,
    load_prc_file_data
)

from src.app.debug_cards import DebugCardController
from src.app.input import OrbitCameraController
from src.app.ocean_geometry import make_ocean_grid
from src.gui.debug_imgui import DebugImGui
from src.ocean.ocean_displacement import OceanDisplacement, OceanMapsConfig
from src.ocean.ocean_ifft2d import OceanFFTConfig, OceanIFFT2D
from src.ocean.ocean_spectrum_generator import OceanSpectrumConfig, OceanSpectrumGenerator
from src.ocean.ocean_time_spectrum import OceanTimeConfig, OceanTimeSpectrum
from src.util.assets_path import assets_path
from src.util.logging_config import setup_logging


class OceanApp(ShowBase):
    def __init__(self) -> None:
        self.configure_panda()
        super().__init__()

        setup_logging()

        self.debug_gui = DebugImGui()

        ############################################################################################
        # Simulation parameters

        # Simulation texture resolution. It's the size of the frequency domain textures and 
        # the produced displacement/normal maps: resolution x resolution
        # Higher resolution = more detail (finer waves, less blocky normals), 
        # but more cost: roughly O(n2 log n) and more VRAM. Must be a power of 2 for the FFT
        self._resolution = 1024

        # World-space size of the ocean patch. Bigger = bigger waves but more tiling
        # This is the "L" parameter in Tessendorf's paper
        # Larger = the same resolution samples cover a larger area → waves get broader,
        # lower spatial frequency and detail density decreases (each texel represents more meters)
        # Smaller = more detail per meter (but can look “too busy” if very small)
        self._ocean_size = 150 # the physical size of the simulated patch

        # Adjusting the wind changes the wave spectrum and thus the overall look of the ocean
        self._wind_x = 60.0
        self._wind_y = 30.0

        # Higher = sharper peaks, but more distortion
        self._choppiness = 1.5

        # World-space size of the mesh (the plane width/height).
        # Bigger = you literally render a bigger patch of water around you
        grid_size = 200.0

        # Mesh tessellation density. Bigger = more vertices, 
        # so the displacement can bend the surface more smoothly (at a cost)
        grid_subdiv = 1024

        # How many times the displacement/normal textures repeat across the mesh
        # Bigger = more repetitions (smaller-looking waves, more tiling).
        uv_tiles = 1.0

        # Rendering parameters
        self._disp_scale = 0.35 # global scale for the displacement effect, purely visual tweak (not related to the ocean_size parameter)
        self._light_dir = (-0.4, -0.8, -0.25)
        self._sun_color = (1.0, 0.94, 0.78)  # warm sunlight, just a fake
        self._sky_color = (3.2, 9.6, 12.8)
        self._water_color = (0.004, 0.016, 0.047)
        self._exposure = 0.15

        # Refraction
        self._refraction_strength = 0.02

        # Specular
        self._roughness = 0.15
        self._specular_strength = 1.0

        # Sub-surface scattering
        self._sss_intensity = 1.5
        self._sss_color = (0.1, 0.4, 0.35)

        # Depth-based absorption
        self._shallow_color = (0.0, 0.15, 0.12)
        self._absorption_depth = 0.1

        # Detail normal overlay
        self._detail_strength = 0.150    # blend intensity
        self._detail_scale = 1.25        # tiles per meter (higher = more repetition)
        self._detail_fade_near = 5.0     # start fading at this distance
        self._detail_fade_far = 200.0    # fully faded by this distance
        ############################################################################################

        ###############################
        # values for a big wavey ocean
        # self._ocean_size = 8192
        # self._resolution = 2048
        # self._wind_x = 60.0
        # self._wind_y = 35.0
        # self._choppiness = 3.0
        # self._disp_scale = 1.2
        # grid_size = 8192
        # grid_subdiv = 512
        # uv_tiles = 1.0
        ###############################

        ###############################
        # values for a quiet, close-detail ocean (doubled size)
        # self._ocean_size = 16384
        # self._resolution = 2048
        # self._wind_x = 8.0
        # self._wind_y = 5.0
        # self._choppiness = 0.6
        # self._disp_scale = 0.35
        # grid_size = 16384
        # grid_subdiv = 1024
        # uv_tiles = 1.0
        ###############################

        # following logic should be in a setup() function
        self.set_frame_rate_meter(True)
        self.disable_mouse()

        logging.info("Creating ocean mesh...")
        self.ocean_np: NodePath = make_ocean_grid(grid_size, 
                                                  grid_subdiv, 
                                                  uv_tiles)
        self.ocean_np.reparent_to(self.render)
        # self.ocean_np.set_color(0.0, 0.35, 0.6, 1.0)
        self.ocean_np.set_light_off(1)
        self.ocean_np.set_two_sided(True)
        logging.info("Ocean mesh created with %d vertices", (grid_subdiv + 1) ** 2)

        self._wireframe = False
        self.accept("w", self._toggle_wireframe)

        # Simple orbit camera
        self._orbit_camera = OrbitCameraController(self)
        logging.info("Orbit camera controller initialized")

        # Initial spectrum (generated once at startup)
        self._spectrum_gen = OceanSpectrumGenerator()
        self.initial_spectrum_tex = self._spectrum_gen.generate(
            self,
            config=OceanSpectrumConfig(
                self._resolution,
                self._ocean_size,
                self._wind_x,
                self._wind_y,
            ),
        )
        logging.info("Initial spectrum generated")

        # Phase evolution + time-varying spectrum
        self.ocean_time = OceanTimeSpectrum(
            self,
            self.initial_spectrum_tex,
            OceanTimeConfig(self._resolution,
                            self._ocean_size,
                            self._choppiness)
        )
        logging.info("Ocean time spectrum initialized")

        # Inverse FFT to spatial domain
        self.ocean_ifft = OceanIFFT2D(
            self,
            self.ocean_time.spectrum,
            OceanFFTConfig(self._resolution)
        )
        logging.info("Ocean IFFT initialized")

        # Displacement + slope/normal maps
        self.ocean_maps = OceanDisplacement(
            self,
            self.ocean_ifft.displacement,
            OceanMapsConfig(self._resolution, self._ocean_size)
        )
        logging.info("Ocean displacement maps initialized")

        # Render the displaced ocean with simple lighting
        ocean_shader = Shader.load(
            Shader.SL_GLSL,
            assets_path("shaders", "ocean.vert.glsl"),
            assets_path("shaders", "ocean.frag.glsl")
        )
        self.ocean_np.set_shader(ocean_shader)

        # Refraction buffer (scene color + depth)
        self._refraction_cam_mask = BitMask32.bit(1)
        self._setup_refraction_buffer()

        self.ocean_np.set_shader_input("u_displacement_map", self.ocean_maps.displacement_map)
        self.ocean_np.set_shader_input("u_normal_map", self.ocean_maps.slope_map)
        self.ocean_np.set_shader_input("u_disp_scale", self._disp_scale)
        self.ocean_np.set_shader_input("u_scene_color", self._scene_color_tex)
        self.ocean_np.set_shader_input("u_scene_depth", self._scene_depth_tex)
        self.ocean_np.set_shader_input("u_refraction_strength", float(self._refraction_strength))
        self.ocean_np.set_shader_input("u_near", float(self.camLens.get_near()))
        self.ocean_np.set_shader_input("u_far", float(self.camLens.get_far()))

        # Lighting & shading
        self.ocean_np.set_shader_input("u_light_dir", self._light_dir)
        self.ocean_np.set_shader_input("u_sun_color", self._sun_color)
        self.ocean_np.set_shader_input("u_sky_color", self._sky_color)
        self.ocean_np.set_shader_input("u_water_color", self._water_color)
        self.ocean_np.set_shader_input("u_exposure", self._exposure)

        # Specular
        self.ocean_np.set_shader_input("u_roughness", float(self._roughness))
        self.ocean_np.set_shader_input("u_specular_strength", float(self._specular_strength))

        # Sub-surface scattering
        self.ocean_np.set_shader_input("u_sss_intensity", float(self._sss_intensity))
        self.ocean_np.set_shader_input("u_sss_color", self._sss_color)

        # Absorption
        self.ocean_np.set_shader_input("u_shallow_color", self._shallow_color)
        self.ocean_np.set_shader_input("u_absorption_depth", float(self._absorption_depth))

        # Detail normal overlay
        self._detail_normal_tex = self._load_detail_normal_texture()
        self.ocean_np.set_shader_input("u_detail_normal", self._detail_normal_tex)
        self.ocean_np.set_shader_input("u_detail_strength", float(self._detail_strength))
        self.ocean_np.set_shader_input("u_detail_scale", float(self._detail_scale))
        self.ocean_np.set_shader_input("u_detail_fade_near", float(self._detail_fade_near))
        self.ocean_np.set_shader_input("u_detail_fade_far", float(self._detail_fade_far))

        # Ensure the compute chain runs before the ocean draw
        self.ocean_np.set_bin("fixed", 1000)

        self.task_mgr.add(self._ocean_step_task, "ocean_step")

        # Debug: visualize textures on-screen
        self._debug_cards = DebugCardController(
            self,
            self.initial_spectrum_tex,
            self.ocean_time,
            self.ocean_maps
        )

        # Bind the running app to ImGui so parameters can be edited live.
        self.debug_gui.bind_ocean(self)
        logging.info("Debug ImGui initialized and bound to ocean app")

    def _ocean_step_task(self, task: Task) -> int:
        dt = ClockObject.get_global_clock().get_dt()
        self.ocean_time.step(dt)
        self.ocean_np.set_shader_input("u_camera_pos", self.camera.get_pos(self.render))
        return task.cont

    def _toggle_wireframe(self) -> None:
        self._wireframe = not self._wireframe
        if self._wireframe:
            self.render.set_render_mode_wireframe()
        else:
            self.render.clear_render_mode()

    def _setup_refraction_buffer(self) -> None:
        width = max(1, self.win.get_x_size())
        height = max(1, self.win.get_y_size())

        self._scene_color_tex = Texture("scene_color")
        self._scene_depth_tex = Texture("scene_depth")

        self._scene_buffer = self.win.make_texture_buffer(
            "scene_color_buffer",
            width,
            height,
            self._scene_color_tex,
            to_ram=False,
        )
        self._scene_buffer.set_sort(-100)

        # Explicitly clear the refraction buffer every frame.
        # Without this, stale/undefined depth values cause the refraction
        # thickness math to intermittently produce black patches.
        self._scene_buffer.set_clear_color_active(True)
        self._scene_buffer.set_clear_depth_active(True)
        self._scene_buffer.set_clear_color((0.0, 0.0, 0.0, 1.0))
        self._scene_buffer.set_clear_depth(1.0)

        self._scene_buffer.add_render_texture(
            self._scene_depth_tex,
            GraphicsOutput.RTMBindOrCopy,
            GraphicsOutput.RTPDepth,
        )

        self._scene_cam = self.make_camera(self._scene_buffer)
        self._scene_cam.reparent_to(self.render)
        self._scene_cam.node().set_lens(self.camLens)
        self._scene_cam.node().set_camera_mask(self._refraction_cam_mask)

        # Hide the water from the refraction buffer to avoid feedback.
        self.ocean_np.hide(self._refraction_cam_mask)

    def configure_panda(self) -> None:
        prc_data = f"""
            window-title Tessendorf Ocean
            win-size 1920 1080
            fullscreen false
            sync-video true
            # hardware-animated-vertices true
            # basic-shaders-only false
        """
        load_prc_file_data("", prc_data)

    def get_ocean_parameters(self) -> dict:
        return {
            "resolution": int(self._resolution),
            "ocean_size": int(self._ocean_size),
            "wind_x": float(self._wind_x),
            "wind_y": float(self._wind_y),
            "choppiness": float(self._choppiness),
            "disp_scale": float(self._disp_scale),
            "light_dir": tuple(self._light_dir),
            "sun_color": tuple(self._sun_color),
            "sky_color": tuple(self._sky_color),
            "water_color": tuple(self._water_color),
            "exposure": float(self._exposure),
            "refraction_strength": float(self._refraction_strength),
            "roughness": float(self._roughness),
            "specular_strength": float(self._specular_strength),
            "sss_intensity": float(self._sss_intensity),
            "sss_color": tuple(self._sss_color),
            "shallow_color": tuple(self._shallow_color),
            "absorption_depth": float(self._absorption_depth),
            "detail_strength": float(self._detail_strength),
            "detail_scale": float(self._detail_scale),
            "detail_fade_near": float(self._detail_fade_near),
            "detail_fade_far": float(self._detail_fade_far),
        }

    def set_choppiness(self, value: float) -> None:
        self._choppiness = float(value)
        self.ocean_time.config.choppiness = float(value)
        self.ocean_time.spectrum_np.set_shader_input("u_choppiness", float(value))

    def set_wind(self, wind_x: float, wind_y: float) -> None:
        self._wind_x = float(wind_x)
        self._wind_y = float(wind_y)
        self._regenerate_initial_spectrum()

    def set_ocean_size(self, ocean_size: int) -> None:
        self._ocean_size = int(ocean_size)
        self.ocean_time.config.ocean_size = int(ocean_size)
        self.ocean_time.phase_np.set_shader_input("u_ocean_size", int(ocean_size))
        self.ocean_time.spectrum_np.set_shader_input("u_ocean_size", int(ocean_size))

        self.ocean_maps.config.ocean_size = int(ocean_size)
        self.ocean_maps.slope_np.set_shader_input("u_ocean_size", int(ocean_size))

        self._regenerate_initial_spectrum()

    def set_disp_scale(self, value: float) -> None:
        self._disp_scale = float(value)
        self.ocean_np.set_shader_input("u_disp_scale", float(value))

    def set_exposure(self, value: float) -> None:
        self._exposure = float(value)
        self.ocean_np.set_shader_input("u_exposure", float(value))

    def set_light_dir(self, x: float, y: float, z: float) -> None:
        self._light_dir = (float(x), float(y), float(z))
        self.ocean_np.set_shader_input("u_light_dir", self._light_dir)

    def set_sky_color(self, r: float, g: float, b: float) -> None:
        self._sky_color = (float(r), float(g), float(b))
        self.ocean_np.set_shader_input("u_sky_color", self._sky_color)

    def set_water_color(self, r: float, g: float, b: float) -> None:
        self._water_color = (float(r), float(g), float(b))
        self.ocean_np.set_shader_input("u_water_color", self._water_color)

    def set_refraction_strength(self, value: float) -> None:
        self._refraction_strength = float(value)
        self.ocean_np.set_shader_input("u_refraction_strength", self._refraction_strength)

    def set_sun_color(self, r: float, g: float, b: float) -> None:
        self._sun_color = (float(r), float(g), float(b))
        self.ocean_np.set_shader_input("u_sun_color", self._sun_color)

    def set_roughness(self, value: float) -> None:
        self._roughness = float(value)
        self.ocean_np.set_shader_input("u_roughness", self._roughness)

    def set_specular_strength(self, value: float) -> None:
        self._specular_strength = float(value)
        self.ocean_np.set_shader_input("u_specular_strength", self._specular_strength)

    def set_sss_intensity(self, value: float) -> None:
        self._sss_intensity = float(value)
        self.ocean_np.set_shader_input("u_sss_intensity", self._sss_intensity)

    def set_sss_color(self, r: float, g: float, b: float) -> None:
        self._sss_color = (float(r), float(g), float(b))
        self.ocean_np.set_shader_input("u_sss_color", self._sss_color)

    def set_shallow_color(self, r: float, g: float, b: float) -> None:
        self._shallow_color = (float(r), float(g), float(b))
        self.ocean_np.set_shader_input("u_shallow_color", self._shallow_color)

    def set_absorption_depth(self, value: float) -> None:
        self._absorption_depth = float(value)
        self.ocean_np.set_shader_input("u_absorption_depth", self._absorption_depth)

    def _regenerate_initial_spectrum(self) -> None:
        self._spectrum_gen.generate(
            self,
            config=OceanSpectrumConfig(
                self._resolution,
                self._ocean_size,
                self._wind_x,
                self._wind_y,
            ),
            target_tex=self.initial_spectrum_tex,
        )

    def _load_detail_normal_texture(self) -> Texture:
        """Load the tileable detail normal map with proper filtering."""
        
        tex = self.loader.load_texture(
            assets_path("textures", "detail_normal.png")
        )
        
        # Linear filtering + mipmaps + anisotropy to avoid aliasing
        tex.set_minfilter(SamplerState.FT_linear_mipmap_linear)
        tex.set_magfilter(SamplerState.FT_linear)
        tex.set_anisotropic_degree(8)
        tex.set_wrap_u(SamplerState.WM_repeat)
        tex.set_wrap_v(SamplerState.WM_repeat)
        return tex

    def set_detail_strength(self, value: float) -> None:
        self._detail_strength = float(value)
        self.ocean_np.set_shader_input("u_detail_strength", self._detail_strength)

    def set_detail_scale(self, value: float) -> None:
        self._detail_scale = float(value)
        self.ocean_np.set_shader_input("u_detail_scale", self._detail_scale)

    def set_detail_fade_near(self, value: float) -> None:
        self._detail_fade_near = float(value)
        self.ocean_np.set_shader_input("u_detail_fade_near", self._detail_fade_near)

    def set_detail_fade_far(self, value: float) -> None:
        self._detail_fade_far = float(value)
        self.ocean_np.set_shader_input("u_detail_fade_far", self._detail_fade_far)
