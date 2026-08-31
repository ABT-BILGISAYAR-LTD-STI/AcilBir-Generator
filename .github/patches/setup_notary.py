import os
import json
import sys
import base64

def main():
    raw = os.environ.get("NOTARIZE_JSON", "").strip()
    if not raw:
        print("[setup_notary] NOTARIZE_JSON is empty, skipping notary setup.")
        sys.exit(0)

    data = None
    # 1. Try decoding as base64 first
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        data = json.loads(decoded)
    except Exception:
        pass

    # 2. Try parsing as raw JSON
    if data is None:
        try:
            data = json.loads(raw)
        except Exception as e:
            print(f"[setup_notary] Failed to parse NOTARIZE_JSON: {e}")
            sys.exit(0)

    key_id = data.get("key_id", "").strip()
    issuer_id = data.get("issuer_id", "").strip()
    private_key = data.get("private_key", "").strip()

    if not key_id or not issuer_id or not private_key:
        print("[setup_notary] Missing required fields (key_id, issuer_id, private_key).")
        sys.exit(0)

    out_dir = "/tmp/apple_notary"
    os.makedirs(out_dir, exist_ok=True)

    p8_path = os.path.join(out_dir, "AuthKey.p8")
    with open(p8_path, "w", encoding="utf-8") as f:
        f.write(private_key + "\n")

    env_path = os.path.join(out_dir, "credentials.env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"KEY_ID={key_id}\n")
        f.write(f"ISSUER_ID={issuer_id}\n")

    print(f"[setup_notary] Successfully extracted Apple Notary credentials (Key ID: {key_id}).")

if __name__ == "__main__":
    main()
