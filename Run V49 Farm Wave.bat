@echo off
cd /d C:\Users\joelc\code\coh-builder
"C:\Users\joelc\AppData\Local\Programs\Python\Python313\python.exe" tools\converge_parallel.py --recert --workers 3 --sweep-backend process --shard-prefix champions_shard_v49afk --keys "Class_Brute|Brute_Melee.Spines|Brute_Defense.Fiery_Aura|farm_afk,Class_Brute|Brute_Melee.Titan_Weapons|Brute_Defense.Bio_Organic_Armor|farm_afk,Class_Tanker|Tanker_Defense.Fiery_Aura|Tanker_Melee.Fiery_Melee|farm_afk" > wave_v49afk.log 2>&1
