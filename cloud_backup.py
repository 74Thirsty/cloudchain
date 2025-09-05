#!/usr/bin/env python3
"""
CloudChain for Google Drive — Single-Chain Backup Manager

Features:
- First run: only asks for LOCAL BACKUP ROOT.
- All state managed inside <LOCAL_ROOT>/cloud_backup/:
    client_secret.json, accounts.yaml, per-account dirs (token.json, uploads.yaml, mirrored files).
- Account naming enforced:
    <base><NNN>.cloudchain@gmail.com
    e.g., mybackup001.cloudchain@gmail.com, mybackup002.cloudchain@gmail.com
- On first account creation:
    Shows WARNING requiring suffix "001.cloudchain".
    User creates Gmail manually and confirms exact address.
    App extracts base and locks naming convention.
- On next account creation:
    Checks quota >=95% OR >=14.25 GB, computes required next email, warns, and verifies exact match.
- Remote path always Drive:/backup/
- Reset option wipes all data/config and exits.
"""

import os
import re
import json
import shutil
import webbrowser
from pathlib import Path
from typing import Dict, List, Tuple
import yaml
from datetime import datetime

import keyring
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

console = Console()

SCOPES = ["https://www.googleapis.com/auth/drive"]
SERVICE_NAME = "cloudchain"
INDEX_WIDTH = 3
REQUIRED_SUFFIX = "cloudchain"
RE_EMAIL_LOCAL = re.compile(rf"^(?P<base>.+?)(?P<idx>\d{{{INDEX_WIDTH}}})\.{REQUIRED_SUFFIX}$")
GMAIL_DOMAIN = "gmail.com"

MAX_BYTES = 15 * 1024**3
CUTOFF_BYTES = int(MAX_BYTES * 0.95)  # 14.25 GB


# ---------------- Keyring & Path helpers ---------------- #

def kr_get(key: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, key)

def kr_set(key: str, val: str) -> None:
    keyring.set_password(SERVICE_NAME, key, val)

def get_base_root() -> Path:
    base = kr_get("base_backup")
    if not base:
        root_input = Prompt.ask("Enter LOCAL BACKUP ROOT (CloudChain will create 'cloud_backup' here)")
        root = Path(root_input).expanduser().resolve()
        cloud_backup = root / "cloud_backup"
        cloud_backup.mkdir(parents=True, exist_ok=True)
        kr_set("base_backup", str(cloud_backup))
        return cloud_backup
    return Path(base).expanduser().resolve()

def reg_path() -> Path:
    return get_base_root() / "accounts.yaml"

def client_secret_path() -> Path:
    return get_base_root() / "client_secret.json"

def account_dir_local(account_local: str) -> Path:
    d = get_base_root() / account_local
    d.mkdir(parents=True, exist_ok=True)
    return d

def token_path(account_local: str) -> Path:
    return account_dir_local(account_local) / "token.json"

def ledger_path(account_local: str) -> Path:
    return account_dir_local(account_local) / "uploads.yaml"


# ---------------- Client secret management ---------------- #

def scaffold_client_secret() -> Dict:
    return {
        "installed": {
            "client_id": "DUMMY_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "cloudchain-local",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "DUMMY_SECRET",
            "redirect_uris": ["http://localhost"]
        }
    }

def ensure_client_secret_with_reset_prompt() -> Path:
    cpath = client_secret_path()
    if cpath.exists():
        return cpath
    console.print("[bold red]ALERT: client_secret.json is missing![/]")
    if not Confirm.ask("WIPE CloudChain state and reinitialize?"):
        console.print("[yellow]Exiting without changes.[/]")
        raise SystemExit(1)
    root = get_base_root()
    for item in [reg_path(), cpath]:
        if item.exists():
            if item.is_file():
                item.unlink(missing_ok=True)
            else:
                shutil.rmtree(item, ignore_errors=True)
    for sub in root.glob("*"):
        if sub.is_dir() and ((sub / "token.json").exists() or (sub / "uploads.yaml").exists()):
            shutil.rmtree(sub, ignore_errors=True)
    obj = scaffold_client_secret()
    cpath.write_text(json.dumps(obj, indent=2))
    os.chmod(cpath, 0o600)
    console.print(f"[green]client_secret.json scaffolded at {cpath}[/]")
    return cpath


# ---------------- Registry ---------------- #

def load_registry() -> Dict:
    rp = reg_path()
    if not rp.exists() or rp.stat().st_size == 0:
        return {}
    with rp.open() as f:
        return yaml.safe_load(f) or {}

def save_registry(reg: Dict) -> None:
    with reg_path().open("w") as f:
        yaml.safe_dump(reg, f, sort_keys=False)

