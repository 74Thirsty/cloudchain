![Sheen Banner](https://raw.githubusercontent.com/74Thirsty/74Thirsty/main/assets/banner.svg)

# CloudChain

> **Single-Chain Google Drive Backup Manager**
> Deterministic, account-chain backups — portable, auditable, and infinitely expandable.
> **⚠️ DO NOT USE in any attempt to bypass Google’s Terms of Service.**

---

## 🖥️ Platform Support

✅ Linux  ✅ macOS  ✅ Windows

---

## 🚀 Overview

CloudChain is a command-line backup manager that chains together multiple Google Drive accounts into one seamless system. It enforces a **strict naming convention** and **quota-based rollover** so your backups are structured, predictable, and never hit a dead end.

* Sequential Gmail accounts (`<base><NNN>.cloudchain@gmail.com`) extend storage deterministically.
* Everything lives in a **single local root** (`cloud_backup/`).
* Encrypted app-state backups (`.ccbak`) let you move between machines with zero logins.
* Color-coded TUI: instantly see which files are cloud-only, local-only, or mirrored both.

---

## 📂 Local Directory Structure

```
<LOCAL_ROOT>/cloud_backup/
├── accounts.yaml             # Account chain state
├── <base>001.cloudchain/     # Per-account directory
│   ├── token.json
│   ├── uploads.yaml          # Cloud ledger (self-healing local flags)
│   └── mirrored files...
└── ...
```

---

## 🔗 Account Naming

CloudChain enforces predictable Gmail usernames:

```
<basename>001.cloudchain@gmail.com
```

* First account must end with `001.cloudchain`.
* Each new account increments numerically (`002`, `003`, …).
* Base string (`mybackup`, `familydrive`) is locked at initialization.
* At **≥95% quota or ≥14.25 GB**, CloudChain requires the next sequential account.

---

## ☁️ Remote Storage

Every account uses the fixed path:

```
Drive:/backup/
```

No custom folders. No scattered files. Just one clean namespace.

---

## 🔧 Features

### Application State Portability

* **Export**: Saves accounts, tokens, ledgers, and config into an encrypted `.ccbak` file.
* **Restore**: Decrypts and rebuilds state on a new machine.
* Encryption: **AES-256-GCM + scrypt KDF**.
* On first run, CloudChain asks if you want to restore or start fresh.

### Backup & Sync

* **Upload**: Send any file to Drive:/backup/. Optionally mirror locally.
* **Download**: Pull cloud files back into the local mirror.
* **Sync (Local→Cloud)**: Push everything in local backup folder to Drive.
* **Sync (Cloud→Local)**: Ensure local mirror has all Drive files.

### Delete

* **Delete Local**: Remove mirrored copies while keeping them in Drive.
* **Delete Cloud**: Remove files from Drive and clean the ledger.

### Ledger

* **Self-healing local flags**: Cloud ledger auto-updates to reflect local reality.
* **Color-coded rows** (UNC theme):

  * Wolf Gray → Cloud only
  * Navy Blue → Local only
  * Carolina Blue → Both present

### Menus

* Sub-menus: **Accounts**, **Cloud**, **Local**, **System**.
* Stable screens — waits for confirmation so messages don’t vanish.
* Styled UI in Tar Heel colors across panels, menus, and ledgers.

---

## 🛠️ Usage

**1. Initialize**

```bash
cloudchain init
```

**2. Upload a file**

```bash
cloudchain upload ~/Documents/file.txt
```

**3. Download or sync**

```bash
cloudchain download
cloudchain sync --local-to-cloud
cloudchain sync --cloud-to-local
```

**4. Export state**

```bash
cloudchain export
# Produces cloudchain_state_20250906T123000Z.ccbak
```

**5. Restore state**

```bash
cloudchain restore /path/to/cloud_backup/
```

**6. Reset**

```bash
cloudchain reset
```

---

## 📖 Example Session

```bash
# Initialize chain
cloudchain init
> Enter LOCAL_ROOT: ~/Backups
> Confirm first account: mybackup001.cloudchain@gmail.com

# Upload a file
cloudchain upload ~/Music/song.mp3
> Uploaded … mirrored locally at ~/Backups/cloud_backup/mybackup001.cloudchain/song.mp3

# View ledger (colors applied)
Name           Size     Uploaded From     When                       Local Mirror
─────────────  ───────  ────────────────  ─────────────────────────  ───────────
song.mp3       4 MB     ~/Music/song.mp3  2025-09-06T12:34:56Z       Yes (blue)

# Export app state
cloudchain export
> Application state exported: ~/Backups/cloud_backup/cloudchain_state_20250906T123456Z.ccbak
```

---

## 💻 Windows Notes

* Python 3.9+ required.
* Keyring integrates with Windows Credential Manager.
* OAuth flow opens in your browser.
* Paths look like:

  ```
  C:\Users\You\CloudChainBackups\cloud_backup
  ```

---

## 🛡️ Philosophy

CloudChain is opinionated. It trades “freedom” for **discipline**:

* No ad-hoc accounts.
* No mystery folders.
* No hidden state.
  Just a deterministic, portable backup chain you can **audit at a glance**.

---

## 📜 License

This project is licensed under the [CloudChain License](LICENSE.md).
© 2025 Christopher Hirschauer. All rights reserved.

---

## ☕ Support Development

* **ETH:** `0xC6139506fa54c450948D9D2d8cCf269453A54f17`
* **PayPal:** [paypal.me/obeymythirst](https://www.paypal.me/obeymythirst)
