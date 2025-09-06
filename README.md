![Sheen Banner](https://raw.githubusercontent.com/74Thirsty/74Thirsty/main/assets/gunfire.svg)

# CloudChain

> **Single-Chain Google Drive Backup Manager**
> A deterministic, account-chain approach to managing unlimited Google Drive backups.
> **⚠️ DO NOT USE in any attempt to bypass Google’s Terms of Service.**

---

## 🖥️ Platform Support

✅ Linux  ✅ macOS  ✅ Windows

---

## 🚀 Overview

CloudChain is a command-line backup manager that chains together multiple Google Drive accounts into one seamless backup system. Instead of random juggling, CloudChain enforces a **strict naming convention** and **quota-based rotation** so your backups are deterministic, auditable, and infinitely expandable.

* Uses sequential Gmail accounts (`<base><NNN>.cloudchain@gmail.com`) to extend storage.
* Self-contained: all metadata, configs, and tokens live inside a single **local root**.
* Deterministic rules: account naming and quota rollover are enforced by code.

---

## 📂 Local Directory Structure

When you first run CloudChain, it prompts for your local backup root (`LOCAL_ROOT`).
It then creates:

```
<LOCAL_ROOT>/cloud_backup/
├── client_secret.json        # OAuth credentials
├── accounts.yaml             # Account chain state
├── <base>001.cloudchain/     # Per-account directory
│   ├── token.json
│   ├── uploads.yaml
│   └── mirrored files...
└── ...
```

Everything lives here. Nothing is scattered elsewhere.

---

## 🔗 Account Naming

CloudChain locks you into a single, predictable naming scheme:

```
<basename>001.cloudchain@gmail.com
```

* The **first account must end in `001.cloudchain`**.
* Each new account increments numerically (`002`, `003`, …).
* The base string (e.g., `mybackup`, `familydrive`) is locked at initialization.

If quota hits **≥95% OR ≥14.25 GB**, CloudChain warns you and requires the **next sequential account**.

---

## ☁️ Remote Storage

Every account in the chain mirrors the same path:

```
Drive:/backup/
```

This location is fixed and cannot be changed.

---

## 🔧 Usage

**1. Initialize**

```bash
cloudchain init
```

* Prompts for local backup root.
* Enforces `<base>001.cloudchain` account.

**2. Add a new account**

```bash
cloudchain add
```

* Checks quota of last account.
* Requires exact next Gmail (e.g., `<base>002.cloudchain@gmail.com`).

**3. Backup files**

```bash
cloudchain backup /path/to/files
```

**4. Reset all state**

```bash
cloudchain reset
```

* Wipes local configs/state and exits.
* Does **not** touch remote Drive data.

---

## ⚠️ Warnings

* Do not deviate from the naming scheme. Mismatches are rejected.
* You must manually create each Gmail account before linking it.
* Drive quota is finite: CloudChain only detects rollover, it cannot expand a single account.

---

## 🛠️ Philosophy

CloudChain eliminates cloud chaos by enforcing discipline:

* No ad-hoc accounts
* No mystery folders
* No hidden state

Just a clean, deterministic chain of accounts you can **audit at a glance**.

---

## 📖 Quick Example Session

Here’s what using CloudChain looks like in practice:

```bash
# Step 1: Initialize
cloudchain init
> Enter LOCAL_ROOT: /home/you/Backups
> Confirm first account: mybackup001.cloudchain@gmail.com

# Step 2: Backup files
cloudchain backup ~/Documents/Taxes
> Uploading… 1.2 GB complete
> Account quota: 12.8 GB / 15 GB

# Step 3: Quota warning (≥95% OR ≥14.25 GB)
cloudchain backup ~/Photos
> Quota reached on mybackup001.cloudchain@gmail.com
> Please create next account: mybackup002.cloudchain@gmail.com

# Step 4: Add the new account
cloudchain add
> Confirm next account: mybackup002.cloudchain@gmail.com
> Linked successfully.

# Step 5: Continue backup
cloudchain backup ~/Photos
> Uploading to mybackup002.cloudchain@gmail.com
> Complete.
```

At the end, you’ve got a **chain of accounts** (`mybackup001`, `mybackup002`, …) all stitched together, each continuing where the last left off.

---

## 💻 Windows Ready

Yes — CloudChain works on Windows as well as Linux/macOS. A few notes:

* **Python Support**
  Install Python 3.9+ on Windows (from [python.org](https://www.python.org/downloads/)) and use `pip install -r requirements.txt` to set up dependencies.

* **Local Storage Path**
  On Windows, your `LOCAL_ROOT` might look like:

  ```
  C:\Users\YourName\CloudChainBackups
  ```

  CloudChain will still create its `cloud_backup/` subfolder there.

* **Keyring Backend**
  CloudChain uses the `keyring` library. On Windows, this integrates with **Windows Credential Manager**, so tokens are stored securely without extra setup.

* **OAuth Browser Flow**
  When authorizing Google Drive access, your default browser will pop open just like on Linux.

* **PowerShell / Command Prompt**
  Use commands like this:

  ```powershell
  cloudchain init
  cloudchain backup C:\Users\YourName\Documents
  ```

## License

This project is licensed under the [CloudChain License](./LICENSE).  
Copyright © 2025 Christopher Hirschauer. All rights reserved.
