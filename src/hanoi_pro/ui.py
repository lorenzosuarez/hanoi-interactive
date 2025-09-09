#!/usr/bin/env python3
"""
Professional Tower of Hanoi — Interactive Visual Analytics
==========================================================

Author
------
Lorenzo Suarez — September 9, 2025

Abstract
--------
An interactive Tower of Hanoi system that merges legality-preserving manual manipulation with
a shortest-path planner capable of resuming and completing the puzzle from any reachable state.
The interface is intentionally minimal: four primary controls and one interval slider, backed
by keyboard shortcuts, with rendering guarantees for full disk visibility across scales.

System Model
------------
Configurations are vectors in {0,1,2}^n where coordinate i encodes the peg of disk i (1 is the
smallest). Legal transitions modify exactly one coordinate subject to the stack partial order.
A breadth-first search over the legal state graph produces shortest completion plans. The
distance-to-go is cached and recomputed only on state changes.

Interaction
-----------
Drag the top disk to a target peg; legal targets are highlighted. Controls:
• Play/Pause (auto-run using the current interval)
• Step (single optimal move)
• Undo
• Reset
Shortcuts: Space = Play/Pause, Enter = Step, U/Backspace = Undo, R = Reset, Esc = Pause.

Rendering Guarantees
--------------------
Axis limits are derived from disk geometry with explicit margins to ensure that no disk is
clipped. Disks render as rounded boxes with anti-aliased edges and centered labels. The drag
overlay snaps horizontally to the nearest peg for precision.

Requirements
------------
Python 3.8+, matplotlib.
"""

from __future__ import annotations

import argparse
import collections
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.widgets import Button, Slider


@dataclass(frozen=True)
class Move:
    """
    Immutable move descriptor.
    
    Attributes
    ----------
    disk : int
        Disk identifier with 1 denoting the smallest.
    src : int
        Source peg index in {0,1,2}.
    dst : int
        Destination peg index in {0,1,2}.
    """
    disk: int
    src: int
    dst: int


class HanoiModel:
    """
    Logical transition system and invariants for Tower of Hanoi.
    
    Parameters
    ----------
    n : int
        Number of disks, n ≥ 1.
    """
    def __init__(self, n: int) -> None:
        if n < 1:
            raise ValueError("n must be >= 1")
        self.n = n
        self.state: Tuple[int, ...] = tuple([0] * n)

    @staticmethod
    def _top_on(positions: Tuple[int, ...], peg: int) -> Optional[int]:
        """
        Returns
        -------
        Optional[int]
            Index i (0-based) of the smallest disk on the peg (the visible top), or None.
        """
        top: Optional[int] = None
        for i in range(len(positions)):
            if positions[i] == peg:
                top = i if top is None else min(top, i)
        return top

    @staticmethod
    def is_legal_move(positions: Tuple[int, ...], mv: Move) -> bool:
        """
        Returns
        -------
        bool
            True iff mv is a legal transition for positions.
        """
        if mv.src == mv.dst:
            return False
        top = HanoiModel._top_on(positions, mv.src)
        if top is None or (top + 1) != mv.disk:
            return False
        dest_top = HanoiModel._top_on(positions, mv.dst)
        return dest_top is None or dest_top > top

    @staticmethod
    def apply(positions: Tuple[int, ...], mv: Move) -> Tuple[int, ...]:
        """
        Returns
        -------
        Tuple[int, ...]
            New positions after applying a legal move.
        """
        if not HanoiModel.is_legal_move(positions, mv):
            raise ValueError("Illegal move")
        lst = list(positions)
        lst[mv.disk - 1] = mv.dst
        return tuple(lst)

    @staticmethod
    def legal_moves(positions: Tuple[int, ...]) -> List[Move]:
        """
        Returns
        -------
        List[Move]
            All legal single-disk moves from positions.
        """
        res: List[Move] = []
        for s in range(3):
            top = HanoiModel._top_on(positions, s)
            if top is None:
                continue
            dsk = top + 1
            for d in range(3):
                if d == s:
                    continue
                dest_top = HanoiModel._top_on(positions, d)
                if dest_top is None or dest_top > top:
                    res.append(Move(dsk, s, d))
        return res

    @staticmethod
    def bfs_shortest_path(start: Tuple[int, ...], goal: Tuple[int, ...]) -> Deque[Move]:
        """
        Returns
        -------
        Deque[Move]
            A shortest legal move sequence from start to goal via BFS.
        """
        if start == goal:
            return collections.deque()
        q: Deque[Tuple[int, ...]] = collections.deque([start])
        prev: Dict[Tuple[int, ...], Tuple[Tuple[int, ...], Move]] = {}
        seen = {start}
        while q:
            cur = q.popleft()
            for mv in HanoiModel.legal_moves(cur):
                nxt = HanoiModel.apply(cur, mv)
                if nxt in seen:
                    continue
                prev[nxt] = (cur, mv)
                if nxt == goal:
                    path: Deque[Move] = collections.deque()
                    s = nxt
                    while s != start:
                        p, m = prev[s]
                        path.appendleft(m)
                        s = p
                    return path
                seen.add(nxt)
                q.append(nxt)
        raise RuntimeError("State space disconnected")


