@echo off
rem ============================================================================
rem #13 batch (v34) — evaluate-first roster pass, DETACHED + READ-ONLY.
rem
rem Scores every certified context under the CURRENT code (model v34, the #13
rem pet-buff term) and prints BASELINE / UNAFFECTED / MOVED vs each entry's
rem recorded v33 canonical_score. NO --write: the verdict-before-write rule
rem (2026-07-16) forbids overwriting canonical_score before the verdict is read
rem (--write would clobber the very baselines the diff compares against).
rem
rem Expected movers: MM contexts (Supremacy/AM/Temporal Selection/Pack Mentality
rem — the NON-incarnate pet buffs; incarnates are display-only in the cert chain,
rem so the Assault Hybrid gap is certification-irrelevant). Everything else:
rem UNAFFECTED (v34 does not touch non-pet scoring).
rem
rem Read-only + restart-safe: if killed, just relaunch (mutates nothing).
rem ============================================================================
cd /d %~dp0
set "PYTHON=python"
where python >nul 2>nul || set "PYTHON=C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe"
echo Started: %DATE% %TIME% > eval_first_v34_log.txt
"%PYTHON%" tools\evaluate_first.py --skip-riders >> eval_first_v34_log.txt 2>&1
echo Finished: %DATE% %TIME% >> eval_first_v34_log.txt
