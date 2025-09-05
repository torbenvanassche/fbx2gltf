import sys
import subprocess
import importlib
import shutil
import json
import threading
import queue
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# -----------------------------
# Dependency helpers
# -----------------------------
def ensure_package(pkg: str):
    try:
        importlib.import_module(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

def install_dependencies() -> list[str]:
    missing: list[str] = []
    try:
        ensure_package("pygltflib")
    except Exception:
        missing.append("pygltflib")
    if not shutil.which("fbx2gltf"):
        missing.append("fbx2gltf (install from https://github.com/facebookincubator/FBX2glTF)")
    return missing

# -----------------------------
# Core conversion (safe cleanup)
# -----------------------------
def convert_fbx_to_glb(
    fbx_path: Path,
    glb_path: Path,
    *,
    keep_materials: bool = True,
    remove_textures: bool = True,
    custom_data: dict | None = None,
    fbx2gltf_path: str = "fbx2gltf",
):
    subprocess.run([
        fbx2gltf_path,
        "-i", str(fbx_path),
        "-o", str(glb_path),
        "--binary",
    ], check=True)

    from pygltflib import GLTF2
    gltf = GLTF2().load(str(glb_path))

    if remove_textures:
        for mat in (gltf.materials or []):
            pmr = getattr(mat, "pbrMetallicRoughness", None)
            if pmr is not None:
                pmr.baseColorTexture = None
                pmr.metallicRoughnessTexture = None
            mat.normalTexture = None
            mat.occlusionTexture = None
            mat.emissiveTexture = None
        gltf.textures = []
        gltf.images = []

    if not keep_materials:
        for mesh in (gltf.meshes or []):
            for prim in (mesh.primitives or []):
                prim.material = None
        gltf.materials = []

    if custom_data:
        if gltf.extras is None:
            gltf.extras = {}
        gltf.extras.update(custom_data)

    gltf.save(str(glb_path))

# -----------------------------
# GUI App
# -----------------------------
class FBXConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FBX → GLB Converter")
        self.root.geometry("680x520")

        self.events = queue.Queue()
        self.convert_thread: threading.Thread | None = None

        main = ttk.Frame(root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Top: Dependency button full-width
        self.dep_btn = ttk.Button(main, text="Check/Install Dependencies", command=self.handle_dependencies)
        self.dep_btn.grid(row=0, column=0, columnspan=3, pady=(0, 10), sticky="ew")

        # Input
        ttk.Label(main, text="Input Folder:").grid(row=1, column=0, sticky="e")
        self.input_var = tk.StringVar(value=str(""))
        ttk.Entry(main, textvariable=self.input_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(main, text="Browse", command=self.browse_input).grid(row=1, column=2)

        # Output
        ttk.Label(main, text="Output Folder:").grid(row=2, column=0, sticky="e")
        self.output_var = tk.StringVar(value=str(""))
        ttk.Entry(main, textvariable=self.output_var).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(main, text="Browse", command=self.browse_output).grid(row=2, column=2)

        # Options
        opts = ttk.LabelFrame(main, text="Conversion Options", padding=10)
        opts.grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")
        self.keep_materials_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Keep Materials", variable=self.keep_materials_var).grid(row=0, column=0, sticky="w")
        self.remove_textures_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Remove Textures", variable=self.remove_textures_var).grid(row=0, column=1, sticky="w")

        # Custom JSON
        ttk.Label(main, text="Custom Data (JSON):").grid(row=4, column=0, sticky="ne")
        self.custom_text = tk.Text(main, height=6)
        self.custom_text.grid(row=4, column=1, columnspan=2, pady=5, sticky="nsew")

        # Insert default custom data
        default_data = {
            "origin": "origin_pack_name"
        }
        self.custom_text.insert("1.0", json.dumps(default_data, indent=4))

        # Progress + status
        self.progress = ttk.Progressbar(main)
        self.progress.grid(row=5, column=0, columnspan=3, pady=10, sticky="ew")
        self.status_label = ttk.Label(main, text="Idle", anchor="center")
        self.status_label.grid(row=6, column=0, columnspan=3, sticky="ew")

        # Bottom: Convert button full-width
        self.convert_btn = ttk.Button(main, text="Convert All FBX", command=self.start_conversion_thread)
        self.convert_btn.grid(row=7, column=0, columnspan=3, pady=15, sticky="ew")

        # Make columns/rows expand nicely
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=3)
        main.columnconfigure(2, weight=1)
        main.rowconfigure(4, weight=1)  # text box grows

        # Start polling queue
        self.root.after(100, self.poll_events)

    # -------------------------
    # UI callbacks
    # -------------------------
    def browse_input(self):
        folder = filedialog.askdirectory(initialdir=self.input_var.get())
        if folder:
            self.input_var.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get())
        if folder:
            self.output_var.set(folder)

    def handle_dependencies(self):
        def work():
            try:
                missing = install_dependencies()
                if not missing:
                    self.events.put(("info", "Dependencies", "All dependencies are installed and ready!"))
                else:
                    self.events.put(("warn", "Dependencies", "Missing: " + ", ".join(missing)))
            except Exception as e:
                self.events.put(("error", "Dependencies", f"Error while installing: {e}"))
        threading.Thread(target=work, daemon=True).start()

    def start_conversion_thread(self):
        if self.convert_thread and self.convert_thread.is_alive():
            return
        self.convert_btn.config(state=tk.DISABLED)
        self.progress.config(value=0, maximum=100)
        self.status_label.config(text="Preparing…")
        self.convert_thread = threading.Thread(target=self.convert_all, daemon=True)
        self.convert_thread.start()

    # -------------------------
    # Worker
    # -------------------------
    def convert_all(self):
        try:
            input_folder = Path(self.input_var.get())
            output_folder = Path(self.output_var.get())
            if not input_folder.exists() or not output_folder.exists():
                self.events.put(("error", "Error", "Please select valid input and output folders."))
                self.events.put(("done",))
                return

            custom_data_str = self.custom_text.get("1.0", tk.END).strip()
            custom_data = {}
            if custom_data_str:
                try:
                    custom_data = json.loads(custom_data_str)
                except json.JSONDecodeError as e:
                    self.events.put(("error", "Invalid JSON", f"Custom data is not valid JSON:\n{e}"))
                    self.events.put(("done",))
                    return

            fbx_files = sorted(list(input_folder.glob("*.fbx")))
            if not fbx_files:
                self.events.put(("info", "Info", "No FBX files found in input folder."))
                self.events.put(("done",))
                return

            self.events.put(("setmax", len(fbx_files)))
            keep_materials = self.keep_materials_var.get()
            remove_textures = self.remove_textures_var.get()

            for i, fbx_file in enumerate(fbx_files, start=1):
                glb_file = output_folder / (fbx_file.stem + ".glb")
                self.events.put(("status", f"Processing {fbx_file.name} ({i}/{len(fbx_files)})"))
                try:
                    convert_fbx_to_glb(
                        fbx_file,
                        glb_file,
                        keep_materials=keep_materials,
                        remove_textures=remove_textures,
                        custom_data=custom_data,
                    )
                except subprocess.CalledProcessError as e:
                    self.events.put(("error", "Conversion failed", f"fbx2gltf failed for {fbx_file.name}:\n{e}"))
                except Exception as e:
                    self.events.put(("error", "Error", f"Error processing {fbx_file.name}: {e}"))
                finally:
                    self.events.put(("progress", i))

            self.events.put(("status", "Conversion complete"))
            self.events.put(("info", "Done", f"Converted {len(fbx_files)} FBX files to GLB."))
        finally:
            self.events.put(("done",))

    # -------------------------
    # Polling
    # -------------------------
    def poll_events(self):
        try:
            while True:
                evt = self.events.get_nowait()
                kind = evt[0]

                if kind == "setmax":
                    self.progress.config(maximum=evt[1], value=0)
                elif kind == "progress":
                    self.progress.config(value=evt[1])
                elif kind == "status":
                    self.status_label.config(text=evt[1], anchor="center")
                elif kind == "info":
                    _, title, msg = evt
                    messagebox.showinfo(title, msg)
                    self.progress.config(value=0)
                    self.status_label.config(text="Idle")
                elif kind == "warn":
                    _, title, msg = evt
                    messagebox.showwarning(title, msg)
                    self.progress.config(value=0)
                    self.status_label.config(text="Idle")
                elif kind == "error":
                    _, title, msg = evt
                    messagebox.showerror(title, msg)
                    self.progress.config(value=0)
                    self.status_label.config(text="Idle")
                elif kind == "done":
                    self.convert_btn.config(state=tk.NORMAL)

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.poll_events)


if __name__ == "__main__":
    root = tk.Tk()
    app = FBXConverterApp(root)
    root.mainloop()