def get_current_account_local() -> str:
    reg = load_registry()
    return reg["current_account"]

def get_chain_base(reg: Dict) -> str | None:
    return reg.get("chain_base")


# ---------------- Init flow ---------------- #

def _extract_local_and_domain(email: str) -> Tuple[str, str]:
    email = email.strip().lower()
    if "@" not in email:
        raise ValueError("Enter FULL Gmail (e.g., mybackup001.cloudchain@gmail.com)")
    local, domain = email.split("@", 1)
    return local, domain

def _validate_first_account(email: str) -> Tuple[str, str, int]:
    local, domain = _extract_local_and_domain(email)
    if domain != GMAIL_DOMAIN:
        raise ValueError(f"Domain must be {GMAIL_DOMAIN}")
    m = RE_EMAIL_LOCAL.match(local)
    if not m:
        raise ValueError("Username must end with 001.cloudchain")
    base = m.group("base")
    idx = int(m.group("idx"))
    if idx != 1:
        raise ValueError("First account must end with 001.cloudchain")
    return base, local, idx

def _format_local(chain_base: str, idx: int) -> str:
    return f"{chain_base}{idx:0{INDEX_WIDTH}d}.{REQUIRED_SUFFIX}"

def _required_email_for_next(reg: Dict) -> str:
    chain_base = reg["chain_base"]
    next_idx = len(reg["accounts"]) + 1
    return f"{_format_local(chain_base, next_idx)}@{GMAIL_DOMAIN}"

def sanity_and_init_if_needed() -> None:
    reg = load_registry()
    if reg.get("accounts"):
        ensure_client_secret_with_reset_prompt()
        return
    csp = client_secret_path()
    if not csp.exists():
        obj = scaffold_client_secret()
        csp.write_text(json.dumps(obj, indent=2))
        os.chmod(csp, 0o600)
        console.print(f"[green]Initialized client_secret.json at {csp}[/]")
    console.print("\n[bold red]WARNING: Gmail username MUST end with '001.cloudchain'[/]")
    console.print("Example: mybackup001.cloudchain@gmail.com\n")
    input("Press Enter to continue to Google signup...")
    webbrowser.open("https://accounts.google.com/signup")
    email = Prompt.ask("Enter EXACT Gmail you created").strip()
    try:
        chain_base, local_first, idx = _validate_first_account(email)
    except Exception as e:
        console.print(f"[red]ERROR:[/] {e}")
        input("Press any key to exit...")
        raise SystemExit(1)
    new_reg = {
        "chain_base": chain_base,
        "domain": GMAIL_DOMAIN,
        "suffix": REQUIRED_SUFFIX,
        "accounts": [local_first],
        "current_account": local_first,
    }
    save_registry(new_reg)
    account_dir_local(local_first)
    if not ledger_path(local_first).exists():
        with ledger_path(local_first).open("w") as f:
            yaml.safe_dump([], f)
    console.print(f"[green]Setup complete.[/] First account: {email}")


# ---------------- Google Drive helpers ---------------- #

def build_service(account_local: str):
    cpath = ensure_client_secret_with_reset_prompt()
    creds = None
    tpath = token_path(account_local)
    if tpath.exists():
        creds = Credentials.from_authorized_user_file(str(tpath), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(cpath), SCOPES)
            creds = flow.run_local_server(port=0)
        with tpath.open("w") as f:
            f.write(creds.to_json())
        os.chmod(tpath, 0o600)
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def get_root_id(service) -> str:
    about = service.about().get(fields="rootFolderId").execute()
    return about["rootFolderId"]

def get_backup_folder(service) -> str:
    root_id = get_root_id(service)
    resp = service.files().list(
        q=f"name='backup' and mimeType='application/vnd.google-apps.folder' and '{root_id}' in parents and trashed=false",
        fields="files(id,name)"
    ).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": "backup", "mimeType": "application/vnd.google-apps.folder", "parents": [root_id]}
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]

def upload_file(service, local_path: Path, parent_id: str):
    media = MediaFileUpload(str(local_path), resumable=True)
    body = {"name": local_path.name, "parents": [parent_id]}
    request = service.files().create(body=body, media_body=media, fields="id,name,size")
    with Progress(TextColumn("[bold]Uploading[/]"), BarColumn(), TimeRemainingColumn(), transient=True, console=console) as progress:
        task = progress.add_task(local_path.name, total=os.path.getsize(local_path))
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress.update(task, completed=status.resumable_progress)
    return response

