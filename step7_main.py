import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import math

class StickerTool:
    # STEP 1 - BUILD THE TWO-PAGE INTERFACE
    def __init__(self, root):
        self.root = root
        self.root.title("Sticker & Scrapbook Tool")

        self.page_crop = tk.Frame(root)
        self.page_scrapbook = tk.Frame(root)

        nav_frame = tk.Frame(root)
        nav_frame.pack(fill=tk.X)
        tk.Button(nav_frame, text="Sticker Crop Page", command=self.show_crop_page).pack(side=tk.LEFT, padx=4, pady=3)
        tk.Button(nav_frame, text="Scrapbook Collage Page", command=self.show_scrapbook_page).pack(side=tk.LEFT, padx=4, pady=3)

        # -------------------------- CROP PAGE --------------------------
        self.page_crop.pack()
        self.img_original = None
        self.img_display = None
        self.cropped_base = None
        self.undo_stack = []
        self.free_path = []
        self.drawing = False

        self.canvas_crop = tk.Canvas(self.page_crop, bg="white", width=600, height=500)
        self.canvas_crop.pack(pady=5)

        frame_btn = tk.Frame(self.page_crop)
        frame_btn.pack()
        tk.Button(frame_btn, text="Upload Image", command=self.load_img).grid(row=0, column=0, padx=3)
        tk.Button(frame_btn, text="Crop Shape", command=self.crop_shape).grid(row=0, column=1, padx=3)
        tk.Button(frame_btn, text="Clear Path", command=self.clear_path).grid(row=0, column=2, padx=3)
        tk.Button(frame_btn, text="Low-Poly Filter", command=self.lowpoly_blur).grid(row=0, column=3, padx=3)
        tk.Button(frame_btn, text="Undo Last", command=self.undo_last).grid(row=0, column=4, padx=3)
        tk.Button(frame_btn, text="Save PNG Sticker", command=self.save_sticker).grid(row=0, column=5, padx=3)

        frame_slider = tk.Frame(self.page_crop)
        frame_slider.pack(pady=4)
        self.pixel_slider = tk.Scale(frame_slider, label="Pixelate", from_=1.0, to=8.0, resolution=0.1, orient=tk.HORIZONTAL, length=140, command=self.update_adjust)
        self.pixel_slider.set(1.0)
        self.pixel_slider.grid(row=0, column=0, padx=6)
        self.contrast_slider = tk.Scale(frame_slider, label="Contrast", from_=0.2, to=3.0, resolution=0.05, orient=tk.HORIZONTAL, length=140, command=self.update_adjust)
        self.contrast_slider.set(1.0)
        self.contrast_slider.grid(row=0, column=1, padx=6)
        self.saturation_slider = tk.Scale(frame_slider, label="Saturation", from_=0.0, to=3.0, resolution=0.05, orient=tk.HORIZONTAL, length=140, command=self.update_adjust)
        self.saturation_slider.set(1.0)
        self.saturation_slider.grid(row=0, column=2, padx=6)

        self.canvas_crop.bind("<ButtonPress-1>", self.start_draw)
        self.canvas_crop.bind("<B1-Motion>", self.draw_path)
        self.canvas_crop.bind("<ButtonRelease-1>", self.end_draw)

        # -------------------------- SCRAPBOOK PAGE --------------------------
        self.scrap_sticker_list = []
        self.scrap_text_list = []
        self.dragging_item = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.selected_canvas_id = None
        self.selected_sticker = None

        self.handle_items = []
        self.drag_mode = None
        self.drag_start_mouse_x = 0
        self.drag_start_mouse_y = 0
        self.drag_start_angle = 0.0
        self.drag_start_scale = 1.0
        self.drag_start_center_x = 0
        self.drag_start_center_y = 0

        self.scrap_bg_color = "#fff8e8"
        self.canvas_scrap = tk.Canvas(self.page_scrapbook, bg=self.scrap_bg_color, width=750, height=550)
        self.canvas_scrap.pack(pady=5)

        scrap_control_frame = tk.Frame(self.page_scrapbook)
        scrap_control_frame.pack(pady=3)
        tk.Button(scrap_control_frame, text="Add PNG Sticker", command=self.scrap_import_png).grid(row=0, column=0, padx=2)
        tk.Button(scrap_control_frame, text="Copy Sticker", command=self.scrap_copy_sticker).grid(row=0, column=1, padx=2)
        tk.Button(scrap_control_frame, text="Flip H", command=self.scrap_flip_horizontal).grid(row=0, column=2, padx=2)
        tk.Button(scrap_control_frame, text="Flip V", command=self.scrap_flip_vertical).grid(row=0, column=3, padx=2)
        tk.Button(scrap_control_frame, text="Add Text", command=self.scrap_add_text_dialog).grid(row=0, column=4, padx=2)
        tk.Button(scrap_control_frame, text="Edit Text Style", command=self.scrap_edit_text).grid(row=0, column=5, padx=2)
        tk.Button(scrap_control_frame, text="Change BG Color", command=self.scrap_change_bg_color).grid(row=0, column=6, padx=2)
        tk.Button(scrap_control_frame, text="Delete Selected", command=self.scrap_delete_selected).grid(row=0, column=7, padx=2)
        tk.Button(scrap_control_frame, text="Clear All", command=self.scrap_clear_all).grid(row=0, column=8, padx=2)
        tk.Button(scrap_control_frame, text="Save Scrapbook PNG", command=self.scrap_save).grid(row=0, column=9, padx=2)

        self.canvas_scrap.bind("<ButtonPress-1>", self.scrap_start_drag)
        self.canvas_scrap.bind("<B1-Motion>", self.scrap_do_drag)
        self.canvas_scrap.bind("<ButtonRelease-1>", self.scrap_end_drag)

        self.show_crop_page()

    # ---------------- PAGE SWITCH ----------------
    def show_crop_page(self):
        self.page_scrapbook.pack_forget()
        self.page_crop.pack()

    def show_scrapbook_page(self):
        self.page_crop.pack_forget()
        self.page_scrapbook.pack()

    # ---------------- CROP PAGE FUNCTIONS ----------------
    def push_undo(self):
        if self.img_display is not None:
            self.undo_stack.append(self.img_display.copy())
            if len(self.undo_stack) > 10:
                self.undo_stack.pop(0)

    def undo_last(self):
        if len(self.undo_stack) == 0:
            return
        self.img_display = self.undo_stack.pop()
        self.show_img()

    # STEP 2 - UPLOAD AND DISPLAY AN IMAGE
    def load_img(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png")])
        if not path:
            return
        self.img_original = Image.open(path).convert("RGBA")
        self.img_original.thumbnail((600, 500))
        self.img_display = self.img_original.copy()
        self.cropped_base = None
        self.undo_stack.clear()
        self.free_path = []
        self.pixel_slider.set(1.0)
        self.contrast_slider.set(1.0)
        self.saturation_slider.set(1.0)
        self.show_img()

    def show_img(self):
        self.tk_img = ImageTk.PhotoImage(self.img_display)
        self.canvas_crop.delete("all")
        self.canvas_crop.create_image(0, 0, anchor="nw", image=self.tk_img)
        if len(self.free_path) > 1:
            self.canvas_crop.create_line(self.free_path, fill="white", width=2, dash=(5,4), smooth=True)

    # STEP 3 - RECORD A FREEHAND SELECTION PATH
    def start_draw(self, event):
        self.drawing = True
        self.free_path = [(event.x, event.y)]

    def draw_path(self, event):
        if not self.drawing:
            return
        self.free_path.append((event.x, event.y))
        self.show_img()

    def end_draw(self, event):
        self.drawing = False
        if len(self.free_path) > 2:
            self.free_path.append(self.free_path[0])
        self.show_img()

    def clear_path(self):
        self.free_path = []
        self.show_img()

    # STEP 4 - TURN THE SELECTION INTO A TRANSPARENT STICKER
    def crop_shape(self):
        if self.img_display is None or len(self.free_path) < 4:
            return
        self.push_undo()
        w, h = self.img_display.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon(self.free_path, fill=255)
        result = self.img_display.copy()
        result.putalpha(mask)
        self.img_display = result
        self.cropped_base = result.copy()
        self.pixel_slider.set(1.0)
        self.contrast_slider.set(1.0)
        self.saturation_slider.set(1.0)
        self.free_path = []
        self.show_img()

    # STEP 5 - APPLY PIXELATION, CONTRAST, AND COLOUR ADJUSTMENTS
    def update_adjust(self, value=None):
        if self.cropped_base is None:
            return
        work_img = self.cropped_base.copy()
        w, h = work_img.size
        pixel_val = float(self.pixel_slider.get())
        if pixel_val > 1.0:
            small = work_img.resize((int(w // pixel_val), int(h // pixel_val)), Image.Resampling.NEAREST)
            work_img = small.resize((w, h), Image.Resampling.NEAREST)
        contrast_val = float(self.contrast_slider.get())
        work_img = ImageEnhance.Contrast(work_img).enhance(contrast_val)
        sat_val = float(self.saturation_slider.get())
        work_img = ImageEnhance.Color(work_img).enhance(sat_val)
        self.img_display = work_img
        self.show_img()

    def lowpoly_blur(self):
        if self.cropped_base is None:
            return
        self.push_undo()
        img = self.cropped_base.filter(ImageFilter.GaussianBlur(radius=1.3))
        w, h = img.size
        small = img.resize((w // 6, h // 6), Image.Resampling.NEAREST)
        img = small.resize((w, h), Image.Resampling.NEAREST)
        img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=12).convert("RGBA")
        self.img_display = img
        self.show_img()

    # STEP 6 - EXPORT THE STICKER AS A PNG
    def save_sticker(self):
        if self.img_display is None:
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Sticker", "*.png")])
        if save_path:
            self.img_display.save(save_path)

    # ---------------- SCRAPBOOK HELPER ----------------
    def clear_handles(self):
        for hid in self.handle_items:
            self.canvas_scrap.delete(hid)
        self.handle_items.clear()

    def get_sticker_center(self, stk):
        return stk["x"] + stk["source_w"] / 2, stk["y"] + stk["source_h"] / 2

    def draw_handles_for_sticker(self, stk):
        self.clear_handles()
        x, y = stk["x"], stk["y"]
        w, h = stk["source_w"], stk["source_h"]
        rect_id = self.canvas_scrap.create_rectangle(x, y, x + w, y + h, outline="#0088ff", dash=(3,2), tags=("handle_bbox",))
        self.handle_items.append(rect_id)
        sz = 7
        corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
        for cx, cy in corners:
            hnd = self.canvas_scrap.create_rectangle(cx - sz, cy - sz, cx + sz, cy + sz, fill="#0088ff", tags=("scale_handle",))
            self.handle_items.append(hnd)
        mx = x + w / 2
        ry = y - 18
        rot_hnd = self.canvas_scrap.create_oval(mx - sz, ry - sz, mx + sz, ry + sz, fill="#ff4444", tags=("rotate_handle",))
        self.handle_items.append(rot_hnd)

    def find_sticker_by_canvas_id(self, cid):
        for s in self.scrap_sticker_list:
            if s["canvas_id"] == cid:
                return s
        return None

    def render_sticker(self, stk):
        self.canvas_scrap.delete(stk["canvas_id"])
        src = stk["source_pil"]
        if stk["flip_h"]:
            src = src.transpose(Image.FLIP_LEFT_RIGHT)
        if stk["flip_v"]:
            src = src.transpose(Image.FLIP_TOP_BOTTOM)
        scaled = src.resize(
            (max(1, int(stk["source_w"] * stk["scale"])),
             max(1, int(stk["source_h"] * stk["scale"]))),
            Image.Resampling.LANCZOS
        )
        rotated = scaled.rotate(stk["rotation"], expand=True, resample=Image.Resampling.BICUBIC)
        stk["pil"] = rotated
        new_tk = ImageTk.PhotoImage(rotated)
        cid = self.canvas_scrap.create_image(stk["x"], stk["y"], image=new_tk, anchor=tk.NW)
        stk["tkimg"] = new_tk
        stk["canvas_id"] = cid
        self.selected_canvas_id = cid
        self.selected_sticker = stk
        self.draw_handles_for_sticker(stk)

    # ---------------- SCRAPBOOK STICKER NEW ACTIONS ----------------
    def scrap_copy_sticker(self):
        if self.selected_sticker is None:
            messagebox.showwarning("Warning", "Please select a sticker first!")
            return
        src = self.selected_sticker
        new_item = {
            "tkimg": None,
            "pil": None,
            "source_pil": src["source_pil"].copy(),
            "canvas_id": None,
            "x": src["x"] + 30,
            "y": src["y"] + 30,
            "source_w": src["source_w"],
            "source_h": src["source_h"],
            "scale": src["scale"],
            "rotation": src["rotation"],
            "flip_h": src["flip_h"],
            "flip_v": src["flip_v"]
        }
        self.scrap_sticker_list.append(new_item)
        self.render_sticker(new_item)

    def scrap_flip_horizontal(self):
        if self.selected_sticker is None:
            messagebox.showwarning("Warning", "Please select a sticker first!")
            return
        self.selected_sticker["flip_h"] = not self.selected_sticker["flip_h"]
        self.render_sticker(self.selected_sticker)

    def scrap_flip_vertical(self):
        if self.selected_sticker is None:
            messagebox.showwarning("Warning", "Please select a sticker first!")
            return
        self.selected_sticker["flip_v"] = not self.selected_sticker["flip_v"]
        self.render_sticker(self.selected_sticker)

    # ---------------- SCRAPBOOK MAIN FUNCTIONS ----------------
    # STEP 7 - IMPORT A STICKER INTO THE SCRAPBOOK
    def scrap_import_png(self):
        path = filedialog.askopenfilename(filetypes=[("PNG sticker", "*.png")])
        if not path:
            return
        pil_img = Image.open(path).convert("RGBA")
        pil_img.thumbnail((220, 220))
        cid = self.canvas_scrap.create_image(100, 100, image=ImageTk.PhotoImage(pil_img), anchor=tk.NW)
        self.scrap_sticker_list.append({
            "tkimg": None,
            "pil": pil_img,
            "source_pil": pil_img.copy(),
            "canvas_id": cid,
            "x": 100,
            "y": 100,
            "source_w": pil_img.width,
            "source_h": pil_img.height,
            "scale": 1.0,
            "rotation": 0.0,
            "flip_h": False,
            "flip_v": False
        })
        self.render_sticker(self.scrap_sticker_list[-1])

    # STEP 8 - ADD AND STYLE JOURNAL TEXT
    def scrap_add_text_dialog(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Text")
        tk.Label(popup, text="Input your hand-book text:").pack(pady=4)
        text_var = tk.Text(popup, width=35, height=5)
        text_var.pack(padx=6, pady=4)
        def confirm():
            content = text_var.get("1.0", tk.END).strip()
            popup.destroy()
            if not content:
                return
            cid = self.canvas_scrap.create_text(200, 200, text=content, font=("Arial", 14), fill="#222222", anchor=tk.NW)
            self.scrap_text_list.append({
                "canvas_id": cid,
                "text": content,
                "x": 200,
                "y": 200,
                "fontfamily": "Arial",
                "fontsize": 14,
                "color": "#222222"
            })
        tk.Button(popup, text="OK Add Text", command=confirm).pack(pady=5)

    def scrap_edit_text(self):
        target = None
        for t in self.scrap_text_list:
            if t["canvas_id"] == self.selected_canvas_id:
                target = t
                break
        if target is None:
            messagebox.showwarning("Warning", "Please select a text block first!")
            return
        popup = tk.Toplevel(self.root)
        popup.title("Edit Text Style")
        font_families = ["Arial", "Courier New", "Georgia", "Times New Roman", "Verdana", "Comic Sans MS"]
        palette = [
            "#000000", "#333333", "#666666", "#999999", "#cccccc", "#ffffff",
            "#ff0000", "#ff6600", "#ffcc00", "#33cc33", "#00ccff", "#0066ff",
            "#9933ff", "#ff3399", "#8b4513", "#d2691e", "#f5deb3", "#ffe4e1"
        ]
        tk.Label(popup, text="Font Family:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        family_var = tk.StringVar(value=target.get("fontfamily", "Arial"))
        family_menu = tk.OptionMenu(popup, family_var, *font_families, command=lambda v:self.update_text_preview(target, family_var.get(), size_var.get(), current_color.get()))
        family_menu.grid(row=0, column=1, padx=4, pady=4)

        tk.Label(popup, text="Font Size:").grid(row=1, column=0, padx=4, pady=4, sticky="w")
        size_var = tk.IntVar(value=target.get("fontsize", 14))
        def on_size_change(v):
            self.update_text_preview(target, family_var.get(), size_var.get(), current_color.get())
        size_scale = tk.Scale(popup, from_=8, to_=72, orient=tk.HORIZONTAL, variable=size_var, length=220, command=on_size_change)
        size_scale.grid(row=1, column=1, padx=4, pady=4)

        tk.Label(popup, text="Text Color:").grid(row=2, column=0, padx=4, pady=4, sticky="nw")
        color_frame = tk.Frame(popup)
        color_frame.grid(row=2, column=1, padx=4, pady=4)
        current_color = tk.StringVar(value=target.get("color", "#222222"))

        def set_color(c):
            current_color.set(c)
            color_preview.config(bg=c)
            self.update_text_preview(target, family_var.get(), size_var.get(), current_color.get())

        color_preview = tk.Label(color_frame, width=4, bg=current_color.get(), relief="solid", borderwidth=1)
        color_preview.grid(row=0, column=0, padx=2)

        def choose_custom_color():
            c = colorchooser.askcolor(title="Choose Text Color", initialcolor=current_color.get())
            if c and c[1]:
                set_color(c[1])

        tk.Button(color_frame, text="Custom", command=choose_custom_color).grid(row=0, column=1, padx=2)
        grid_frame = tk.Frame(color_frame)
        grid_frame.grid(row=1, column=0, columnspan=2, pady=4)
        for i, c in enumerate(palette):
            btn = tk.Button(grid_frame, bg=c, width=2, height=1, relief="flat", command=lambda color=c: set_color(color))
            btn.grid(row=i // 10, column=i % 10, padx=1, pady=1)

        def apply():
            target["fontfamily"] = family_var.get()
            target["fontsize"] = int(size_var.get())
            target["color"] = current_color.get()
            popup.destroy()

        tk.Button(popup, text="Apply", command=apply).grid(row=3, column=0, columnspan=2, pady=6)

    def update_text_preview(self, text_item, family, size, color):
        self.canvas_scrap.itemconfig(text_item["canvas_id"], font=(family, int(size)), fill=color)

    def scrap_change_bg_color(self):
        c = colorchooser.askcolor(title="Choose Background Color", initialcolor=self.scrap_bg_color)
        if c and c[1]:
            self.scrap_bg_color = c[1]
            self.canvas_scrap.config(bg=c[1])

    # STEP 9 - MOVE, SCALE, AND ROTATE STICKERS WITH THE MOUSE
    def scrap_start_drag(self, event):
        items_under = self.canvas_scrap.find_closest(event.x, event.y)
        if not items_under:
            self.selected_canvas_id = None
            self.selected_sticker = None
            self.drag_mode = None
            self.clear_handles()
            return
        item_id = items_under[0]
        tags = self.canvas_scrap.gettags(item_id)
        stk = self.find_sticker_by_canvas_id(item_id)
        if "scale_handle" in tags and self.selected_sticker is not None:
            self.drag_mode = "scale"
            self.drag_start_scale = self.selected_sticker["scale"]
            self.drag_start_mouse_x = event.x
            self.drag_start_mouse_y = event.y
            return
        if "rotate_handle" in tags and self.selected_sticker is not None:
            self.drag_mode = "rotate"
            cx, cy = self.get_sticker_center(self.selected_sticker)
            self.drag_start_center_x = cx
            self.drag_start_center_y = cy
            self.drag_start_angle = math.atan2(event.y - cy, event.x - cx)
            return
        if stk is not None:
            self.selected_sticker = stk
            self.selected_canvas_id = stk["canvas_id"]
            self.draw_handles_for_sticker(stk)
            self.drag_mode = "move"
            self.dragging_item = item_id
            x0, y0 = self.canvas_scrap.coords(item_id)
            self.drag_offset_x = event.x - x0
            self.drag_offset_y = event.y - y0
            return
        for t in self.scrap_text_list:
            if t["canvas_id"] == item_id:
                self.selected_canvas_id = item_id
                self.selected_sticker = None
                self.clear_handles()
                self.drag_mode = "move"
                self.dragging_item = item_id
                x0, y0 = self.canvas_scrap.coords(item_id)
                self.drag_offset_x = event.x - x0
                self.drag_offset_y = event.y - y0
                return
        self.selected_canvas_id = None
        self.selected_sticker = None
        self.drag_mode = None
        self.clear_handles()

    def scrap_do_drag(self, event):
        if self.drag_mode is None or self.selected_sticker is None:
            if self.drag_mode == "move" and self.dragging_item is not None:
                for t in self.scrap_text_list:
                    if t["canvas_id"] == self.dragging_item:
                        new_x = event.x - self.drag_offset_x
                        new_y = event.y - self.drag_offset_y
                        self.canvas_scrap.coords(self.dragging_item, new_x, new_y)
                        t["x"] = new_x
                        t["y"] = new_y
                        return
            return
        stk = self.selected_sticker
        if self.drag_mode == "move":
            new_x = event.x - self.drag_offset_x
            new_y = event.y - self.drag_offset_y
            stk["x"] = new_x
            stk["y"] = new_y
            self.canvas_scrap.coords(stk["canvas_id"], new_x, new_y)
            self.draw_handles_for_sticker(stk)
            return
        if self.drag_mode == "scale":
            orig_w = stk["source_w"]
            orig_h = stk["source_h"]
            corner_x = stk["x"] + orig_w
            corner_y = stk["y"] + orig_h
            dx = event.x - corner_x
            dy = event.y - corner_y
            dist_now = math.hypot(dx, dy)
            dist_start = math.hypot(self.drag_start_mouse_x - corner_x, self.drag_start_mouse_y - corner_y)
            if dist_start > 0:
                new_scale = max(0.15, min(3.0, self.drag_start_scale * (dist_now / dist_start)))
            else:
                new_scale = self.drag_start_scale
            stk["scale"] = new_scale
            self.render_sticker(stk)
            return
        if self.drag_mode == "rotate":
            current_angle = math.atan2(event.y - self.drag_start_center_y, event.x - self.drag_start_center_x)
            delta_deg = math.degrees(current_angle - self.drag_start_angle)
            stk["rotation"] = (stk["rotation"] + delta_deg) % 360
            self.drag_start_angle = current_angle
            self.render_sticker(stk)
            return

    def scrap_end_drag(self, event):
        self.dragging_item = None
        self.drag_mode = None

    def scrap_delete_selected(self):
        if self.selected_canvas_id is None:
            messagebox.showinfo("Hint", "Click a sticker/text first!")
            return
        self.canvas_scrap.delete(self.selected_canvas_id)
        self.scrap_sticker_list = [s for s in self.scrap_sticker_list if s["canvas_id"] != self.selected_canvas_id]
        self.scrap_text_list = [t for t in self.scrap_text_list if t["canvas_id"] != self.selected_canvas_id]
        self.selected_canvas_id = None
        self.selected_sticker = None
        self.clear_handles()

    def scrap_clear_all(self):
        for s in self.scrap_sticker_list:
            self.canvas_scrap.delete(s["canvas_id"])
        for t in self.scrap_text_list:
            self.canvas_scrap.delete(t["canvas_id"])
        self.scrap_sticker_list.clear()
        self.scrap_text_list.clear()
        self.selected_canvas_id = None
        self.selected_sticker = None
        self.clear_handles()

    # STEP 10 - EXPORT THE FINISHED SCRAPBOOK PAGE
    def scrap_save(self):
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Scrapbook PNG", "*.png")]
        )
        if not save_path:
            return

        w = int(self.canvas_scrap["width"])
        h = int(self.canvas_scrap["height"])
        bg = Image.new(
            "RGBA",
            (w, h),
            self.hex_to_rgba(self.scrap_bg_color)
        )

        for s in self.scrap_sticker_list:
            bg.paste(
                s["pil"],
                (int(s["x"]), int(s["y"])),
                mask=s["pil"]
            )

        draw = ImageDraw.Draw(bg)

        for t in self.scrap_text_list:
            try:
                font = ImageFont.truetype(
                    "arial.ttf",
                    t["fontsize"]
                )
            except OSError:
                font = ImageFont.load_default()

            draw.multiline_text(
                (t["x"], t["y"]),
                t["text"],
                fill=t["color"],
                font=font
            )

        bg.save(save_path)
        messagebox.showinfo(
            "Done",
            f"Saved file:\n{save_path}"
        )

    def hex_to_rgba(self, hex_color):
        hex_color = hex_color.strip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b, 255)

if __name__ == "__main__":
    root = tk.Tk()
    app = StickerTool(root)
    root.mainloop()


