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


# Our local-build auth path is Joel's `az login` (signing-runbook.md). Pin the
# credential to azure-cli so the tool doesn't default through DefaultAzureCredential
# and die on ManagedIdentity (which only exists on Azure VMs). Overridable for CI
# (e.g. workload-identity) via AZURE_CREDENTIAL_TYPE.
CRED_TYPE = os.environ.get("AZURE_CREDENTIAL_TYPE", "azure-cli")


def sign_file(sign_tool, path):
    """Sign one file with the Trusted Signing client. Returns True on success."""
    cmd = [sign_tool, "code", "trusted-signing",
           "--trusted-signing-account", ACCOUNT,
           "--trusted-signing-certificate-profile", PROFILE,
           "--trusted-signing-endpoint", ENDPOINT,
           "--azure-credential-type", CRED_TYPE,
           path]
    print(f"  signing {os.path.relpath(path, ROOT)} …", flush=True)
    r = subprocess.run(cmd)
    return r.returncode == 0


def verify_file(path):
    """Confirm the Authenticode signature is Valid and read the signer subject.
    Uses PowerShell's Get-AuthenticodeSignature — always present on Windows, no
    Windows SDK / signtool needed."""
    ps = ("$s = Get-AuthenticodeSignature -LiteralPath '%s'; "
          "\"$($s.Status)|$($s.SignerCertificate.Subject)\"" % path)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    out = (r.stdout or "").strip()
    status, _, subject = out.partition("|")
    ok = status == "Valid"
    print(f"  verify {os.path.basename(path)}: {status or 'UNKNOWN'}"
          + (f"  [{subject.split(',')[0]}]" if subject else ""))
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
