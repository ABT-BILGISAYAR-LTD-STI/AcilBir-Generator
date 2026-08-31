import os
import json
import sys
import re
import base64

def extract_notary_credentials(raw):
    raw = raw.strip()
    data = {}

    # Strategy 1: Try Base64 decode
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        data = json.loads(decoded, strict=False)
    except Exception:
        pass

    # Strategy 2: Try JSON with strict=False (allows unescaped control chars / literal newlines)
    if not isinstance(data, dict) or not data.get("key_id"):
        try:
            data = json.loads(raw, strict=False)
        except Exception:
            pass

    # Extract fields from dict if available
    key_id = data.get("key_id", "").strip() if isinstance(data, dict) else ""
    issuer_id = data.get("issuer_id", "").strip() if isinstance(data, dict) else ""
    private_key = data.get("private_key", "").strip() if isinstance(data, dict) else ""

    # Strategy 3: Robust regex fallback (handles any format, unescaped newlines, missing quotes)
    if not key_id:
        m = re.search(r'["\']?key_id["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]+)["\']?', raw, re.IGNORECASE)
        if m:
            key_id = m.group(1).strip()

    if not issuer_id:
        m = re.search(r'["\']?issuer_id["\']?\s*[:=]\s*["\']?([a-f0-9-]+)["\']?', raw, re.IGNORECASE)
        if m:
            issuer_id = m.group(1).strip()

    if not private_key or "BEGIN PRIVATE KEY" not in private_key:
        m = re.search(r'(-----BEGIN PRIVATE KEY-----[\s\S]+?-----END PRIVATE KEY-----)', raw)
        if m:
            private_key = m.group(1).strip()

    return key_id, issuer_id, private_key

def main():
    raw = os.environ.get("NOTARIZE_JSON", "").strip()
    if not raw:
        print("[setup_notary] NOTARIZE_JSON is empty, skipping notary setup.")
        sys.exit(0)

    key_id, issuer_id, private_key = extract_notary_credentials(raw)

    if not key_id or not issuer_id or not private_key:
        print(f"[setup_notary] Error: Could not extract full credentials. key_id={bool(key_id)}, issuer_id={bool(issuer_id)}, private_key={bool(private_key)}")
        sys.exit(1)

    out_dir = "/tmp/apple_notary"
    os.makedirs(out_dir, exist_ok=True)

    p8_path = os.path.join(out_dir, "AuthKey.p8")
    with open(p8_path, "w", encoding="utf-8") as f:
        f.write(private_key + "\n")

    env_path = os.path.join(out_dir, "credentials.env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"KEY_ID={key_id}\n")
        f.write(f"ISSUER_ID={issuer_id}\n")

    print(f"[setup_notary] Successfully extracted Apple Notary credentials (Key ID: {key_id}, Issuer ID: {issuer_id}).")

if __name__ == "__main__":
    main()
