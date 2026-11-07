# Server

The laptop makes the karaokes on its GPU and serves them to every device: the laptop itself (and
the TV plugged in over HDMI), the phones at home and, if you want, your devices away from home.
One program does all of it, `karaoke-server`, which runs inside WSL. The design decisions are in
[`plan-v3/decisiones/011-servidor.md`](plan-v3/decisiones/011-servidor.md) (in Spanish).

## The essentials

- **One command to start it**: `make serve`. Then, on the laptop, open <http://localhost:8765>.
- **Who can do what**:
  - The **laptop** can do everything.
  - A **phone on the home Wi-Fi** can browse the songs, sing them and start or join a party. To
    create, correct or delete songs it has to be **paired** once.
  - **Away from home** (through Tailscale) only paired devices get in.
  - Party **guests** join with the TV's QR code and can only ask for songs and act as a remote.
- **Pairing a device**: on the laptop, *Axustes → Este aparello → Vincular outro aparello*. An
  8-letter code (valid for 10 minutes, once) and a QR code appear. On the other device, scan the QR
  code or type the code in *Axustes*. `uv run karaoke-server pair` in the terminal works too.
- **Where everything lives**: `~/.local/share/karaoke/` (inside WSL):
  - `library/`: one folder per song, with the exported MP4 files in `exports/`.
  - `karaoke.db`: the database (jobs, devices, parties).
  - `jobs/`: what is being processed.
  - `trash/`: deleted songs; emptied automatically after 30 days.
  - `logs/`: the logs.

  It can be changed with `--data` or the `KARAOKE_DATA` variable.

## The first time

From the project's folder in WSL:

```bash
make install       # the engine with the GPU, the built web app, the Galician models and `doctor`
make serve
```

`make install` does, with checks, the same as these manual steps:

```bash
uv sync --extra ml --inexact          # the engine with the GPU (if not there yet)
pnpm --dir web build                  # the web app
uv run karaoke-server prepare --lang gl   # downloads the models (a few GB, once)
uv run karaoke-server doctor          # what is missing and how to fix it
```

`doctor` checks ffmpeg, the GPU, NVENC, the models, yt-dlp, the jobs' memory limit, the free disk
space, the built web app, the home network, Tailscale and starting with Windows. Every failure comes
with its fix.

If you already have packages made with `karaoke make`, add them to the library with:

```bash
uv run karaoke-server import path/to/package [another/package …]
```

## Letting the phones at home reach the laptop

By default WSL lives in an internal network (NAT) that phones cannot reach. While it stays that
way, the party TV says so under the code, and so does `doctor`. Two changes in Windows are needed,
**once**:

### 1. Put WSL in "mirrored" mode

1. In Windows, press `Win + R`, type `%UserProfile%` and press Enter. Your user folder opens.
2. Look for a file called `.wslconfig`. If it does not exist, create it: right click → *New → Text
   Document*, and name it `.wslconfig` (without `.txt` at the end; if Windows hides extensions, turn
   them on in *View → Show → File name extensions*).
3. Open it with Notepad and write this (if it already has a `[wsl2]` section, only add the
   `networkingMode` line under it):

   ```ini
   [wsl2]
   networkingMode=mirrored
   ```

4. Save and close.
5. Open **PowerShell** (Start menu → type "PowerShell") and run `wsl --shutdown`. Wait about 10
   seconds and open the Ubuntu terminal again.

### 2. Open port 8765 in the firewall, on private networks only

1. Start menu → type "PowerShell" → right click → **Run as administrator**.
2. Copy and paste this command (it is a single line):

   ```powershell
   New-NetFirewallHyperVRule -Name Karaoke -DisplayName "Karaoke (WSL)" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol TCP -LocalPorts 8765 -Profiles Private
   ```

3. Check that your home Wi-Fi is marked as **private**: *Settings → Network & internet → Wi-Fi →*
   (your network) *→ Network profile type → Private network*. On a public network (a bar, a train)
   the port stays closed, which is what we want.

