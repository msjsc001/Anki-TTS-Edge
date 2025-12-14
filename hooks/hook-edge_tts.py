# Custom hook for edge_tts
from PyInstaller.utils.hooks import collect_all

# Force collect edge_tts from wherever it's installed
datas, binaries, hiddenimports = collect_all('edge_tts')
