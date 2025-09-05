# FBX → GLB Converter

A lightweight Python GUI tool to batch convert FBX files to GLB format, preserving materials, optionally removing textures to reduce file size, and adding custom metadata for tracking.

---

## Features

* Batch convert FBX files in a folder to GLB format.
* Optionally keep or remove materials.
* Optionally strip textures to reduce file size.
* Add custom metadata (`extras`) to GLB files (e.g., `"origin": "synty dark fantasy"`).
* Multithreaded conversion with progress bar and status messages.
* Dependency checker for Python packages and external `fbx2gltf` tool.
* Thread-safe GUI with Tkinter.

---

## Requirements

* Python 3.11+
* [`pygltflib`](https://pypi.org/project/pygltflib/)
* [`fbx2gltf`](https://github.com/facebookincubator/FBX2glTF) (add to PATH or use absolute path)

---

## Installation

1. Clone the repository:

```powershell
git clone https://github.com/torbenvanassche/fbx2gltf.git
Set-Location fbx2glb-converter
```

2. Install Python dependencies:

```powershell
python -m pip install pygltflib
```

3. Download `fbx2gltf.exe` and place it in the same folder as the script or add it to your PATH.

---

## Usage

1. Run the script:

```powershell
python .\main.py
```

2. Select **Input Folder** (FBX files) and **Output Folder** (GLB files).
3. Optionally configure:

   * Keep Materials / Remove Textures
   * Add custom metadata in JSON (default includes `"origin": "origin_of_files"`).
4. Click **Convert All FBX**.
5. Progress bar and status messages will indicate conversion progress.

---

### Example Custom Data

```json
{
    "origin": "origin_of_files",
    "author": "YourName"
}
```

This metadata is saved in the GLB's `extras` property and can be read in Godot, Blender, or other GLTF tools.

---

## Notes

* Ensure `fbx2gltf.exe` is accessible; the GUI includes a dependency checker button.
* Converted GLBs are safe to open in Blender, Godot, Three.js, or Unity.

---

## License

MIT License © Torben Van Assche
