import os
import shutil
import PyInstaller.__main__

def build_executable():
    """Build the student client executable using PyInstaller."""
    
    script_file = 'service.py'
    exe_name = 'ClassroomClient'
    
    # PyInstaller options
    opts = [
        f'--name={exe_name}',
        '--onefile',
        '--windowed',
        '--add-data=../shared;shared',
        '--hidden-import=win32timezone' # Required for PyInstaller
    ]
    
    print("Building executable...")
    PyInstaller.__main__.run([
        script_file,
        *opts
    ])
    
    print("\nBuild complete.")
    print(f"Executable created in: {os.path.abspath('dist')}")

if __name__ == '__main__':
    build_executable()