Only the karaoke's port is opened, not the whole virtual machine.

### 3. Check it

1. Start the server (`make serve`) and run `uv run karaoke-server doctor`: the "home network" line
   must show ✓ and an address such as `http://192.168.1.38:8765`.
2. On the phone, connected to the same Wi-Fi, open that address. The library must appear.
3. If it does not load: check that the Wi-Fi is private (step 2.3) and that the phone is not on the
   router's guest network (it keeps devices apart).

## Away from home: Tailscale

Tailscale makes a private network between your devices and gives the laptop an `https://` address
with a real certificate. With HTTPS, the phone also gets what browsers only allow over secure
connections: songs saved for offline use, pitch shifting and keeping the screen on (which is why
it is worth using at home too).

1. In PowerShell (on Windows, no administrator needed):

   ```powershell
   tailscale serve --bg 8766
   ```

   Port 8766 is the server's door for tunnels: everything coming through it is treated as "from
   outside", even if someone on your Tailscale network opens it. If Tailscale asks you to turn on
   HTTPS for your network, follow the link it prints. **Do not point it at 8765**: `doctor` warns if
   that happens.
2. `uv run karaoke-server doctor` shows the address (`https://<laptop>.<your-network>.ts.net`).
3. On the phone, install the Tailscale app with the same account, open that address and pair the
   phone (at home, with the QR code in *Axustes*; or by typing the code).

To remove it: `tailscale serve --https=443 off`.

Party guests do not need Tailscale: they come in through the home Wi-Fi.

## Starting on its own

```bash
uv run karaoke-server autostart install    # creates a shortcut in Windows' Startup folder
uv run karaoke-server autostart status
uv run karaoke-server autostart remove
```

When you sign in to Windows, `scripts/serve-forever.sh` starts with no window: it starts the server
and starts it again 5 s after it stops. While it runs, WSL stays up. Its messages go to
`~/.local/share/karaoke/logs/forever.log`.

- **Settings** for the automatic start (such as the backup folder): in
  `~/.config/karaoke/server.env`, one setting per line, for example
  `KARAOKE_BACKUP_DIR=/mnt/d/KaraokeBackups`.
- **Stopping it**: `pkill -f "[k]araoke-server serve"` (it exits cleanly and the loop does not
  start it again). To start it again without signing out: `make serve`, or double click the
  "Karaoke server" shortcut in the Startup folder (`Win + R` → `shell:startup`).
- It starts **when you sign in**, not before. Starting it with nobody signed in would need the Task
  Scheduler with administrator rights.

### Power and the lid

If Windows puts the laptop to sleep, the server stops answering. For parties and for creating
karaokes from a phone:

- *Settings → System → Power → Screen, sleep and hibernate*: when plugged in, "Make my device
  sleep after" → **Never**.
- *Control Panel → Power Options → Choose what closing the lid does*: when plugged in, **Do
  nothing** (so you can close it with the TV connected).

## Backups

```bash
uv run karaoke-server backup --to /mnt/d/KaraokeBackups
```

It copies the database (live, without stopping anything) and the songs; the next time it only copies
what changed. Exported MP4 files are not copied (they can be made again). A song no longer in the
library is not deleted from the backup: it is moved to `_borrado/<date>/`. `/mnt/d/…` is Windows'
D: drive; a OneDrive or Google Drive folder works too.

With `KARAOKE_BACKUP_DIR` (in `~/.config/karaoke/server.env` or in the environment), the server makes
the backup by itself, once a day.

**Restoring**: with the server stopped, copy `karaoke.db` and `library/` from the backup to
`~/.local/share/karaoke/`.

## Creating karaokes

From *Crear* (the laptop or a paired device): an audio or video file, or a link. Limits: 2 GB, 20
minutes and 2 GB of free disk space left.

