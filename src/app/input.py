# -*- coding: utf-8 -*-

"""
Filename: input.py
Author: storro
Date: 2026-02-11
Description: Orbit camera input/controller
"""

from direct.task.Task import Task

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.main import OceanApp


class OrbitCameraController:
    def _imgui_wants_mouse(self) -> bool:
        debug_gui = getattr(self._app, "debug_gui", None)
        return bool(getattr(debug_gui, "want_capture_mouse", False))

    def __init__(
        self,
        app: "OceanApp",
        heading: float = 0.0,
        pitch: float = -25.0,
        distance: float = 300.0,
        min_distance: float = 10.0,
        max_distance: float = 5000.0,
        rotate_speed: float = 180.0,
        pivot_name: str = "orbit_pivot",
        task_name: str = "orbit_camera",
    ) -> None:
        self._app = app

        self._pivot = self._app.render.attach_new_node(pivot_name)
        self._heading = heading
        self._pitch = pitch
        self._distance = distance
        self._min_distance = min_distance
        self._max_distance = max_distance
        self._rotate_speed = rotate_speed

        self._dragging = False
        self._last_mouse = None

        self._app.camera.reparent_to(self._pivot)
        self._apply_camera()

        self._app.accept("mouse1", self._start_drag)
        self._app.accept("mouse1-up", self._stop_drag)
        self._app.accept("wheel_up", self._zoom_in)
        self._app.accept("wheel_down", self._zoom_out)
        self._app.task_mgr.add(self._task, task_name)

    def _apply_camera(self) -> None:
        self._pivot.set_hpr(self._heading, self._pitch, 0.0)
        self._app.camera.set_pos(0.0, -self._distance, 0.0)

    def _start_drag(self) -> None:
        if self._imgui_wants_mouse():
            return
        
        self._dragging = True
        self._last_mouse = None

    def _stop_drag(self) -> None:
        self._dragging = False
        self._last_mouse = None

    def _zoom_in(self) -> None:
        if self._imgui_wants_mouse():
            return
        self._distance = max(self._min_distance, self._distance * 0.9)
        self._apply_camera()

    def _zoom_out(self) -> None:
        if self._imgui_wants_mouse():
            return
        self._distance = min(self._max_distance, self._distance / 0.9)
        self._apply_camera()

    def _task(self, task: Task) -> int:
        if not self._dragging:
            return task.cont

        # If the UI is interacting with the mouse, stop orbiting immediately.
        if self._imgui_wants_mouse():
            self._dragging = False
            self._last_mouse = None
            return task.cont

        # sadly mouse_watcher_node does not exists
        if not self._app.mouseWatcherNode.hasMouse():
            self._last_mouse = None
            return task.cont

        mpos = self._app.mouseWatcherNode.getMouse()  # (-1..1, -1..1)
        if self._last_mouse is None:
            self._last_mouse = (mpos.x, mpos.y)
            return task.cont

        last_x, last_y = self._last_mouse
        dx = mpos.x - last_x
        dy = mpos.y - last_y
        self._last_mouse = (mpos.x, mpos.y)

        self._heading -= dx * self._rotate_speed
        self._pitch -= dy * self._rotate_speed
        self._pitch = max(-89.0, min(-5.0, self._pitch))

        self._apply_camera()
        return task.cont
