@echo off
rem v38+HO wave VERDICT PASS over the 23 banked contexts (Crab Spider follows
rem separately when its re-run lands; verdict jsons merge before the table).
rem Read-only analysis; the merge step never runs from here.
cd /d %~dp0
set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
echo ===== verdicts launch %DATE% %TIME% ===== >> verdicts_v38ho.log
"%PYTHON%" tools\recert_verdicts.py champions_shard_v38ho_p0.json champions_shard_v38ho_p1.json champions_shard_v38ho_p2.json champions_shard_v38ho_p4.json champions_shard_v38ho_p5.json champions_shard_v38ho_resume1_p0.json champions_shard_v38ho_resume1_p1.json champions_shard_v38ho_resume1_p2.json champions_shard_v38ho_resume1_p3.json >> verdicts_v38ho.log 2>&1
echo ===== verdicts exited %ERRORLEVEL% at %DATE% %TIME% ===== >> verdicts_v38ho.log
