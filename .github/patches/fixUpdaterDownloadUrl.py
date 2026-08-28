"""
fixUpdaterDownloadUrl.py — Patch RustDesk updater.rs download URL construction.

The upstream updater.rs constructs download filenames as:
    format!("{}/rustdesk-{}-{}.{}", download_url, version, arch, ext)
    → rustdesk-v1.4.9-x86_64.exe

But custom client builds produce:
    AcilBir.exe  (Windows — no version/arch in filename)

This script patches the format strings to use crate::get_app_name()
and drop version/arch from the filename, matching the actual build output.

Usage: python fixUpdaterDownloadUrl.py
Run from the rustdesk source root (where src/updater.rs exists).
"""
import os
import sys
import re

UPDATER_PATH = os.path.join("src", "updater.rs")

if not os.path.isfile(UPDATER_PATH):
    print(f"[fixUpdaterDownloadUrl] {UPDATER_PATH} not found, skipping.")
    sys.exit(0)

with open(UPDATER_PATH, "r", encoding="utf-8") as f:
    content = f.read()

original = content
changes = 0

# ──────────────────────────────────────────────────────────────────────
# Fix 1: Windows Flutter download URL (the main path)
#
# FROM (multiline format!):
#   format!(
#       "{}/rustdesk-{}-{}.{}",
#       download_url,
#       version,
#       arch,
#       if update_msi { "msi" } else { "exe" }
#   )
#
# TO:
#   format!(
#       "{}/{}.{}",
#       download_url,
#       crate::get_app_name(),
#       if update_msi { "msi" } else { "exe" }
#   )
# ──────────────────────────────────────────────────────────────────────

# Pattern: the format string template
old_fmt = '"{}/rustdesk-{}-{}.{}"'
new_fmt = '"{}/{}.{}"'

if old_fmt in content:
    content = content.replace(old_fmt, new_fmt, 1)
    # Now remove the `version,` and `arch,` arguments from this format! call.
    # They appear as separate lines:
    #     download_url,
    #     version,        ← remove
    #     arch,           ← remove
    #     if update_msi ...

    # Use regex to find and remove the version and arch lines in this specific context
    # We look for the pattern after our new format string
    pattern = re.compile(
        r'(format!\(\s*"\{}/\{}\.\{}"[^)]*?download_url,)\s*\n\s*version,\s*\n\s*arch,',
        re.DOTALL
    )
    replacement = r'\1\n                    crate::get_app_name(),'
    content, n = pattern.subn(replacement, content, count=1)
    if n > 0:
        changes += 1
        print("[fixUpdaterDownloadUrl] Patched Windows Flutter download URL format.")
    else:
        # Fallback: try simpler replacement of just version/arch args
        # after download_url, on consecutive lines
        content_lines = content.split('\n')
        new_lines = []
        i = 0
        while i < len(content_lines):
            line = content_lines[i]
            # Look for download_url, followed by version, then arch,
            if ('download_url,' in line and
                i + 2 < len(content_lines) and
                'version,' in content_lines[i + 1].strip() and
                'arch,' in content_lines[i + 2].strip() and
                # Make sure we're in the right context (after our new format string)
                any('"{}/{}.{}"' in content_lines[j] for j in range(max(0, i - 5), i))):
                new_lines.append(line)  # keep download_url,
                indent = len(content_lines[i + 1]) - len(content_lines[i + 1].lstrip())
                new_lines.append(' ' * indent + 'crate::get_app_name(),')
                i += 3  # skip version, and arch,
                changes += 1
                print("[fixUpdaterDownloadUrl] Patched Windows Flutter download URL args (fallback).")
                continue
            new_lines.append(line)
            i += 1
        content = '\n'.join(new_lines)

# ──────────────────────────────────────────────────────────────────────
# Fix 2: Windows Sciter download URL (legacy path)
#
# FROM:
#   format!("{}/rustdesk-{}-x86-sciter.exe", download_url, version)
#
# TO:
#   format!("{}/{}.exe", download_url, crate::get_app_name())
# ──────────────────────────────────────────────────────────────────────

old_sciter = '"{}/rustdesk-{}-x86-sciter.exe"'
new_sciter = '"{}/{}.exe"'

if old_sciter in content:
    content = content.replace(old_sciter, new_sciter, 1)
    # Replace the version argument with get_app_name()
    content = content.replace(
        'format!("{}/{}.exe", download_url, version)',
        'format!("{}/{}.exe", download_url, crate::get_app_name())'
    )
    changes += 1
    print("[fixUpdaterDownloadUrl] Patched Windows Sciter download URL format.")

if changes == 0 and old_fmt not in original:
    print("[fixUpdaterDownloadUrl] Format strings not found — source may have changed. No changes made.")
elif content == original:
    print("[fixUpdaterDownloadUrl] No changes needed.")
else:
    with open(UPDATER_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[fixUpdaterDownloadUrl] {changes} patch(es) applied to {UPDATER_PATH}.")
