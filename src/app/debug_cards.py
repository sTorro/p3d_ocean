# -*- coding: utf-8 -*-

"""
Filename: debug_cards.py
Author: storro
Date: 2026-02-11
Description: Debug card visualization + hotkeys.
"""

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

from src.ocean.texture_debug_card import attach_texture_debug_card

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


class DebugCardController:
    def __init__(
        self,
        app: "OceanApp",
        initial_spectrum_tex,
        ocean_time,
        ocean_maps,
    ) -> None:
        self._app = app
        self._initial_spectrum_tex = initial_spectrum_tex
        self._ocean_time = ocean_time
        self._ocean_maps = ocean_maps

        self._debug_mode = 0
        self._debug_visible = False

        self._debug_card = attach_texture_debug_card(
            self._app,
            initial_spectrum_tex,
            gain=2000.0,
            pos=(0.03, 0.06),
            anchor="bottom_right",
            label_text="Initial spectrum",
        )
        self._debug_card.set_shader_input("u_mode", 0)

        debug_margin_x, debug_margin_y = (0.03, 0.06)
        debug_width, debug_height = (0.5, 0.5)
        debug_label_offset = 0.02

        self._debug_label = OnscreenText(
            text="Initial spectrum",
            parent=self._app.a2dBottomRight,
            pos=(-debug_margin_x - debug_width, debug_margin_y + debug_height + debug_label_offset),
            align=TextNode.A_left,
            scale=0.05,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 1),
            mayChange=True,
        )
        self._debug_label.hide()
        self._debug_card.hide()

        self._app.accept("d", self.cycle)
        self._app.accept("c", self.toggle)

        self._create_help_text()

    def _create_help_text(self) -> None:
        help_text = (
            "F1: show/hide imgui\n"
            "c: show/hide debug card\n"
            "d: cycle debug view\n"
            "w: toggle wireframe\n"
            "mouse drag: orbit camera\n"
            "mouse wheel: zoom"
        )
        OnscreenText(
            text=help_text,
            parent=self._app.a2dTopLeft,
            pos=(0.03, -0.06),
            align=TextNode.A_left,
            scale=0.05,
            fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 1),
            mayChange=False,
        )

    def _set_label(self, text: str) -> None:
        if hasattr(self._debug_label, "setText"):
            self._debug_label.setText(text)

    def toggle(self) -> None:
        self._debug_visible = not self._debug_visible
        if self._debug_visible:
            self._debug_card.show()
            self._debug_label.show()
        else:
            self._debug_card.hide()
            self._debug_label.hide()

    def cycle(self) -> None:
        if not self._debug_visible:
            return

        # 0: initial spectrum, 1: phases, 2: time spectrum, 3: displacement, 4: slope/normal map
        self._debug_mode = (self._debug_mode + 1) % 5

        if self._debug_mode == 0:
            self._debug_card.set_texture(self._initial_spectrum_tex)
            self._debug_card.set_shader_input("u_gain", 2000.0)
            self._debug_card.set_shader_input("u_mode", 0)
            self._set_label("Initial spectrum")
        elif self._debug_mode == 1:
            phase_tex = self._ocean_time.debug_current_phase_texture()
            self._debug_card.set_texture(phase_tex)
            self._debug_card.set_shader_input("u_gain", 2000.0)
            self._debug_card.set_shader_input("u_mode", 3)
            self._set_label("Phase")
        elif self._debug_mode == 2:
            self._debug_card.set_texture(self._ocean_time.spectrum)
            self._debug_card.set_shader_input("u_gain", 2000.0)
            self._debug_card.set_shader_input("u_mode", 1)
            self._set_label("Time spectrum")
        elif self._debug_mode == 3:
            self._debug_card.set_texture(self._ocean_maps.displacement_map)
            self._debug_card.set_shader_input("u_gain", 10.0)
            self._debug_card.set_shader_input("u_mode", 4)
            self._set_label("Displacement (height)")
        else:
            self._debug_card.set_texture(self._ocean_maps.slope_map)
            self._debug_card.set_shader_input("u_gain", 1.0)
            self._debug_card.set_shader_input("u_mode", 5)
            self._set_label("Normal map")
