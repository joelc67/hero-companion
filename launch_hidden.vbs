' Hidden-console launcher for the overnight-run bats (2026-07-16).
' WHY: both scheduled-task generations died to a literal ^C in their logs -
' visible task consoles are killable (closed windows / stray Ctrl+C).
' wscript runs the bat with window style 0: no console visible, nothing to
' close, no keyboard focus to catch an interrupt. Usage:
'   wscript.exe launch_hidden.vbs "Run Swap Sweep.bat"
If WScript.Arguments.Count < 1 Then WScript.Quit 1
bat = WScript.Arguments(0)
Set sh = CreateObject("Wscript.Shell")
sh.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
sh.Run "cmd /c """ & bat & """", 0, False
