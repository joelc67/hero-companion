' Run the given bat with NO console window (worker ticks stay invisible).
Set sh = CreateObject("Wscript.Shell")
sh.Run """" & WScript.Arguments(0) & """", 0, False
