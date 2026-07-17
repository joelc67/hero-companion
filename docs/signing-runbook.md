# Code Signing + AV-whitelisting runbook (Windows Citizenship)

Both Companion Lite and Hero Companion ship **code-signed** so Windows shows a
verified publisher ("Joel Andrew Chambers") instead of an "unknown publisher"
warning. Signing uses **Azure Trusted (Artifact) Signing** — a cloud
Public-Trust certificate; no private key ever lives on disk.

## The facts
- Account `herocompanionsign` · endpoint `https://eus.codesigning.azure.net/`
  · resource group `hero-companion-signing` · region East US · SKU Basic
  (5,000 signatures/month).
- Identity validation: **Completed 2026-07-15, expires 2027-07-15** (id
  724232a4-8f38-4ec1-96de-ebce1afddd04, subject `CN=Joel Andrew Chambers`).
  ⚠ A lapse halts all signing — see the CLAUDE.md watch item.

## One-time setup (Joel's portal minutes)
1. **Certificate profile** — portal → the signing account → Objects →
   Certificate profiles → Create → **Public Trust** → select the completed
   identity → leave street/postal checkboxes OFF. Note the profile NAME.
2. **Signer role** — account → Access control (IAM) → assign your user
   **"Artifact Signing Certificate Profile Signer"** (the Verifier role does
   NOT sign — this is the classic gotcha).
3. Confirm the Basic-tier monthly price shown in the portal.

## One-time setup (build machine)
- `az login` as Joel (the signer credential — DefaultAzureCredential picks it up).
- `dotnet tool install --global sign` (the Trusted Signing client), OR set
  `SIGN_TOOL` to a full path.
- Set `TRUSTED_SIGNING_PROFILE` to the certificate-profile name from step 1.
- (Optional, for verify) the Windows SDK's `signtool` on PATH.

## Signing a release (part of the release procedure for BOTH apps)
After the frozen build + installer are produced:
```
python tools\sign_artifacts.py            # signs exe(s) + installer, then verifies
python tools\sign_artifacts.py --check    # report prerequisites only, sign nothing
```
It signs whatever build artifacts exist (Lite exe + `CompanionLite-Setup-*.exe`,
Hero Companion exe + `HeroCompanion-Setup-*.exe`) and runs `signtool verify /pa`
on each. If a prerequisite is missing it prints exactly which and signs nothing.

## AV false-positive / whitelist submissions (run per release)
Signing removes the "unknown publisher" warning immediately; SmartScreen's "not
commonly downloaded" prompt is reputation-based and decays as installs
accumulate. If a scanner still flags a signed build, submit it:
- **Microsoft** (SmartScreen / Defender): https://www.microsoft.com/wdsi (submit a file → "I believe this is safe").
- **Bitdefender**: https://www.bitdefender.com/submit — the standing Bitdefender-heuristic watch (status-line check) rides along; note behavior on Joel's boxes.
- **Avast/AVG** (shared engine): https://www.avast.com/false-positive-file-form.php
- **Kaspersky**: https://opentip.kaspersky.com/ (submit for analysis).
- **Malwarebytes**: https://www.malwarebytes.com/false-positive (forum/submission).

## Honest user-facing wording (say this, don't overclaim)
Signing kills the unknown-publisher warning and puts a verified name on the
install dialog **immediately**. SmartScreen may still show a "not commonly
downloaded" prompt on day one because this tier has no instant-reputation (EV)
shortcut — that fades to zero as reputation builds on the signed identity.
Warnings drop sharply at signing and decay to zero, not guaranteed-zero on day
one.