class HanoiUI:
    """
    Minimal-control interactive UI with optimal resume and interval-accurate auto-run.
    
    Parameters
    ----------
    n : int
        Number of disks.
    goal_peg : int
        Target peg index in {0,1,2}.
    """
    def __init__(self, n: int, goal_peg: int = 2) -> None:
        self.n = n
        self.model = HanoiModel(n)
        self.goal_peg = goal_peg
        mpl.rcParams['figure.dpi'] = 120
        self.fig, self.ax = plt.subplots(figsize=(12.5, 7.5))
        plt.subplots_adjust(bottom=0.20, top=0.90)
        self._peg_x = [2.5, 6.25, 10.0]
        self._base_y = 0.9
        self._disk_h = max(0.22, 4.8 / max(3, n))
        self._timer = self.fig.canvas.new_timer(interval=600)
        self._timer.add_callback(self._on_timer)
        self._auto = False
        self._plan: Optional[Deque[Move]] = None
        self._history: List[Move] = []
        self._remain_cache: Optional[int] = None
        self._drag_active = False
        self._drag_disk: Optional[int] = None
        self._drag_src: Optional[int] = None
        self._hover_x: Optional[float] = None
        self._build_widgets()
        self.fig.canvas.mpl_connect("button_press_event", self._on_press)
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)
        self._render()

    def _build_widgets(self) -> None:
        """
        Constructs a compact control bar: Play/Pause, Step, Undo, Reset, and an interval slider.
        """
        ax_run = plt.axes([0.09, 0.09, 0.18, 0.08])
        ax_step = plt.axes([0.29, 0.09, 0.18, 0.08])
        ax_undo = plt.axes([0.49, 0.09, 0.18, 0.08])
        ax_reset = plt.axes([0.69, 0.09, 0.18, 0.08])
        ax_speed = plt.axes([0.09, 0.02, 0.78, 0.05])

        self.btn_run = Button(ax_run, "Play/Pause ␣")
        self.btn_step = Button(ax_step, "Step ⏎")
        self.btn_undo = Button(ax_undo, "Undo ⌫")
        self.btn_reset = Button(ax_reset, "Reset R")
        self.sld_speed = Slider(ax_speed, "Interval (s)", 0.05, 3.0, valinit=0.6, valfmt="%.2f")

        self.btn_run.on_clicked(lambda _: self.toggle_run())
        self.btn_step.on_clicked(lambda _: self.step_optimal())
        self.btn_undo.on_clicked(lambda _: self.undo())
        self.btn_reset.on_clicked(lambda _: self.reset())
        self.sld_speed.on_changed(self._on_speed_change)

    def _on_key(self, event) -> None:
        """
        Keyboard handler matching the minimal control set.
        """
        k = (event.key or "").lower()
        if k == " ":
            self.toggle_run()
        elif k == "enter":
            self.step_optimal()
        elif k in ("u", "backspace"):
            self.undo()
        elif k == "r":
            self.reset()
        elif k == "escape":
            self.pause()

    def _on_speed_change(self, val: float) -> None:
        """
        Updates the auto-run timer to respect the current interval exactly.
        """
        self._timer.interval = int(float(val) * 1000)

    def toggle_run(self) -> None:
        """
        Toggles interval-accurate automated playback from the current state.
        """
        if self._auto:
            self.pause()
        else:
            self.start()

    def start(self) -> None:
        """
        Starts auto-run using the optimal plan and the current slider interval.
        """
        if self._plan is None:
            self._plan = self._plan_to_goal()
        if not self._plan:
            return
        self._auto = True
        self._timer.start()

    def pause(self) -> None:
        """
        Pauses auto-run without altering state.
        """
        self._auto = False
        self._timer.stop()

    def reset(self) -> None:
        """
        Restores the initial configuration and clears history and plans.
        """
        self.pause()
        self.model = HanoiModel(self.n)
        self._history.clear()
        self._plan = None
        self._remain_cache = None
        self._render()

    def undo(self) -> None:
        """
        Reverts the last executed move, if any, and invalidates cached plans.
        """
        if not self._history:
            return
        last = self._history.pop()
        inv = Move(last.disk, last.dst, last.src)
        self.model.state = HanoiModel.apply(self.model.state, inv)
        self._plan = None
        self._remain_cache = None
        self._render()

    def step_optimal(self) -> None:
        """
        Executes a single optimal step from the current configuration.
        """
        self._advance_plan_single()

    def _plan_to_goal(self) -> Deque[Move]:
        """
        Returns
        -------
        Deque[Move]
            A shortest plan from the current state to the goal peg.
        """
        goal = tuple([self.goal_peg] * self.n)
        path = HanoiModel.bfs_shortest_path(self.model.state, goal)
        self._remain_cache = len(path)
        return path

    def _advance_plan_single(self) -> bool:
        """
        Advances by one move in the plan, recomputing as needed.
        
        Returns
        -------
        bool
            True if a move was executed; False if already solved.
        """
        if self._plan is None or not self._plan:
            self._plan = self._plan_to_goal()
            if not self._plan:
                self._render()
                return False
        mv = self._plan.popleft()
        self.model.state = HanoiModel.apply(self.model.state, mv)
        self._history.append(mv)
        if self._remain_cache is not None and self._remain_cache > 0:
            self._remain_cache -= 1
        self._render()
        return True

    def _on_timer(self) -> None:
        """
        Timer callback; schedules the next tick strictly after the configured interval.
        """
        if not self._auto:
            return
        progressed = self._advance_plan_single()
        if progressed and self._auto:
            self._timer.start()

    def _peg_from_x(self, x: float) -> Optional[int]:
        """
        Maps an x-coordinate to the nearest peg index.
        """
        if x is None:
            return None
        dists = [abs(x - px) for px in self._peg_x]
        return int(min(range(3), key=lambda i: dists[i]))

    def _on_press(self, event) -> None:
        """
        Mouse press handler initiating a drag for the top disk when available.
        """
        if event.inaxes != self.ax:
            return
        peg = self._peg_from_x(event.xdata)
        if peg is None:
            return
        top = HanoiModel._top_on(self.model.state, peg)
        if top is None:
            return
        self._drag_active = True
        self._drag_disk = top + 1
        self._drag_src = peg
        self._hover_x = event.xdata
        self._render()

    def _on_motion(self, event) -> None:
        """
        Mouse motion handler updating the drag overlay.
        """
        if not self._drag_active or event.inaxes != self.ax:
            return
        self._hover_x = event.xdata
        self._render()

    def _on_release(self, event) -> None:
        """
        Mouse release handler applying a legal drag, if any, and invalidating cached plans.
        """
        if not self._drag_active:
            return
        dest = self._peg_from_x(event.xdata) if event.inaxes == self.ax else None
        self._drag_active = False
        if self._drag_disk is not None and self._drag_src is not None and dest is not None:
            mv = Move(self._drag_disk, self._drag_src, dest)
            if HanoiModel.is_legal_move(self.model.state, mv):
                self.model.state = HanoiModel.apply(self.model.state, mv)
                self._history.append(mv)
                self._plan = None
                self._remain_cache = None
        self._drag_disk = None
        self._drag_src = None
        self._hover_x = None
        self._render()

    def _draw_disk(self, x_center: float, y: float, w: float, h: float, label: str, alpha: float = 1.0) -> None:
        """
        Renders a rounded disk with centered label.
        """
        patch = FancyBboxPatch((x_center - w / 2, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
                               linewidth=1.0, antialiased=True, alpha=alpha)
        self.ax.add_patch(patch)
        self.ax.text(x_center, y + h / 2, label, ha="center", va="center", fontsize=10)

    def _compute_limits(self, width_map: Dict[int, float]) -> Tuple[float, float, float, float]:
        """
        Computes axis limits that guarantee full visibility based on geometry.
        """
        w_max = width_map[self.n]
        x_min = min(self._peg_x)
        x_max = max(self._peg_x)
        pad_x = 0.8 + 0.5 * (w_max / 4.0)
        y_top_stack = self._base_y + self._disk_h * self.n + 0.6
        pad_y_top = 0.9
        pad_y_bottom = 0.6
        x0 = x_min - w_max / 2 - pad_x
        x1 = x_max + w_max / 2 + pad_x
        y0 = max(0.1, self._base_y - pad_y_bottom)
        y1 = y_top_stack + pad_y_top
        return x0, x1, y0, y1

    def _render(self) -> None:
        """
        Renders the scene and HUD with minimal visual noise and no clipping.
        """
        self.ax.clear()
        width_map = {i: 1.8 + 0.7 * (i - 1) for i in range(1, self.n + 1)}
        x0, x1, y0, y1 = self._compute_limits(width_map)
        self.ax.set_xlim(x0, x1)
        self.ax.set_ylim(y0, y1)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.ax.plot([self._peg_x[0] - 2.2, self._peg_x[2] + 2.2], [self._base_y, self._base_y], linewidth=3)
        for i, px in enumerate(self._peg_x):
            self.ax.plot([px, px], [self._base_y, y1 - 0.7], linewidth=2.8, alpha=0.9)
            self.ax.text(px, self._base_y - 0.28, "ABC"[i], ha="center", va="top", fontsize=12)

        stacks = self._stacks(self.model.state)
        for peg_idx, stack in enumerate(stacks):
            for level, disk in enumerate(stack):
                y = self._base_y + self._disk_h * level + 0.09
                x_center = self._peg_x[peg_idx]
                w = width_map[disk]
                self._draw_disk(x_center, y, w, self._disk_h, str(disk))

        if self._drag_active and self._drag_disk is not None:
            px = self._peg_x[self._peg_from_x(self._hover_x)]
            w = width_map[self._drag_disk]
            y = y1 - self._disk_h - 0.25
            self._draw_disk(px, y, w, self._disk_h, str(self._drag_disk), alpha=0.7)
            for d in range(3):
                mv = Move(self._drag_disk, self._drag_src, d)
                if HanoiModel.is_legal_move(self.model.state, mv):
                    self.ax.plot([self._peg_x[d], self._peg_x[d]], [self._base_y, y1 - 0.7], linewidth=4.2, alpha=0.28)

        title = self._title_text()
        self.ax.set_title(title, fontsize=15)
        self.fig.canvas.draw_idle()

    def _title_text(self) -> str:
        """
        Returns a concise HUD title with executed steps and cached remaining distance.
        """
        if self._remain_cache is None:
            goal = tuple([self.goal_peg] * self.n)
            self._remain_cache = len(HanoiModel.bfs_shortest_path(self.model.state, goal))
        return f"Tower of Hanoi — n={self.n} | steps={len(self._history)} | remaining≈{self._remain_cache}"

    @staticmethod
    def _stacks(positions: Tuple[int, ...]) -> List[List[int]]:
        """
        Returns
        -------
        List[List[int]]
            Peg-wise stacks from bottom to top as disk labels.
        """
        pegs: List[List[int]] = [[], [], []]
        for dsk in range(len(positions), 0, -1):
            peg = positions[dsk - 1]
            pegs[peg].append(dsk)
        return pegs


def main(argv: Optional[Iterable[str]] = None) -> None:
    """
    Entry point.
    """
    parser = argparse.ArgumentParser(description="Professional Tower of Hanoi — Interactive")
    parser.add_argument("--disks", type=int, default=5, help="Number of disks (n ≥ 1)")
    args = parser.parse_args(list(argv) if argv is not None else None)
    ui = HanoiUI(args.disks)
    plt.show()


if __name__ == "__main__":
    main()