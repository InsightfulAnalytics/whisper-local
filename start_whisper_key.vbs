Set WshShell = CreateObject("WScript.Shell")
' Run pythonw.exe (windowless python) and point it to main.py
' The "0" means hide the window, "False" means don't wait for it to finish
WshShell.Run "g:\Git\whisper-key-local\.venv\Scripts\pythonw.exe g:\Git\whisper-key-local\src\whisper_key\main.py", 0, False
