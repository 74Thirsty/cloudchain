# CloudChain

> Single-Chain Google Drive Backup Manager A deterministic, account-chain approach to managing unlimited Google Drive backups. DO NOT USE IN AN ATTEMPT TO ABUSE TOC's.

---

## 🚀 Overview

CloudChain is a command-line backup manager designed to store files into a linked chain of Google accounts.
Instead of juggling random drives, CloudChain enforces a strict naming convention and quota-based rotation so your backups are always deterministic and infinitely expandable.
	
 	•	Uses sequential Gmail accounts (<base><NNN>.cloudchain@gmail.com) to extend storage when quotas are hit.
	•	Self-contained state: All metadata, configs, and tokens are managed inside a single local root folder.
	•	Deterministic rules: Naming and rotation are enforced by code, so you’ll never wonder which account is “next.”

---

## 📂 Local Directory Structure

On first run, you’ll be asked for your local backup root (LOCAL_ROOT).
CloudChain will create a state directory:

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

All state lives here. Nothing is hidden elsewhere.

⸻

## 🔗 Account Naming

CloudChain enforces a strict naming scheme:
```
<basename>001.cloudchain@gmail.com


	•	The very first account must end in 001.cloudchain.
	•	Each new account increments numerically (002, 003, …).
	•	Base string (mybackup, familydrive, etc.) is locked at first creation.
```

If quota reaches ≥95%, CloudChain warns you and requires the next sequential account.

---

## ☁️ Remote Storage

All files are uploaded to:
```
Drive:/backup/
```

This is fixed and cannot be changed. Every account in the chain mirrors the same folder structure.

---

## 🔧 Usage


1.	Initialize
 
```
cloudchain init
```

	•	Prompts for local backup root.
	•	Enforces base account naming (001.cloudchain).


2.	Add a new account
```
cloudchain add
```

	•	Checks last account’s quota.
	•	Requires next sequential Gmail (<base>002.cloudchain@gmail.com).



 3.	Backup files
```
cloudchain backup /path/to/files
```


 4.	Reset all state
```
cloudchain reset
```
	•	Wipes local configs and exits.
	•	Does not touch remote accounts.

---

## ⚠️ Warnings
	•	Do not deviate from naming scheme. The system will reject mismatches.
	•	Manual Gmail creation required. You must manually create each <base><NNN>.cloudchain@gmail.com before adding it.
	•	Drive quota is finite. CloudChain only detects when it’s time to roll over; it cannot expand a single account.
 
 ---

## 🛠️ Philosophy

CloudChain takes the chaos out of cloud backup by enforcing discipline:
	•	No ad-hoc accounts
	•	No mystery folders
	•	No hidden state

Just a clean, deterministic chain of accounts you can audit at a glance.
