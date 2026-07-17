"""Artifact Signing — sign HC/Lite build artifacts with Azure Trusted (Artifact)
Signing (Windows Citizenship, 2026-07-17). SHARED by both apps' build scripts.

WHY THIS EXISTS: signing an .exe/installer with a Public-Trust cert removes the
"unknown publisher" warning and puts "Joel Andrew Chambers" on the install
dialog. This wraps the `sign` CLI (Microsoft's Trusted Signing client), which
authenticates with DefaultAzureCredential — i.e. Joel's `az login` — and signs
against the cloud cert profile (no private key ever on disk).

PREREQUISITES (Joel's portal minutes + a one-time local setup; the script
checks each and prints exactly what is missing rather than failing cryptically):
  1. Azure identity validation COMPLETED (done 2026-07-15, expires 2027-07-15).
  2. A Certificate profile created in the portal (Objects -> Certificate
     profiles -> Public Trust). Its NAME goes in TRUSTED_SIGNING_PROFILE.
  3. Joel's user has the "Artifact Signing Certificate Profile Signer" role on
     the account (IAM) — the Verifier role does NOT sign.
  4. Local: `az login` as Joel, and the sign tool:
        dotnet tool install --global sign
     (or set SIGN_TOOL to a full path).

FACTS (from signing-setup-walkthrough.md — not secret, the account is public-trust):
  account   herocompanionsign
  endpoint  https://eus.codesigning.azure.net/
  region    East US   sku Basic (5,000 sigs/mo)

Run:
  # sign the default build artifacts (Lite exe + installer, whichever exist):
  py tools\\sign_artifacts.py
  # or specific files:
  py tools\\sign_artifacts.py dist\\CompanionLite\\CompanionLite.exe dist\\CompanionLite-Setup-0.1.18.exe
  # dry run — only report prerequisite status, sign nothing:
  py tools\\sign_artifacts.py --check
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ACCOUNT = os.environ.get("TRUSTED_SIGNING_ACCOUNT", "herocompanionsign")
ENDPOINT = os.environ.get("TRUSTED_SIGNING_ENDPOINT",
                          "https://eus.codesigning.azure.net/")
# The profile NAME is created by Joel in the portal — no default can be assumed.
PROFILE = os.environ.get("TRUSTED_SIGNING_PROFILE")

# Default artifacts: sign whatever the current builds produced.
DEFAULT_GLOBS = [
    os.path.join(ROOT, "dist", "CompanionLite", "CompanionLite.exe"),
    os.path.join(ROOT, "dist", "CompanionLite-Setup-*.exe"),
    os.path.join(ROOT, "dist", "HeroCompanion", "HeroCompanion.exe"),
    os.path.join(ROOT, "dist", "HeroCompanion-Setup-*.exe"),
]


def _which(name):
    return shutil.which(name) or (shutil.which(name + ".exe"))


def check_prereqs():
    """Return (ok, [missing-messages]). Never raises."""
    missing = []
    # 1) az login
    az = _which("az")
    if not az:
        missing.append("Azure CLI not found — install it and run `az login` as Joel.")
    else:
        r = subprocess.run([az, "account", "show"], capture_output=True, text=True)
        if r.returncode != 0:
            missing.append("Not logged in to Azure — run `az login` as Joel.")
    # 2) the sign tool
    sign = os.environ.get("SIGN_TOOL") or _which("sign")
    if not sign:
        missing.append("`sign` tool not found — `dotnet tool install --global sign` "
                       "(or set SIGN_TOOL).")
    # 3) the cert profile name
    if not PROFILE:
        missing.append("TRUSTED_SIGNING_PROFILE not set — put the Certificate profile "
                       "name Joel created in the portal (Objects -> Certificate profiles).")
    return (not missing), missing, (sign if sign else None)


def sign_file(sign_tool, path):
    """Sign one file with the Trusted Signing client. Returns True on success."""
    cmd = [sign_tool, "code", "trusted-signing",
           "--trusted-signing-account", ACCOUNT,
           "--trusted-signing-certificate-profile", PROFILE,
           "--trusted-signing-endpoint", ENDPOINT,
           path]
    print(f"  signing {os.path.relpath(path, ROOT)} …", flush=True)
    r = subprocess.run(cmd)
    return r.returncode == 0


def verify_file(path):
    """signtool verify /pa — confirm the Authenticode signature chains to a
    trusted root. signtool ships with the Windows SDK; skip (warn) if absent."""
    st = _which("signtool")
    if not st:
        print(f"  (signtool not on PATH — skipped verify of "
              f"{os.path.basename(path)}; install the Windows SDK to verify)")
        return True
    r = subprocess.run([st, "verify", "/pa", "/v", path],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"  verify {os.path.basename(path)}: {'OK' if ok else 'FAILED'}")
    if not ok:
        print("   ", (r.stdout or r.stderr).strip().splitlines()[-1:])
    return ok


def resolve_targets(args):
    if args:
        out = []
        for a in args:
            out += glob.glob(a) or [a]
        return out
    found = []
    for g in DEFAULT_GLOBS:
        found += glob.glob(g)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="files/globs to sign (default: build artifacts)")
    ap.add_argument("--check", action="store_true", help="report prerequisites only, sign nothing")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    ok, missing, sign_tool = check_prereqs()
    print(f"Trusted Signing: account={ACCOUNT} endpoint={ENDPOINT} "
          f"profile={PROFILE or '(unset)'}")
    if missing:
        print("PREREQUISITES NOT MET — nothing signed:")
        for m in missing:
            print("  -", m)
        # Not an error when merely checking; a real signing run should fail.
        sys.exit(0 if args.check else 2)
    print("prerequisites OK.")
    if args.check:
        return

    targets = resolve_targets(args.files)
    if not targets:
        print("no artifacts found to sign (build first).")
        sys.exit(1)
    print(f"signing {len(targets)} artifact(s):")
    failed = 0
    for t in targets:
        if not sign_file(sign_tool, t):
            failed += 1
            print(f"  SIGN FAILED: {t}")
            continue
        if not verify_file(t):
            failed += 1
    print(f"\n{len(targets) - failed} of {len(targets)} signed+verified.")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