def check_quota(account_local: str) -> Tuple[int, int, float]:
    service = build_service(account_local)
    about = service.about().get(fields="storageQuota").execute()
    quota = about.get("storageQuota", {})
    used = int(quota.get("usage", 0))
    limit = int(quota.get("limit", 1))
    pct = used / limit if limit else 0.0
    return used, limit, pct


# ---------------- Ledger ---------------- #

def load_ledger(account_local: str) -> List[Dict]:
    p = ledger_path(account_local)
    if p.exists():
        with p.open() as f:
            return yaml.safe_load(f) or []
    return []

def save_ledger(account_local: str, rows: List[Dict]) -> None:
    with ledger_path(account_local).open("w") as f:
        yaml.safe_dump(rows, f, sort_keys=False)


# ---------------- Commands ---------------- #

def show_current_account():
    reg = load_registry()
    if not reg.get("accounts"):
        console.print("[yellow]No account recorded yet.[/]")
        return
    account = reg["current_account"]
    console.print(f"[cyan]Current account:[/] {account}@{reg.get('domain','gmail.com')}")
    console.print(f"Local backup folder: {account_dir_local(account)}")

def switch_account():
    reg = load_registry()
    accts = reg.get("accounts", [])
    if not accts:
        console.print("[yellow]No accounts available.[/]")
        return
    console.print("Available accounts:")
    for idx, acc in enumerate(accts, start=1):
        console.print(f"  {idx}) {acc}@{reg.get('domain','gmail.com')}")
    choice = Prompt.ask("Enter account number to switch")
    try:
        idx = int(choice) - 1
        reg["current_account"] = accts[idx]
        save_registry(reg)
        console.print(f"[green]Switched to {reg['current_account']}[/]")
    except Exception:
        console.print("[red]Invalid choice[/]")

