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

    # Audio cue WAV files
    audio_cues_dir = os.path.join(project_dir, "audio_cues")
    if os.path.isdir(audio_cues_dir):
        data_files.append(f"--add-data=audio_cues;audio_cues")

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
        "--runtime-hook=rthooks/pyi_rth_dll_security.py",
        "--uac-admin=False",
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
        print(f"\n[FEHLER] PyInstaller Build fehlgeschlagen (Exit-Code {res.returncode})")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Post-build: Ensure all CUDA DLLs and data files are in place
    # ------------------------------------------------------------------
    print("\n[2/3] Bereite neutrale App-Struktur und CUDA-Treiber vor...")

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
        print("  [ERFOLG] Velodictum erfolgreich gebaut!")
        print("=" * 60)
        print(f"  Exe:            {exe_path}")
        print(f"  Exe-Groesse:    {size_mb:.1f} MB")
        print(f"  Ordner-Gesamt:  {total_size:.0f} MB")
        print()
        print("  Zum Weitergeben:")
        print(f"  -> Den gesamten Ordner 'dist\\Velodictum\\' als ZIP verpacken.")
        print("  -> Dein Freund entpackt die ZIP und startet Velodictum.exe.")
        print("  -> Keine Python-Installation noetig!")
        print("=" * 60)
    else:
        print("\n[WARNUNG] Velodictum.exe nicht in dist/ gefunden.")


if __name__ == "__main__":
    build()
