# -*- coding: utf-8 -*-

"""
Filename: debug_manager.py
Author: storro
Date: 2026-02-11
Description: ImGui debug overlay for performance stats and ocean parameters
"""

from direct.showbase.DirectObject import DirectObject

# edit ImGuiBackend and replace the shader import with: "from .shaders import FRAG_SHADER, VERT_SHADER"
import p3dimgui as p3dimgui

from imgui_bundle import imgui, imgui_ctx

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


class DebugImGui(DirectObject):
    def __init__(self):
        self.enabled = False

        # When True, ImGui wants to consume mouse input this frame.
        # Use this to prevent game controls (orbit camera) from reacting to UI drags.
        self.want_capture_mouse = False

        self._ocean_app: "OceanApp | None" = None
        self._ocean_params = {}

        p3dimgui.init()

        self.accept("imgui-new-frame", self.draw)
        self.accept("f1", self.toggle)

        imgui.get_style().font_scale_dpi = 2.0

    def bind_ocean(self, ocean_app) -> None:
        """Bind a running OceanApp so we can tweak parameters live."""
        self._ocean_app = ocean_app
        if hasattr(ocean_app, "get_ocean_parameters"):
            self._ocean_params = dict(ocean_app.get_ocean_parameters())

    def draw(self) -> None:
        """Draw ImGui debug window if enabled."""
        # Keep the capture state up-to-date even if the window is hidden.
        self.want_capture_mouse = bool(imgui.get_io().want_capture_mouse)

        if not self.enabled:
            return

        # Simple movable ImGui window
        with imgui_ctx.begin(
            "Ocean Parameters", True, imgui.WindowFlags_.no_title_bar.value
        ) as window:
            if window:
                imgui.text("Ocean Parameters")
                imgui.separator()

                # Performance Stats Group (tree node for nested look)
                if imgui.collapsing_header("Performance Stats##group"):
                    fps = imgui.get_io().framerate
                    frame_time = 1000.0 / max(1.0, fps)
                    imgui.text(f"FPS: {fps:.1f}")
                    imgui.text(f"Frame Time: {frame_time:.2f} ms")
                imgui.spacing()

                if self._ocean_app is None:
                    imgui.text("No OceanApp bound")
                    return

                if not self._ocean_params:
                    self._ocean_params = dict(self._ocean_app.get_ocean_parameters())

                if imgui.collapsing_header("Ocean Simulation##group"):
                    imgui.text(
                        f"Resolution (restart/rebuild): {self._ocean_params.get('resolution', 0)}"
                    )

                    changed, ocean_size = imgui.input_int(
                        "Ocean size", int(self._ocean_params.get("ocean_size", 1024))
                    )
                    if changed:
                        ocean_size = max(1, int(ocean_size))
                        self._ocean_params["ocean_size"] = ocean_size
                        self._ocean_app.set_ocean_size(ocean_size)

                    changed_x, wind_x = imgui.input_float(
                        "Wind X", float(self._ocean_params.get("wind_x", 14.0))
                    )
                    changed_y, wind_y = imgui.input_float(
                        "Wind Y", float(self._ocean_params.get("wind_y", 14.0))
                    )
                    if changed_x or changed_y:
                        self._ocean_params["wind_x"] = float(wind_x)
                        self._ocean_params["wind_y"] = float(wind_y)
                        self._ocean_app.set_wind(float(wind_x), float(wind_y))

                    changed, choppiness = imgui.slider_float(
                        "Choppiness",
                        float(self._ocean_params.get("choppiness", 1.5)),
                        0.0,
                        5.0,
                    )
                    if changed:
                        self._ocean_params["choppiness"] = float(choppiness)
                        self._ocean_app.set_choppiness(float(choppiness))

                if imgui.collapsing_header("Ocean Rendering##group"):
                    changed, disp_scale = imgui.slider_float(
                        "Displacement scale",
                        float(self._ocean_params.get("disp_scale", 0.5)),
                        0.0,
                        2.0,
                    )
                    if changed:
                        self._ocean_params["disp_scale"] = float(disp_scale)
                        self._ocean_app.set_disp_scale(float(disp_scale))

                    changed, refr_strength = imgui.slider_float(
                        "Refraction strength",
                        float(self._ocean_params.get("refraction_strength", 0.02)),
                        0.0,
                        0.1,
                    )
                    if changed:
                        self._ocean_params["refraction_strength"] = float(refr_strength)
                        self._ocean_app.set_refraction_strength(float(refr_strength))

                    changed, exposure = imgui.slider_float(
                        "Exposure",
                        float(self._ocean_params.get("exposure", 0.35)),
                        0.0,
                        2.0,
                    )
                    if changed:
                        self._ocean_params["exposure"] = float(exposure)
                        self._ocean_app.set_exposure(float(exposure))

                    light_dir = self._ocean_params.get("light_dir", (-0.4, -0.8, -0.25))
                    changed_x, lx = imgui.input_float("Light dir X", float(light_dir[0]))
                    changed_y, ly = imgui.input_float("Light dir Y", float(light_dir[1]))
                    changed_z, lz = imgui.input_float("Light dir Z", float(light_dir[2]))
                    if changed_x or changed_y or changed_z:
                        self._ocean_params["light_dir"] = (float(lx), float(ly), float(lz))
                        self._ocean_app.set_light_dir(float(lx), float(ly), float(lz))

                    sky_color = self._ocean_params.get("sky_color", (3.2, 9.6, 12.8))
                    changed_r, sr = imgui.input_float("Sky R", float(sky_color[0]))
                    changed_g, sg = imgui.input_float("Sky G", float(sky_color[1]))
                    changed_b, sb = imgui.input_float("Sky B", float(sky_color[2]))
                    if changed_r or changed_g or changed_b:
                        self._ocean_params["sky_color"] = (float(sr), float(sg), float(sb))
                        self._ocean_app.set_sky_color(float(sr), float(sg), float(sb))

                    water_color = self._ocean_params.get("water_color", (0.004, 0.016, 0.047))
                    changed_r, wr = imgui.input_float("Water R", float(water_color[0]))
                    changed_g, wg = imgui.input_float("Water G", float(water_color[1]))
                    changed_b, wb = imgui.input_float("Water B", float(water_color[2]))
                    if changed_r or changed_g or changed_b:
                        self._ocean_params["water_color"] = (float(wr), float(wg), float(wb))
                        self._ocean_app.set_water_color(float(wr), float(wg), float(wb))

                if imgui.collapsing_header("Specular & SSS##group"):
                    changed, roughness = imgui.slider_float(
                        "Roughness",
                        float(self._ocean_params.get("roughness", 0.15)),
                        0.01,
                        1.0,
                    )
                    if changed:
                        self._ocean_params["roughness"] = float(roughness)
                        self._ocean_app.set_roughness(float(roughness))

                    changed, spec_str = imgui.slider_float(
                        "Specular strength",
                        float(self._ocean_params.get("specular_strength", 1.0)),
                        0.0,
                        5.0,
                    )
                    if changed:
                        self._ocean_params["specular_strength"] = float(spec_str)
                        self._ocean_app.set_specular_strength(float(spec_str))

                    sun_color = self._ocean_params.get("sun_color", (1.0, 0.94, 0.78))
                    changed_r, sunr = imgui.input_float("Sun R", float(sun_color[0]))
                    changed_g, sung = imgui.input_float("Sun G", float(sun_color[1]))
                    changed_b, sunb = imgui.input_float("Sun B", float(sun_color[2]))
                    if changed_r or changed_g or changed_b:
                        self._ocean_params["sun_color"] = (float(sunr), float(sung), float(sunb))
                        self._ocean_app.set_sun_color(float(sunr), float(sung), float(sunb))

                    imgui.separator()

                    changed, sss_int = imgui.slider_float(
                        "SSS intensity",
                        float(self._ocean_params.get("sss_intensity", 1.5)),
                        0.0,
                        5.0,
                    )
                    if changed:
                        self._ocean_params["sss_intensity"] = float(sss_int)
                        self._ocean_app.set_sss_intensity(float(sss_int))

                    sss_col = self._ocean_params.get("sss_color", (0.1, 0.4, 0.35))
                    changed_r, ssr = imgui.input_float("SSS R", float(sss_col[0]))
                    changed_g, ssg = imgui.input_float("SSS G", float(sss_col[1]))
                    changed_b, ssb = imgui.input_float("SSS B", float(sss_col[2]))
                    if changed_r or changed_g or changed_b:
                        self._ocean_params["sss_color"] = (float(ssr), float(ssg), float(ssb))
                        self._ocean_app.set_sss_color(float(ssr), float(ssg), float(ssb))

                if imgui.collapsing_header("Absorption##group"):
                    shallow = self._ocean_params.get("shallow_color", (0.0, 0.15, 0.12))
                    changed_r, shr = imgui.input_float("Shallow R", float(shallow[0]))
                    changed_g, shg = imgui.input_float("Shallow G", float(shallow[1]))
                    changed_b, shb = imgui.input_float("Shallow B", float(shallow[2]))
                    if changed_r or changed_g or changed_b:
                        self._ocean_params["shallow_color"] = (float(shr), float(shg), float(shb))
                        self._ocean_app.set_shallow_color(float(shr), float(shg), float(shb))

                    changed, abs_depth = imgui.slider_float(
                        "Absorption depth",
                        float(self._ocean_params.get("absorption_depth", 0.1)),
                        0.0,
                        1.0,
                    )
                    if changed:
                        self._ocean_params["absorption_depth"] = float(abs_depth)
                        self._ocean_app.set_absorption_depth(float(abs_depth))

                if imgui.collapsing_header("Detail Normal##group"):
                    changed, detail_str = imgui.slider_float(
                        "Detail strength",
                        float(self._ocean_params.get("detail_strength", 0.3)),
                        0.0,
                        1.0,
                    )
                    if changed:
                        self._ocean_params["detail_strength"] = float(detail_str)
                        self._ocean_app.set_detail_strength(float(detail_str))

                    changed, detail_scale = imgui.slider_float(
                        "Detail scale",
                        float(self._ocean_params.get("detail_scale", 0.5)),
                        0.01,
                        2.0,
                    )
                    if changed:
                        self._ocean_params["detail_scale"] = float(detail_scale)
                        self._ocean_app.set_detail_scale(float(detail_scale))

                    changed, fade_near = imgui.slider_float(
                        "Fade near",
                        float(self._ocean_params.get("detail_fade_near", 5.0)),
                        0.0,
                        50.0,
                    )
                    if changed:
                        self._ocean_params["detail_fade_near"] = float(fade_near)
                        self._ocean_app.set_detail_fade_near(float(fade_near))

                    changed, fade_far = imgui.slider_float(
                        "Fade far",
                        float(self._ocean_params.get("detail_fade_far", 60.0)),
                        10.0,
                        200.0,
                    )
                    if changed:
                        self._ocean_params["detail_fade_far"] = float(fade_far)
                        self._ocean_app.set_detail_fade_far(float(fade_far))

        # Update once more after building the UI, so the value reflects this frame.
        self.want_capture_mouse = bool(imgui.get_io().want_capture_mouse)

    def toggle(self) -> None:
        """Toggle the ImGui debug overlay."""
        self.enabled = not self.enabled