- **Links** are downloaded with yt-dlp, always at its latest release (`uvx` fetches it the first
  time; YouTube changes often and an old version stops working). It is best effort: some sites
  fail. Live streams and playlists are not accepted. The video comes at up to 1080p: the song keeps
  it as it came for the MP4 export (`master.mp4`, [`video.md`](video.md)) and the players get a
  lighter 720p copy.
- Jobs go through the GPU **one at a time**, each in its own process with a memory limit: if one runs
  out of memory, it dies and WSL does not. Downloads progress at the same time.
- A passing failure (out of memory, the process crashed) is retried once on its own. *Tentar de
  novo* retries without uploading the file again (the input is kept for 7 days).
- If the server stops with a job half done, it picks it up when it comes back.

Times on the RTX 3050 (`bench/results/2026-11-05-c8-servidor/`): a 4-minute song with lyrics,
about 90 s; without lyrics, about 110 s; exporting the MP4, about 25 s.

## Downloading

In the player, **Descargar** (the arrow at the top) lists the song's karaoke videos and lets the
laptop or a paired device make one (16:9 for the TV or YouTube, 9:16 for social media, in the
lyrics style chosen, with the guide vocals from none to the song as sung), with its progress live.
The GPU makes one thing at a time: a video waiting for its turn says so. Asking again for a video
that is already waiting or being made gives that same job, never a second copy. Anyone who can see the song can download the videos,
the music without vocals, the vocals and the synced lyrics. Files are saved under the song's name
(«Artist - Title (karaoke).mp4»). A video made before a correction of the lyrics is marked as
outdated.

- `GET /api/songs/{id}/exports`: the videos, newest first (`file`, `aspect`, `theme`, `vocals`,
  `size`, `created_at`, `thumbnail`, `outdated`); `DELETE /api/songs/{id}/exports/{name}` deletes
  one (owner). `POST /api/songs/{id}/exports` (`aspect`, `theme`, `vocals` from 0 to 1, in
  hundredths) makes one; its job carries the `song_id` from the start. Each shape, style and
  vocals level is a file of its own: `exports/<id>-<16x9|9x16>-<style>[-v<percent>].mp4`.
- `GET /media/{id}/{file}?download=1&name=…` sends any file of the package as an attachment, under
  that name: the server keeps only its last part, drops the characters no file system takes, cuts
  it to 120 characters and gives it the real file's extension.

## When something goes wrong

| What happens | What to do |
|---|---|
| The phone does not open the home address | `doctor`; check mirrored mode, the firewall rule and that the Wi-Fi is private |
| The party TV says phones cannot get in | the same: WSL is still in NAT |
| «Isto só se pode facer dende o portátil ou un aparello vinculado» | pair that device (*Axustes*) |
| A link fails to download | try later (yt-dlp updates itself) or download the file and upload it |
| A job fails | *Tentar de novo*; the job's log is at `GET /api/jobs/<id>/log` and in `~/.local/share/karaoke/jobs/<id>/log.txt` |
| The server does not start | `~/.local/share/karaoke/logs/server.log` and `forever.log`; is another program using 8765? (`ss -ltnp \| grep 8765`) |
| Unpair a lost device | *Axustes → Aparellos vinculados*, or `uv run karaoke-server devices --revoke <id>` |

## For development

- `pnpm --dir web dev` uses the stand-in server (`web/dev/mock/`). With
  `KARAOKE_SERVER=http://127.0.0.1:8765 pnpm --dir web dev`, the development web app talks to the
  real server.
- `uv run karaoke-server serve --fake-engine` makes pretend karaokes (the synthetic package) without
  a GPU, in a second.
- `pnpm --dir web test:e2e:server`: browser tests against the real server with the fake engine and a
  new library (the laptop through `localhost`, the phones through the machine's IP address).
- The API is described in `schemas/openapi.json` (`make contracts` regenerates it along with the web
  app's types in `web/src/lib/api/generated/`).
- Ports: 8765 (home, `KARAOKE_PORT`) and the next one, 8766 (tunnels, only on `127.0.0.1`).
