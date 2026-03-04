"""
One-time helper to get a refresh token for a PERSONAL Microsoft account (OneDrive personal).

Usage:
  1) Ensure your Azure app registration supports "Personal Microsoft accounts"
  2) Add delegated permissions: Files.ReadWrite, offline_access
  3) Set env:
       - AZURE_CLIENT_ID (or MS_CLIENT_ID)
       - MS_TENANT_ID=consumers  (recommended for personal accounts)
  4) Run:
       python ms_personal_auth_device_code.py
  5) Follow the prompt in the terminal and paste the refresh token into .env as:
       MS_REFRESH_TOKEN=...
"""

import os
import time
import requests


DEVICE_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/devicecode"
TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


def main() -> None:
    tenant = os.getenv("MS_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "consumers"
    client_id = os.getenv("MS_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
    if not client_id:
        raise SystemExit("Missing MS_CLIENT_ID/AZURE_CLIENT_ID in env")

    # For Excel workbook APIs, Files.ReadWrite is usually sufficient (file-based access).
    scope = os.getenv("MS_DEVICE_CODE_SCOPE", "offline_access Files.ReadWrite")

    device = requests.post(
        DEVICE_URL_TMPL.format(tenant=tenant),
        data={"client_id": client_id, "scope": scope},
        timeout=30,
    )
    device.raise_for_status()
    d = device.json()

    print("\nOpen this URL and enter the code:")
    print(f"  URL : {d['verification_uri']}")
    print(f"  Code: {d['user_code']}\n")
    print(d.get("message", ""))

    interval = int(d.get("interval", 5))
    expires_in = int(d.get("expires_in", 900))
    deadline = time.time() + expires_in

    while time.time() < deadline:
        time.sleep(interval)
        token = requests.post(
            TOKEN_URL_TMPL.format(tenant=tenant),
            data={
                "client_id": client_id,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": d["device_code"],
            },
            timeout=30,
        )

        if token.status_code == 200:
            t = token.json()
            refresh_token = t.get("refresh_token")
            if not refresh_token:
                raise SystemExit(f"Got token response but no refresh_token: {t}")
            print("\n✅ SUCCESS")
            print("Set this in your hco-agent/.env:")
            print(f"MS_TENANT_ID=consumers")
            print(f"MS_REFRESH_TOKEN={refresh_token}\n")
            return

        # Expected pending responses
        try:
            err = token.json()
        except Exception:
            err = {"error": token.text}

        if err.get("error") in ("authorization_pending", "slow_down"):
            continue

        raise SystemExit(f"Device code flow failed: {err}")

    raise SystemExit("Device code expired. Run again.")


if __name__ == "__main__":
    main()


