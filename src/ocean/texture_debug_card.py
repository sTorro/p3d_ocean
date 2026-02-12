# -*- coding: utf-8 -*-

"""
Filename: texture_debug_card.py
Author: storro
Date: 2026-02-11
Description: Utility for displaying a texture on a card in the scene for debugging purposes.
"""


from panda3d.core import CardMaker, NodePath, Shader, Texture, TransparencyAttrib

from src.util.assets_path import assets_path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


class TextureDebugCard:
    @staticmethod
    def attach(
        app: "OceanApp",
        tex: Texture,
        gain: float = 2000.0,
        pos: tuple[float, float] = (-1.0, 0.7),
        size: tuple[float, float] = (0.5, 0.5),
        anchor: str = "top_left",
        label_text: str = "",
    ) -> NodePath:
        """
        Attach a card to the aspect2d layer that displays the given texture for debugging purposes
        """

        cm = CardMaker("tex_debug")
        width, height = size

        left: float
        right: float
        bottom: float
        top: float

        if anchor == "top_right":
            margin_x, margin_y = pos
            left, right, bottom, top = (-margin_x - width, -margin_x, -margin_y - height, -margin_y)
            cm.set_frame(left, right, bottom, top)
            card = NodePath(cm.generate())
            card.reparent_to(app.a2dTopRight)
        elif anchor == "bottom_right":
            margin_x, margin_y = pos
            left, right, bottom, top = (-margin_x - width, -margin_x, margin_y, margin_y + height)
            cm.set_frame(left, right, bottom, top)
            card = NodePath(cm.generate())
            card.reparent_to(app.a2dBottomRight)
        else:
            left, bottom = pos
            left, right, bottom, top = (left, left + width, bottom, bottom + height)
            cm.set_frame(left, right, bottom, top)
            card = NodePath(cm.generate())
            card.reparent_to(app.aspect2d)

        card.set_texture(tex)

        shader = Shader.load(
            Shader.SL_GLSL,
            assets_path("shaders", "debug_tex.vert.glsl"),
            assets_path("shaders", "debug_tex.frag.glsl")
        )
        card.set_shader(shader)
        card.set_shader_input("u_gain", float(gain))
        card.set_shader_input("u_mode", 0)

        card.set_bin("fixed", 100)
        card.set_depth_test(False)
        card.set_depth_write(False)
        card.set_transparency(TransparencyAttrib.M_none)

        return card


def attach_texture_debug_card(*args, **kwargs) -> NodePath:
    return TextureDebugCard.attach(*args, **kwargs)
