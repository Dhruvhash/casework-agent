"""Report each verifiable TigerGraph connection stage without false success."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main() -> int:
    host = os.getenv("TG_HOST", "").rstrip("/")
    graph = os.getenv("TG_GRAPHNAME", "")
    token = os.getenv("TG_API_TOKEN", "")
    secret = os.getenv("TG_SECRET", "")
    username = os.getenv("TG_USERNAME", "")
    password = os.getenv("TG_PASSWORD", "")
    if not host or not graph or not (secret or token or (username and password)):
        print("Application configuration: INCOMPLETE")
        print("Set TG_HOST, TG_GRAPHNAME, and TG_SECRET (or TG_API_TOKEN or username/password) in .env")
        return 2
    if urlparse(host).scheme not in {"http", "https"}:
        print("TigerGraph host: INVALID URL; TG_HOST must begin with https:// or http://")
        return 2
    headers = {"Authorization": f"Bearer {token}"} if token else ({"Authorization": f"GSQL-Secret {secret}"} if secret else {})
    auth = None if (token or secret) else (username, password)
    session = requests.Session()
    # Some local development shells have a stale proxy configured. The Savanna
    # workspace is reached directly over HTTPS; do not mistake proxy failure
    # for an invalid TigerGraph credential.
    session.trust_env = False
    try:
        response = session.get(f"{host}/restpp/echo", headers=headers, auth=auth, timeout=15)
    except requests.RequestException as exc:
        print(f"TigerGraph HTTP: NOT CONNECTED ({type(exc).__name__}: {exc})")
        return 1
    if response.status_code in (401, 403):
        print(f"TigerGraph HTTP: AUTH FAILED ({response.status_code}); check TG_API_TOKEN or username/password")
        return 1
    if not response.ok:
        print(f"TigerGraph HTTP: FAILED ({response.status_code}); verify workspace URL and REST endpoint")
        return 1
    print("TigerGraph HTTP: CONNECTED")
    try:
        response = session.get(f"{host}/restpp/endpoints/{graph}", headers=headers, auth=auth, timeout=15)
    except requests.RequestException as exc:
        print(f"Graph endpoints: NOT REACHABLE ({type(exc).__name__}: {exc})")
        return 1
    if not response.ok:
        print(f"Graph endpoints: FAILED ({response.status_code}); verify TG_GRAPHNAME and graph permissions")
        return 1
    try:
        body = response.json()
    except ValueError:
        print("Graph endpoints: FAILED (response was not JSON)")
        return 1
    if body.get("error"):
        print(f"Graph endpoints: NOT READY ({body.get('code', 'unknown code')}: {body.get('message', 'unknown error')})")
        return 1
    print(f"Graph endpoints: REACHABLE ({graph})")
    transport = os.getenv("TG_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        import shutil
        if shutil.which("tigergraph-mcp"):
            print("TigerGraph MCP executable: FOUND; live MCP tool call still requires a client")
        else:
            print("TigerGraph MCP executable: MISSING; run pip install tigergraph-mcp")
            return 1
    elif transport == "http":
        url = os.getenv("TG_MCP_URL", "")
        if not url:
            print("TigerGraph MCP URL: MISSING; set TG_MCP_URL")
            return 1
        print(f"TigerGraph MCP URL: CONFIGURED ({url}); protocol handshake not yet verified")
    else:
        print("TigerGraph MCP transport: INVALID; use stdio or http")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
