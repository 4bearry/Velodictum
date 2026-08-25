"""
Velodictum - PyInstaller Standalone Build Script
Bundles Velodictum into a fully portable Windows application.

Usage:
    .venv\Scripts\python.exe build_executable.py

Output:
    dist\Velodictum\Velodictum.exe   (portable, no Python required)
"""
import subprocess
import sys
import os
import shutil


def build():
    print("=" * 60)
    print("  VELODICTUM - STANDALONE BUILD ENGINE")
    print("=" * 60)

    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Use a temp directory outside OneDrive to avoid sync-related file locks
    import tempfile
    build_tmp = os.path.join(tempfile.gettempdir(), "VelodictumBuild")
    dist_tmp  = os.path.join(tempfile.gettempdir(), "VelodictumDist")
    os.makedirs(build_tmp, exist_ok=True)
    os.makedirs(dist_tmp, exist_ok=True)

    # Final destination inside the project (copied after successful build)
    dist_dir = os.path.join(project_dir, "dist", "Velodictum")

    # ------------------------------------------------------------------
    # 1. Collect data files that must ship alongside the .exe
    # ------------------------------------------------------------------
    data_files = []

    # Only include non-personal template/config files if explicitly present
    for json_file in ["app_profiles.json"]:
        src = os.path.join(project_dir, json_file)
        if os.path.exists(src):
            data_files.append(f"--add-data={json_file};.")

    # ------------------------------------------------------------------
    # 2. Hidden imports for dynamic/lazy imports that PyInstaller misses
    # ------------------------------------------------------------------
    hidden_imports = [
        # Audio
        "sounddevice",
        "numpy",
        "pyfxr",
        # Credentials
        "keyring",
        "keyring.backends",
        "keyring.backends.Windows",
        # Clipboard
        "pyperclip",
        # Input
        "pynput",
        "pynput.keyboard",
        "pynput.keyboard._win32",
        "pynput.mouse",
        "pynput.mouse._win32",
        "keyboard",
        # Qt GUI
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtSvg",
        # STT / ML
        "faster_whisper",
        "ctranslate2",
        "onnxruntime",
        # Win32
        "comtypes",
        "winsound",
        # HTTP (Mobile Bridge)
        "httpx",
        "httpcore",
        "h11",
        "anyio",
        # Misc
        "scipy",
        "scipy.signal",
    ]

    # ------------------------------------------------------------------
    # 3. Build command
    # ------------------------------------------------------------------
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Velodictum",
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--distpath={dist_tmp}",
        f"--workpath={build_tmp}",
        "--runtime-hook=rthooks/pyi_rth_dll_security.py",
        "--collect-all=faster_whisper",

        "--collect-all=ctranslate2",
        "--collect-all=onnxruntime",
        "--collect-all=nvidia_cublas_cu12",
        "--collect-all=nvidia_cudnn_cu12",
        "--collect-all=nvidia_cuda_nvrtc_cu12",
        "--paths=core",
        "--paths=.",
    ]


    for imp in hidden_imports:
        pyinstaller_cmd.append(f"--hidden-import={imp}")

    pyinstaller_cmd.extend(data_files)
    pyinstaller_cmd.append("main.py")

    print()
    print("[1/3] Running PyInstaller...")
    print(f"      Command: {' '.join(pyinstaller_cmd[:6])} ...")
    print()

    res = subprocess.run(pyinstaller_cmd, cwd=project_dir)

    if res.returncode != 0:
        print(f"\n[ERROR] PyInstaller build failed (exit code {res.returncode})")
        sys.exit(1)

    # Copy the result from temp dist back to the project's dist/ folder
    print("\n[1.5/3] Copying build output to dist/Velodictum/...")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    shutil.copytree(os.path.join(dist_tmp, "Velodictum"), dist_dir)
    print(f"      Copied to: {dist_dir}")

    # ------------------------------------------------------------------
    # 4. Post-build: Ensure all CUDA DLLs and data files are in place
    # ------------------------------------------------------------------
    print("\n[2/3] Setting up app structure and CUDA drivers...")

    # Copy template configs
    for json_file in ["app_profiles.json"]:
        src = os.path.join(project_dir, json_file)
        dst = os.path.join(dist_dir, json_file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"      {json_file} -> dist/Velodictum/{json_file}")

    # Copy any nvidia DLLs if not already placed
    import site
    site_dirs = []
    if hasattr(site, "getsitepackages"):
        site_dirs.extend(site.getsitepackages())
    site_dirs.append(os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages"))
    
    internal_target = os.path.join(dist_dir, "_internal")
    target_dir = internal_target if os.path.isdir(internal_target) else dist_dir

    for s_dir in site_dirs:
        nvidia_dir = os.path.join(s_dir, "nvidia")
        if os.path.isdir(nvidia_dir):
            for root, dirs, files in os.walk(nvidia_dir):
                for f in files:
                    if f.endswith(".dll"):
                        src_dll = os.path.join(root, f)
                        dst_dll = os.path.join(target_dir, f)
                        if not os.path.exists(dst_dll):
                            shutil.copy2(src_dll, dst_dll)
                            print(f"      CUDA DLL: {f} -> dist/Velodictum/")


    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    exe_path = os.path.join(dist_dir, "Velodictum.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        total_size = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, dn, fn in os.walk(dist_dir)
            for f in fn
        ) / (1024 * 1024)

        print()
        print("=" * 60)
        print("  [SUCCESS] Velodictum built successfully!")
        print("=" * 60)
        print(f"  Exe:           {exe_path}")
        print(f"  Exe size:      {size_mb:.1f} MB")
        print(f"  Folder total:  {total_size:.0f} MB")
        print()
        print("  To distribute:")
        print("  -> ZIP the entire 'dist\\Velodictum\\' folder.")
        print("  -> The recipient extracts it and runs Velodictum.exe.")
        print("  -> No Python installation required!")
        print("=" * 60)
    else:
        print("\n[WARNING] Velodictum.exe not found in dist/.")


if __name__ == "__main__":
    build()
