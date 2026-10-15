' TaskFlow Silent Launcher for Windows
' Double-clicking this file launches TaskFlow without opening a black command prompt window.
Set WshShell = CreateObject("WScript.Shell")
strCurDir = WshShell.CurrentDirectory
WshShell.Run "pythonw """ & strCurDir & "\todo.py""", 0, False
