# GitHub Sync

Keep the same Brain on several computers through a **private GitHub repository you own**, similar to the Obsidian Git plugin. Notes travel only between your computers and GitHub. Notryn has no server that receives your notes or your token, and no Notryn account is needed.

GitHub Sync is free during the beta. It may become an optional paid feature in the future to support development. If it does, it will be very affordable, with a one-time option, and the rest of Notryn stays free. Your notes and repository always stay yours.

Step-by-step help: https://notryn.com/sync.html

## Requirements

- Notryn 0.2.0-beta.12 or newer.
- Git 2.31 or newer on each computer. macOS: `xcode-select --install`. Linux: `sudo apt install git`, `sudo dnf install git` or `sudo pacman -S git`.
- A GitHub account.
- A Brain with **Read and write** access (sync changes files).

## First computer

1. On GitHub, [create a private repository](https://github.com/new?name=notryn-brain&visibility=private). Any name. Leave it empty, without a README.
2. [Create a fine-grained personal access token](https://github.com/settings/personal-access-tokens/new?name=Notryn%20Sync&expires_in=365&contents=write):
   - **Repository access:** *Only select repositories* → your Brain repository.
   - **Permissions → Repository → Contents:** *Read and write*. Nothing else is needed (GitHub adds *Metadata: read* automatically).
   - Pick an expiry you are comfortable with. When it expires, create a new token and connect again.
3. In Notryn, open **GitHub Sync**: the cloud button in the top bar, the card in **Your Brains**, the command palette, or press **Y**.
4. Paste the token and press **Connect**. Notryn checks it with GitHub and shows the account it belongs to.
5. Enter the repository (`your-name/notryn-brain` or its GitHub URL), choose the schedule and press **Start syncing**. Your notes are sent on the first sync.

## Notes already on GitHub (for example Obsidian Git)

You do not need a new repository:

1. Open the folder with your notes in Notryn (**Your Brains → Open a folder**, *Read and write*), unless it is already a Brain.
2. Create the token as above, choosing **your existing repository** under *Only select repositories*.
3. In **GitHub Sync**, connect the token and type your existing repository (`your-name/my-notes`), then **Start syncing**.

Nothing is overwritten; both sides are merged. Notryn syncs the repository's main (default) branch; if the folder is checked out on another branch, it stops and asks you to switch first. Notryn adds its own `notryn` remote and leaves `origin` and Obsidian Git alone. If Obsidian Git also runs on the same computer, turn off its automatic sync so both apps do not sync at the same moment.

## Every other computer

1. Install Notryn and Git.
2. Create an empty Brain where you want the notes to live (or open the folder you want to merge).
3. Open **GitHub Sync**, connect a token (the same one, or a new one for that computer) and choose the **same repository**. Your notes arrive on the first sync.

If the folder already had notes, both sides are merged: nothing is overwritten.

## Several Brains

Each Brain syncs with its own repository, and you can sync as many as you like. For a new Brain, create another private repository (or use an existing one), add it to your token on GitHub (open the token → **Edit** → add the repository → save), then open GitHub Sync in that Brain and type its repository. The token on this computer does not need to be reconnected.

## How a sync works

Each sync, for one Brain:

1. Records every change in the Brain folder (new, edited, renamed, moved and removed files) as a commit.
2. Downloads changes from GitHub and merges them.
3. Sends the result back to GitHub.

Notryn syncs:

- when it opens, if **Sync when Notryn opens** is on;
- every 5, 10, 15, 30 or 60 minutes while it is open, if you choose a schedule;
- when you press **Sync now** in the dialog or **Shift Y** anywhere.

The top bar's cloud shows a green dot when the current Brain is synced, amber while syncing and red when the last sync failed. Hover it for the last sync time. The library refreshes automatically when changes arrive. Save the note you are editing before pressing **Sync now**; if a scheduled sync changes a note while you edit it, Notryn's usual conflict protection keeps your draft.

### Conflicts never lose an edit

If two computers change the same note before syncing, Notryn keeps **this computer's version** in place and saves the other version next to it as `Note (GitHub copy 2026-10-02 1530).md`. Compare the two, keep what you want and remove the copy. If one computer edited a note that the other removed, the edited note is kept.

Notryn never leaves Git conflict markers (`<<<<<<<`) in your notes.

### Stop syncing

**Stop syncing** in the dialog keeps every note in the folder and on GitHub, and keeps the history in the folder's `.git` directory. Notryn simply stops talking to GitHub for that Brain. **Disconnect** removes the token from this computer.

## Security and privacy

- **The token is stored by your operating system:** macOS Keychain, or the Secret Service keyring (GNOME Keyring, KWallet) on Linux. When no keyring is available it is saved in a file readable only by your user (`0600`, inside a `0700` folder in Notryn's private state).
- **It is never shown again**, never returned to the interface, never written to the Brain folder, `.git/config`, the remote URL or logs, and never placed on a command line. Git receives it through environment-scoped configuration that only applies to `https://github.com/`.
- **Least privilege:** a fine-grained token limited to one repository and *Contents* is all Notryn needs. Notryn cannot see your other repositories.
- **Public repositories** require an explicit confirmation, because anyone could read the notes.
- Sync runs only from the local app. The private preview link (`share.py`) cannot read or change sync settings.
- Notryn commits use your Git identity if you have one, otherwise your GitHub *noreply* address. Pre-commit hooks and commit signing are skipped for Notryn's automatic commits, so a sync never waits for a passphrase.
- Revoke the token at any time in GitHub → Settings → Developer settings → Personal access tokens.

Sync is not a backup on its own: a note removed on one computer is removed on the others. GitHub keeps the full history, so earlier versions can be restored from the repository.

## Troubleshooting

| Message | What to do |
| --- | --- |
| Git is not installed | Install Git (see Requirements), then reopen the dialog. |
| GitHub did not accept the token | It expired or was revoked. Create a new token and connect again. |
| Repository not found | Check the name, and that the token's *Repository access* includes this repository. |
| GitHub refused the upload | Give the token *Contents: Read and write*. |
| A file is larger than GitHub allows | GitHub rejects files over 100 MB. Move the file out of the Brain folder. |
| This Brain must allow reading and writing | Change it in **Your Brains → Access**. |

Files Notryn ignores when syncing: its temporary save files (`.notryn-*`), `.DS_Store`, `Thumbs.db` and `desktop.ini`. Add your own patterns to the Brain's `.gitignore` if needed.
