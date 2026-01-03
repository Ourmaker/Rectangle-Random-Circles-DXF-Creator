#!/usr/bin/env python3
"""
Rectangle + Random Circles DXF Creator (mm) - Auto-fit with Zoom and Mix
Requires:
    pip install ezdxf
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ezdxf
import sys
import random
import math

CANVAS_BG = "#ffffff"
CANVAS_MIN_W = 800
CANVAS_MIN_H = 600
CANVAS_MARGIN_PX = 24  # margin used when auto-fitting

GRID_MAJOR_MM = 100
GRID_MINOR_MM = 20

class RectangleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rectangle + Random Circles DXF Creator (mm) - Auto-fit + Zoom + Mix")
        self.minsize(CANVAS_MIN_W + 380, CANVAS_MIN_H + 20)

        # Rectangle parameters (mm) - default rectangle 800 x 2000 mm
        self.x0_var = tk.DoubleVar(value=10.0)          # top-left of bounding box in mm
        self.y0_var = tk.DoubleVar(value=10.0)
        self.width_var = tk.DoubleVar(value=800.0)      # width in mm
        self.height_var = tk.DoubleVar(value=2000.0)    # height in mm

        # Circle parameters
        self.circle_diam_var = tk.DoubleVar(value=100.0)  # mm
        self.circle_count_var = tk.IntVar(value=5)
        # Minimum spacing (edge-to-edge) in mm (default 20 mm)
        self.circle_min_spacing_var = tk.DoubleVar(value=20.0)

        # Scaling control
        self.px_per_mm_var = tk.DoubleVar(value=3.0)    # manual pixels per mm (used when auto-fit disabled)
        self.auto_fit_var = tk.BooleanVar(value=True)
        # Zoom multiplier applied on top of computed or manual px/mm
        self.zoom_var = tk.DoubleVar(value=1.0)

        # DXF export options
        self.layer_var = tk.StringVar(value="0")
        self.color_var = tk.IntVar(value=7)

        # internal state
        self.canvas_w = CANVAS_MIN_W
        self.canvas_h = CANVAS_MIN_H

        # store shapes
        self.rect = {
            "x0_mm": float(self.x0_var.get()),
            "y0_mm": float(self.y0_var.get()),
            "w_mm": float(self.width_var.get()),
            "h_mm": float(self.height_var.get()),
        }
        # circles: list of dicts {"cx_mm":..., "cy_mm":..., "d_mm":...}
        self.circles: list[dict] = []

        # Build UI
        self._build_ui()

        # Bind events
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Initial draw (will auto-fit)
        self.redraw()

    def _build_ui(self):
        # Left control panel
        panel = ttk.Frame(self)
        panel.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(panel, text="Rectangle + Circles Creator (mm)", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0,8))

        form = ttk.Frame(panel)
        form.pack(anchor="w", pady=(0,6))

        ttk.Label(form, text="X0 (mm) - top-left:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.x0_var, width=14).grid(row=0, column=1, padx=6, pady=3)

        ttk.Label(form, text="Y0 (mm) - top-left:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.y0_var, width=14).grid(row=1, column=1, padx=6, pady=3)

        ttk.Label(form, text="Width (mm):").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.width_var, width=14).grid(row=2, column=1, padx=6, pady=3)

        ttk.Label(form, text="Height (mm):").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.height_var, width=14).grid(row=3, column=1, padx=6, pady=3)

        # Auto-fit checkbox and px/mm entry
        fit_row = ttk.Frame(panel)
        fit_row.pack(fill="x", pady=(6,6))
        ttk.Checkbutton(fit_row, text="Auto-fit scale to window", variable=self.auto_fit_var, command=self.on_fit_toggle).pack(anchor="w")
        pxrow = ttk.Frame(panel)
        pxrow.pack(fill="x", pady=(2,4))
        ttk.Label(pxrow, text="Pixels per mm (manual):").grid(row=0, column=0, sticky="w")
        self.px_entry = ttk.Entry(pxrow, textvariable=self.px_per_mm_var, width=12)
        self.px_entry.grid(row=0, column=1, padx=6)
        ttk.Label(pxrow, text="(disabled when auto-fit on)").grid(row=0, column=2, padx=6)

        # Zoom controls
        zoom_row = ttk.Frame(panel)
        zoom_row.pack(fill="x", pady=(4,6))
        ttk.Label(zoom_row, text="Zoom:").grid(row=0, column=0, sticky="w")
        ttk.Button(zoom_row, text="+", width=3, command=self.zoom_in).grid(row=0, column=1, padx=(6,2))
        ttk.Button(zoom_row, text="-", width=3, command=self.zoom_out).grid(row=0, column=2, padx=2)
        ttk.Button(zoom_row, text="Reset", width=6, command=self.zoom_reset).grid(row=0, column=3, padx=6)
        self.scale_label = ttk.Label(zoom_row, text="Scale: -- px/mm  (100%)")
        self.scale_label.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6,0))

        ttk.Separator(panel).pack(fill="x", pady=6)

        # Buttons for rectangle
        ttk.Button(panel, text="Update rectangle", command=self.on_update_shape).pack(fill="x", pady=(0,6))
        ttk.Button(panel, text="Reset rectangle to default", command=self.reset_default).pack(fill="x", pady=(0,6))

        ttk.Separator(panel).pack(fill="x", pady=6)

        # Circle controls
        circle_frame = ttk.LabelFrame(panel, text="Random circles (inside rectangle)")
        circle_frame.pack(fill="x", pady=(4,6))
        ttk.Label(circle_frame, text="Diameter (mm):").grid(row=0, column=0, sticky="w", pady=3, padx=4)
        ttk.Entry(circle_frame, textvariable=self.circle_diam_var, width=12).grid(row=0, column=1, padx=4)
        ttk.Label(circle_frame, text="Number:").grid(row=1, column=0, sticky="w", pady=3, padx=4)
        ttk.Entry(circle_frame, textvariable=self.circle_count_var, width=12).grid(row=1, column=1, padx=4)
        ttk.Label(circle_frame, text="Min spacing (mm):").grid(row=2, column=0, sticky="w", pady=3, padx=4)
        ttk.Entry(circle_frame, textvariable=self.circle_min_spacing_var, width=12).grid(row=2, column=1, padx=4)
        ttk.Button(circle_frame, text="Add random circles", command=self.add_random_circles).grid(row=3, column=0, columnspan=2, sticky="we", padx=4, pady=(6,4))
        ttk.Button(circle_frame, text="Clear circles", command=self.clear_circles).grid(row=4, column=0, columnspan=2, sticky="we", padx=4, pady=(2,4))
        ttk.Button(circle_frame, text="Mix circles (reposition)", command=self.mix_circles).grid(row=5, column=0, columnspan=2, sticky="we", padx=4, pady=(2,4))

        ttk.Separator(panel).pack(fill="x", pady=6)

        # DXF options
        dxf_frame = ttk.Frame(panel)
        dxf_frame.pack(fill="x")
        ttk.Label(dxf_frame, text="Layer:").grid(row=0, column=0, sticky="w")
        ttk.Entry(dxf_frame, textvariable=self.layer_var, width=12).grid(row=0, column=1, padx=6)
        ttk.Label(dxf_frame, text="Color idx:").grid(row=1, column=0, sticky="w")
        ttk.Entry(dxf_frame, textvariable=self.color_var, width=12).grid(row=1, column=1, padx=6)

        ttk.Separator(panel).pack(fill="x", pady=8)

        # Prominent green Save DXF button
        # Use a regular tk.Button for consistent background color across platforms.
        self.save_button = tk.Button(panel,
                                     text="Save DXF",
                                     command=self._on_save_button,
                                     bg="#2e7d32",       # green
                                     activebackground="#256028",
                                     fg="white",
                                     activeforeground="white",
                                     font=("Segoe UI", 11, "bold"),
                                     padx=8, pady=6)
        self.save_button.pack(fill="x", pady=(0,8))

        notes = ("Notes:\n- Units are millimetres (mm).\n- X increases to the right, Y increases downward on the canvas.\n- Circles are placed randomly within the rectangle and will respect the minimum spacing (edge-to-edge),\n  including spacing to rectangle edges.\n- Mix will attempt to reposition existing circles (keeping diameters) with the same spacing rule.\n- Save exports mm units and sets INSUNITS to millimetres.")
        ttk.Label(panel, text=notes, wraplength=360).pack(anchor="w", pady=(4,0))

        # Canvas (resizable)
        self.canvas = tk.Canvas(self, bg=CANVAS_BG, highlightthickness=1, highlightbackground="#888")
        self.canvas.pack(side=tk.LEFT, fill="both", expand=True, padx=8, pady=8)

    # -------------------- Events / actions --------------------
    def on_canvas_configure(self, event):
        # canvas resized -> update stored size and redraw (recompute auto-fit if enabled)
        self.canvas_w = max(1, event.width)
        self.canvas_h = max(1, event.height)
        self.redraw()

    def on_fit_toggle(self):
        # disable/enable px_per_mm entry depending on auto-fit
        if self.auto_fit_var.get():
            self.px_entry.state(["disabled"])
        else:
            self.px_entry.state(["!disabled"])
        self.redraw()

    def on_update_shape(self):
        # validate and update rectangle params from entries
        try:
            x0 = float(self.x0_var.get())
            y0 = float(self.y0_var.get())
            w = float(self.width_var.get())
            h = float(self.height_var.get())
            if w <= 0 or h <= 0:
                raise ValueError("Width and Height must be > 0.")
        except Exception as e:
            messagebox.showerror("Invalid input", f"Please enter valid numeric values:\n{e}")
            return

        self.rect = {"x0_mm": x0, "y0_mm": y0, "w_mm": w, "h_mm": h}
        self.redraw()

    def reset_default(self):
        # reset to default rectangle and auto-fit
        self.x0_var.set(10.0)
        self.y0_var.set(10.0)
        self.width_var.set(800.0)
        self.height_var.set(2000.0)
        self.circle_diam_var.set(100.0)
        self.circle_count_var.set(5)
        self.circle_min_spacing_var.set(20.0)
        self.px_per_mm_var.set(3.0)
        self.zoom_var.set(1.0)
        self.auto_fit_var.set(True)
        self.on_fit_toggle()
        self.on_update_shape()
        self.clear_circles()

    def clear_drawing(self):
        # remove rectangle and circles (clear visual overlay but keep params)
        self.canvas.delete("shape")
        self.canvas.delete("overlay")

    # -------------------- Zoom --------------------
    def zoom_in(self):
        cur = float(self.zoom_var.get())
        cur *= 1.2
        self.zoom_var.set(min(cur, 10.0))
        self.redraw()

    def zoom_out(self):
        cur = float(self.zoom_var.get())
        cur /= 1.2
        self.zoom_var.set(max(cur, 0.05))
        self.redraw()

    def zoom_reset(self):
        self.zoom_var.set(1.0)
        self.redraw()

    # -------------------- Circles --------------------
    def clear_circles(self):
        self.circles.clear()
        self.redraw()

    def add_random_circles(self):
        # Read parameters
        try:
            diam = float(self.circle_diam_var.get())
            count = int(self.circle_count_var.get())
            min_space = float(self.circle_min_spacing_var.get())
            if diam <= 0 or count <= 0 or min_space < 0:
                raise ValueError("Diameter and count must be > 0; min spacing must be >= 0.")
        except Exception as e:
            messagebox.showerror("Invalid input", f"Please enter valid numeric values for circles:\n{e}")
            return

        # Ensure rectangle exists and has space (account for min spacing to rectangle edges)
        x0 = self.rect["x0_mm"]
        y0 = self.rect["y0_mm"]
        w = self.rect["w_mm"]
        h = self.rect["h_mm"]
        r = diam / 2.0

        # To keep edge-to-edge spacing >= min_space, center must be >= r + min_space from rectangle edges.
        if w <= 2 * (r + min_space) or h <= 2 * (r + min_space):
            messagebox.showwarning("Too large / spacing too big", "Circle diameter and/or minimum spacing are too large to fit inside the rectangle.")
            return

        placed = 0
        max_attempts_per_circle = 600
        new_circles = []

        for i in range(count):
            placed_this = False
            attempts = 0
            while attempts < max_attempts_per_circle and not placed_this:
                attempts += 1
                cx = random.uniform(x0 + r + min_space, x0 + w - r - min_space)
                cy = random.uniform(y0 + r + min_space, y0 + h - r - min_space)
                # check overlap with existing circles (both previously existing and newly placed)
                ok = True
                for c in self.circles:
                    dist = math.hypot(cx - c["cx_mm"], cy - c["cy_mm"])
                    min_allowed = r + (c["d_mm"] / 2.0) + min_space
                    if dist < min_allowed:
                        ok = False
                        break
                if not ok:
                    continue
                for c in new_circles:
                    dist = math.hypot(cx - c["cx_mm"], cy - c["cy_mm"])
                    min_allowed = r + (c["d_mm"] / 2.0) + min_space
                    if dist < min_allowed:
                        ok = False
                        break
                if ok:
                    new_circles.append({"cx_mm": cx, "cy_mm": cy, "d_mm": diam})
                    placed += 1
                    placed_this = True
            if not placed_this:
                # Could not place this circle without violating spacing after many attempts: stop trying further
                break

        # append new circles to global list and redraw
        self.circles.extend(new_circles)
        self.redraw()

        if placed < count:
            messagebox.showwarning(
                "Placement limited",
                f"Requested {count} circles of Ø{diam} mm with {min_space} mm spacing.\n"
                f"Could place {placed} circles; the rectangle or spacing prevented placing more."
            )
        # else: no popup on success per request

    def mix_circles(self):
        """Reposition already created circles (keep diameters)."""
        if not self.circles:
            # no popup necessary
            return

        # Extract diameters (keep count)
        diameters = [c["d_mm"] for c in self.circles]
        # Sort descending to place large ones first (better packing)
        diameters.sort(reverse=True)

        # Attempt to place same number of circles with same diameters
        x0 = self.rect["x0_mm"]
        y0 = self.rect["y0_mm"]
        w = self.rect["w_mm"]
        h = self.rect["h_mm"]
        min_space = float(self.circle_min_spacing_var.get())

        new_circles: list[dict] = []
        max_attempts_per_circle = 800
        placed = 0

        for diam in diameters:
            r = diam / 2.0
            # require room within rectangle considering min spacing to edges
            if w <= 2 * (r + min_space) or h <= 2 * (r + min_space):
                # cannot place this diameter at all; skip it
                continue
            placed_this = False
            attempts = 0
            while attempts < max_attempts_per_circle and not placed_this:
                attempts += 1
                cx = random.uniform(x0 + r + min_space, x0 + w - r - min_space)
                cy = random.uniform(y0 + r + min_space, y0 + h - r - min_space)
                ok = True
                # check with already placed new circles
                for c in new_circles:
                    dist = math.hypot(cx - c["cx_mm"], cy - c["cy_mm"])
                    min_allowed = r + (c["d_mm"] / 2.0) + min_space
                    if dist < min_allowed:
                        ok = False
                        break
                if ok:
                    new_circles.append({"cx_mm": cx, "cy_mm": cy, "d_mm": diam})
                    placed += 1
                    placed_this = True
            # if not placed_this -> skip this diameter and continue with others

        old_count = len(self.circles)
        self.circles = new_circles
        self.redraw()

        if placed < old_count:
            messagebox.showwarning(
                "Mix limited",
                f"Tried to reposition {old_count} circles.\n"
                f"Successfully placed {placed}. Some could not be placed due to spacing/space limits."
            )
        # else: no popup on success per request

    # -------------------- Drawing helpers --------------------
    def compute_px_per_mm_and_offset(self):
        """
        Compute effective px_per_mm and x_offset_px,y_offset_px mapping from model mm coords to canvas px.
        Applies zoom multiplier on top of computed or manual px/mm.
        Returns: effective_px_per_mm, x_offset_px, y_offset_px, bbox_min_x, bbox_min_y
        """
        zoom = float(self.zoom_var.get())
        # get bounding box of rectangle in mm
        x0 = self.rect["x0_mm"]
        y0 = self.rect["y0_mm"]
        w = self.rect["w_mm"]
        h = self.rect["h_mm"]
        min_x = x0
        max_x = x0 + w
        min_y = y0
        max_y = y0 + h
        width_mm = max_x - min_x
        height_mm = max_y - min_y
        width_mm = max(width_mm, 1e-6)
        height_mm = max(height_mm, 1e-6)

        if self.auto_fit_var.get():
            avail_w = max(1, self.canvas_w - 2 * CANVAS_MARGIN_PX)
            avail_h = max(1, self.canvas_h - 2 * CANVAS_MARGIN_PX)
            base_px_per_mm_x = avail_w / width_mm
            base_px_per_mm_y = avail_h / height_mm
            base_px_per_mm = min(base_px_per_mm_x, base_px_per_mm_y)
            if base_px_per_mm <= 0:
                base_px_per_mm = 1.0
            effective_px_per_mm = base_px_per_mm * zoom
            x_offset_px = CANVAS_MARGIN_PX - (min_x * effective_px_per_mm)
            y_offset_px = CANVAS_MARGIN_PX - (min_y * effective_px_per_mm)
            return effective_px_per_mm, x_offset_px, y_offset_px, min_x, min_y
        else:
            try:
                manual_px = float(self.px_per_mm_var.get())
                if manual_px <= 0:
                    raise ValueError
            except Exception:
                manual_px = 1.0
                self.px_per_mm_var.set(manual_px)
            effective_px_per_mm = manual_px * zoom
            x_offset_px = 0.0
            y_offset_px = 0.0
            return effective_px_per_mm, x_offset_px, y_offset_px, 0.0, 0.0

    def mm_to_canvas_px(self, x_mm, y_mm, px_per_mm, x_offset_px, y_offset_px):
        x_px = x_mm * px_per_mm + x_offset_px
        y_px = y_mm * px_per_mm + y_offset_px
        return x_px, y_px

    def update_scale_label(self, effective_px_per_mm):
        try:
            zoom_pct = int(round(self.zoom_var.get() * 100))
        except Exception:
            zoom_pct = 100
        try:
            eff = float(effective_px_per_mm)
            text = f"Scale: {eff:.3f} px/mm  ({zoom_pct}%)"
        except Exception:
            text = f"Scale: -- px/mm  ({zoom_pct}%)"
        self.scale_label.config(text=text)

    def redraw(self):
        """Redraw grid, axes, rectangle and the circles according to current parameters and scale."""
        self.canvas.delete("overlay")
        self.canvas.delete("shape")

        px_per_mm, x_off, y_off, bbox_min_x, bbox_min_y = self.compute_px_per_mm_and_offset()
        self.update_scale_label(px_per_mm)

        try:
            px_per_mm_f = float(px_per_mm)
            if px_per_mm_f <= 0:
                px_per_mm_f = 1.0
        except Exception:
            px_per_mm_f = 1.0

        # draw minor grid
        minor_step_px = GRID_MINOR_MM * px_per_mm_f
        if minor_step_px >= 4:
            x = 0.0
            while x <= self.canvas_w:
                self.canvas.create_line(x, 0, x, self.canvas_h, fill="#f7f7f7", tags="overlay")
                x += minor_step_px
            y = 0.0
            while y <= self.canvas_h:
                self.canvas.create_line(0, y, self.canvas_w, y, fill="#f7f7f7", tags="overlay")
                y += minor_step_px

        # major grid
        major_step_px = GRID_MAJOR_MM * px_per_mm_f
        x = 0.0
        while x <= self.canvas_w:
            self.canvas.create_line(x, 0, x, self.canvas_h, fill="#e8e8e8", tags="overlay")
            mm_val = (x - x_off) / px_per_mm_f
            if -10000 < mm_val < 10000:
                self.canvas.create_text(x + 2, 2, text=f"{int(round(mm_val))}", anchor="nw", fill="#666", font=("Arial", 8), tags="overlay")
            x += major_step_px
        y = 0.0
        while y <= self.canvas_h:
            self.canvas.create_line(0, y, self.canvas_w, y, fill="#e8e8e8", tags="overlay")
            mm_val = (y - y_off) / px_per_mm_f
            if -10000 < mm_val < 10000:
                self.canvas.create_text(2, y + 2, text=f"{int(round(mm_val))}", anchor="nw", fill="#666", font=("Arial", 8), tags="overlay")
            y += major_step_px

        # axis arrows
        ox_px, oy_px = 12, 12
        arrow_len_px = min(120, int(40 * px_per_mm_f))
        self.canvas.create_line(ox_px, oy_px, ox_px + arrow_len_px, oy_px, arrow=tk.LAST, width=2, fill="#111", tags="overlay")
        self.canvas.create_text(ox_px + arrow_len_px + 6, oy_px - 6, text="+X", anchor="nw", font=("Arial", 10, "bold"), tags="overlay")
        self.canvas.create_line(ox_px, oy_px, ox_px, oy_px + arrow_len_px, arrow=tk.LAST, width=2, fill="#111", tags="overlay")
        self.canvas.create_text(ox_px + 6, oy_px + arrow_len_px + 2, text="+Y", anchor="nw", font=("Arial", 10, "bold"), tags="overlay")
        self.canvas.create_text(ox_px + 6, oy_px + 10, text="(0,0)", anchor="nw", font=("Arial", 9), tags="overlay")

        # draw rectangle
        x0 = self.rect["x0_mm"]
        y0 = self.rect["y0_mm"]
        w = self.rect["w_mm"]
        h = self.rect["h_mm"]

        # corners in model mm (top-left origin)
        p1 = (x0, y0)          # top-left
        p2 = (x0 + w, y0)      # top-right
        p3 = (x0 + w, y0 + h)  # bottom-right
        p4 = (x0, y0 + h)      # bottom-left
        pts_mm = [p1, p2, p3, p4]

        pts_px = [self.mm_to_canvas_px(px, py, px_per_mm_f, x_off, y_off) for (px, py) in pts_mm]
        flat = [coord for p in pts_px for coord in p]

        # draw rectangle as polygon
        self.canvas.create_polygon(flat, outline="#000", fill="#cfe8ff", width=1.5, tags="shape")
        bbox_tl_px = self.mm_to_canvas_px(x0, y0, px_per_mm_f, x_off, y_off)
        lbl = f"W={w} mm  H={h} mm"
        self.canvas.create_text(bbox_tl_px[0] + 6, bbox_tl_px[1] + 6, text=lbl, anchor="nw", fill="#003366", font=("Arial", 10, "bold"), tags="shape")

        # draw circles
        for c in self.circles:
            cx_mm = c["cx_mm"]
            cy_mm = c["cy_mm"]
            d_mm = c["d_mm"]
            r_mm = d_mm / 2.0
            # convert center to px
            cx_px, cy_px = self.mm_to_canvas_px(cx_mm, cy_mm, px_per_mm_f, x_off, y_off)
            r_px = r_mm * px_per_mm_f
            self.canvas.create_oval(cx_px - r_px, cy_px - r_px, cx_px + r_px, cy_px + r_px,
                                    outline="#900", fill="#ffdfdf", width=1.2, tags="shape")
            # label diameter
            self.canvas.create_text(cx_px + 4, cy_px - 4, text=f"Ø{int(round(d_mm))}mm", anchor="nw", font=("Arial", 8), tags="shape")

        if self.auto_fit_var.get():
            self.px_entry.state(["disabled"])
        else:
            self.px_entry.state(["!disabled"])

    # -------------------- DXF export --------------------
    def _on_save_button(self):
        # disable button while saving to avoid duplicate presses
        try:
            self.save_button.config(state="disabled", text="Saving...")
            self.update_idletasks()
            self.save_dxf()
        finally:
            self.save_button.config(state="normal", text="Save DXF")

    def save_dxf(self):
        try:
            x0 = float(self.rect["x0_mm"])
            y0 = float(self.rect["y0_mm"])
            w = float(self.rect["w_mm"])
            h = float(self.rect["h_mm"])
        except Exception:
            messagebox.showerror("Error", "Rectangle parameters invalid.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".dxf", filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")])
        if not path:
            return
        try:
            doc = ezdxf.new(dxfversion="R2010")
            try:
                doc.header["$INSUNITS"] = 4
            except Exception:
                pass
            msp = doc.modelspace()
            layer_name = self.layer_var.get() or "0"
            color = int(self.color_var.get()) if self.color_var.get() else 7
            if layer_name not in doc.layers:
                doc.layers.new(name=layer_name, dxfattribs={"color": color})

            # Rectangle points in model mm
            p1 = (x0, y0)
            p2 = (x0 + w, y0)
            p3 = (x0 + w, y0 + h)
            p4 = (x0, y0 + h)
            pts_model = [p1, p2, p3, p4]

            # To flip Y for DXF (so Y is up), compute canvas height in mm using the effective px_per_mm
            effective_px_per_mm, x_off, y_off, bbox_min_x, bbox_min_y = self.compute_px_per_mm_and_offset()
            try:
                canvas_h_mm = self.canvas_h / effective_px_per_mm
            except Exception:
                canvas_h_mm = float(self.canvas_h)

            # convert rectangle corners to DXF coords
            pts_dxf = [(float(px), float(canvas_h_mm - py)) for (px, py) in pts_model]
            msp.add_lwpolyline(pts_dxf, close=True, dxfattribs={"layer": layer_name, "color": color})

            # add circles as DXF CIRCLE (center x, flipped y, radius in mm)
            for c in self.circles:
                cx = float(c["cx_mm"])
                cy = float(c["cy_mm"])
                r = float(c["d_mm"]) / 2.0
                dxf_center = (cx, float(canvas_h_mm - cy))
                msp.add_circle(dxf_center, r, dxfattribs={"layer": layer_name, "color": color})

            doc.saveas(path)
            messagebox.showinfo("Saved", f"Saved DXF (mm) to: {path}")
        except Exception as e:
            messagebox.showerror("Save error", f"Failed to save DXF: {e}")

def main():
    try:
        app = RectangleApp()
        app.mainloop()
    except Exception as e:
        print("Fatal error:", e, file=sys.stderr)

if __name__ == "__main__":
    main()
