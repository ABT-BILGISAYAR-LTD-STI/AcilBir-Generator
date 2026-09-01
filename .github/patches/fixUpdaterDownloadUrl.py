#!/usr/bin/env python3
"""
fixUpdaterDownloadUrl.py — No-op compatibility stub.
Dynamic asset URL resolution is natively handled in src/updater.rs (resolve_download_asset_url).
"""
import sys

def main():
    print("[fixUpdaterDownloadUrl] Native dynamic updater active. No legacy regex patch needed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
