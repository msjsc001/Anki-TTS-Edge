import PyInstaller.__main__
import os
import sys
import shutil
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Change working directory to the script directory to simplify relative paths
os.chdir(script_dir)

print(f"Working directory set to: {os.getcwd()}")

def build():
    # Ensure dist and build directories are clean if needed, 
    # but --clean and --y usually handle overwrite.
    
    # PyInstaller arguments
    assets_path = os.path.join(script_dir, 'assets')
    icon_path = os.path.join(script_dir, 'assets', 'icon.ico')

    # Collect customtkinter data files
    # collect_data_files returns a list of (source, dest) tuples
    ctk_datas = collect_data_files('customtkinter')
    ctk_add_data_args = []
    for source, dest in ctk_datas:
        # Use semicolon for Windows separator
        ctk_add_data_args.append(f'--add-data={source};{dest}')
    
    # Collect all edge_tts data, binaries, and hidden imports
    print("Collecting edge_tts dependencies...")
    edge_tts_datas, edge_tts_binaries, edge_tts_hiddenimports = collect_all('edge_tts')
    
    edge_tts_args = []
    
    # Add datas
    for source, dest in edge_tts_datas:
        edge_tts_args.append(f'--add-data={source};{dest}')
        
    # Add binaries
    for source, dest in edge_tts_binaries:
        edge_tts_args.append(f'--add-binary={source};{dest}')
        
    # Add hidden imports
    for hidden_import in edge_tts_hiddenimports:
        edge_tts_args.append(f'--hidden-import={hidden_import}')
        
    print(f"Collected {len(edge_tts_datas)} datas, {len(edge_tts_binaries)} binaries, {len(edge_tts_hiddenimports)} hidden imports for edge_tts")

    args = [
        'main.py',                       # Main script
        '--name=Anki-TTS-Edge',          # Executable name
        '--noconsole',                   # Hide console
        f'--icon={icon_path}',           # Application icon
        f'--add-data={assets_path};assets', # Include assets (Windows separator ;)
        
        # Hidden imports for dependencies that PyInstaller might miss
        '--hidden-import=PIL',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=customtkinter',
        '--hidden-import=engineio.async_drivers.threading', # critical for edge-tts
        # edge_tts imports are now handled by collect_all below
        '--hidden-import=pystray',
        '--hidden-import=pystray._win32',
        
        '--clean',                       # Clean cache before building
        '-y',                            # Overwrite output directory
    ]
    
    # Add collected data files and imports to arguments
    args.extend(ctk_add_data_args)
    args.extend(edge_tts_args)
    
    print("Starting PyInstaller build with arguments:", args)
    
    try:
        PyInstaller.__main__.run(args)
        print("\nBuild completed successfully!")
        print(f"Executable should be in: {os.path.join(script_dir, 'dist', 'Anki-TTS-Edge')}")
    except Exception as e:
        print(f"\nBuild failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()