def upload_file_for_account():
    reg = load_registry()
    account = reg["current_account"]
    service = build_service(account)
    backup_id = get_backup_folder(service)
    local_file = Path(Prompt.ask("Enter path to file to upload")).expanduser().resolve()
    if not local_file.exists():
        console.print("[red]File not found[/]")
        return
    response = upload_file(service, local_file, backup_id)
    record = {
        "name": response.get("name"),
        "id": response.get("id"),
        "size": response.get("size"),
        "uploaded_from": str(local_file),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    ledger = load_ledger(account)
    ledger.append(record)
    save_ledger(account, ledger)
    dest = account_dir_local(account) / local_file.name
    dest.write_bytes(local_file.read_bytes())
    console.print(f"[green]Uploaded[/] {local_file} → Drive:/backup/ and local mirror {dest}")

def sync_local_backup_to_cloud():
    reg = load_registry()
    account = reg["current_account"]
    files = [p for p in account_dir_local(account).rglob("*") if p.is_file()]
    if not files:
        console.print("[yellow]Local backup folder is empty[/]")
        return
    mode = Prompt.ask("Sync mode: [m]erge or [o]verwrite?", choices=["m", "o"], default="m")
    service = build_service(account)
    backup_id = get_backup_folder(service)
    ledger = load_ledger(account)
    ledger_names = {r["name"] for r in ledger}
    uploaded = 0
    for f in files:
        if mode == "m" and f.name in ledger_names:
            continue
        response = upload_file(service, f, backup_id)
        record = {
            "name": response.get("name"),
            "id": response.get("id"),
            "size": response.get("size"),
            "uploaded_from": str(f),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        ledger.append(record)
        uploaded += 1
    save_ledger(account, ledger)
    console.print(f"[green]Sync complete.[/] Files uploaded: {uploaded}")

def show_local_backup():
    reg = load_registry()
    account = reg.get("current_account")
    if not account:
        console.print("[yellow]No account recorded yet.[/]")
        return
    folder = account_dir_local(account)
    items = list(folder.rglob("*"))
    if not items:
        console.print(f"[yellow]Local backup folder for {account} is empty[/]")
        return
    table = Table(title=f"Local Backup for {account}")
    table.add_column("Type"); table.add_column("Path")
    for p in items:
        table.add_row("FILE" if p.is_file() else "DIR", str(p.relative_to(folder)))
    console.print(table)

def list_cloud_contents():
    reg = load_registry()
    account = reg.get("current_account")
    if not account:
        console.print("[yellow]No account recorded yet.[/]")
        return
    ledger = load_ledger(account)
    if not ledger:
        console.print("[yellow]No uploads recorded for this account[/]")
        return
    table = Table(title=f"Cloud Ledger for {account}")
    table.add_column("Name"); table.add_column("Size"); table.add_column("Uploaded From"); table.add_column("When")
    for rec in ledger:
        table.add_row(rec["name"], str(rec.get("size", "")), rec.get("uploaded_from", ""), rec.get("timestamp", ""))
    console.print(table)

def create_next_account():
    reg = load_registry()
    if not reg.get("accounts"):
        console.print("[red]No chain exists yet.[/]")
        return
    current_local = reg["current_account"]
    used, limit, pct = check_quota(current_local)
    gb_used = used / (1024**3)
    gb_limit = limit / (1024**3)
    console.print(f"[cyan]Quota:[/] {gb_used:.2f} GB / {gb_limit:.2f} GB ({pct*100:.1f}%)")
    if pct < 0.95 and used < CUTOFF_BYTES:
        console.print("[yellow]Current account not full enough.[/]")
        return
    required_email = _required_email_for_next(reg)
    console.print("\n[bold red]WARNING: You MUST create this Gmail EXACTLY:[/]")
    console.print(f"    [cyan]{required_email}[/]")
    input("Press Enter to continue to Google signup...")
    webbrowser.open("https://accounts.google.com/signup")
    actual = Prompt.ask("Enter EXACT Gmail you created").strip().lower()
    if actual != required_email.lower():
        console.print(f"[red]ERROR: Expected {required_email}, got {actual}[/]")
        input("Press any key to exit...")
        raise SystemExit(1)
    new_local, _ = actual.split("@", 1)
    reg["accounts"].append(new_local)
    reg["current_account"] = new_local
    save_registry(reg)
    account_dir_local(new_local)
    if not ledger_path(new_local).exists():
        save_ledger(new_local, [])
    console.print(f"[green]Account added:[/] {actual}")

def reset_cloudchain():
    root = get_base_root()
    console.print("\n[bold red]WARNING: This will WIPE ALL CloudChain data under[/] "
                  f"[cyan]{root}[/]\n"
                  "[bold]This includes accounts.yaml, client_secret.json, tokens, ledgers, and local mirrors.[/]")
    if not Confirm.ask("Are you ABSOLUTELY sure?"):
        console.print("[yellow]Reset cancelled.[/]")
        return
    for item in [reg_path(), client_secret_path()]:
        if item.exists():
            if item.is_file():
                item.unlink(missing_ok=True)
            else:
                shutil.rmtree(item, ignore_errors=True)
    for sub in root.glob("*"):
        if sub.is_dir() and ((sub / "token.json").exists() or (sub / "uploads.yaml").exists()):
            shutil.rmtree(sub, ignore_errors=True)
    for key in ["base_backup", "chain_base"]:
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except Exception:
            pass
    console.print("[green]CloudChain reset complete. Restart the app to reinitialize.[/]")
    raise SystemExit(0)


# ---------------- Menu ---------------- #

def interactive():
    banner = r"""▄▖▜      ▌▄▖▌   ▘    ▐▘              ▜      ▌  ▘      
▌ ▐ ▛▌▌▌▛▌▌ ▛▌▀▌▌▛▌  ▜▘▛▌▛▘  ▛▌▛▌▛▌▛▌▐ █▌  ▛▌▛▘▌▌▌█▌  
▙▖▐▖▙▌▙▌▙▌▙▖▌▌█▌▌▌▌  ▐ ▙▌▌   ▙▌▙▌▙▌▙▌▐▖▙▖  ▙▌▌ ▌▚▘▙▖▗ 
                             ▄▌    ▄▌                 """
    disclaimer = "[bold red]DISCLAIMER:[/] DO NOT VIOLATE Google’s Terms."
    while True:
        console.print(f"[bold cyan]{banner}[/]")
        console.print("[bold white]        CloudChain for Google Drive[/]")
        console.print("-" * 60)
        console.print(disclaimer)
        console.print("-" * 60)
        console.print("\n[bold cyan]Main Menu[/]:")
        console.print("  1) Show current account")
        console.print("  2) Switch account")
        console.print("  3) Upload file")
        console.print("  4) Sync local backup to cloud")
        console.print("  5) Show local backup")
        console.print("  6) List cloud contents (ledger)")
        console.print("  7) Create next account (when full)")
        console.print("  8) Quit")
        console.print("  9) Reset CloudChain (WIPE ALL DATA)")
        choice = Prompt.ask("Select", default="8")
        if choice == "1": show_current_account()
        elif choice == "2": switch_account()
        elif choice == "3": upload_file_for_account()
        elif choice == "4": sync_local_backup_to_cloud()
        elif choice == "5": show_local_backup()
        elif choice == "6": list_cloud_contents()
        elif choice == "7": create_next_account()
        elif choice == "8": break
        elif choice == "9": reset_cloudchain()
        else: console.print("[red]Invalid choice[/]")


# ---------------- Main ---------------- #

if __name__ == "__main__":
    sanity_and_init_if_needed()
    interactive()

