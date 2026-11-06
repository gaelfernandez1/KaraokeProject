# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 3.x | yes |
| 2.x and older (`v2-final`, the thesis version) | no: replaced by the 3.0 rebuild |

## Reporting a vulnerability

Please report it **privately** through GitHub:
[Security → Report a vulnerability](https://github.com/gaelfernandez1/KaraokeProject/security/advisories/new).
Do not open a public issue.

Include what an attacker can do, the steps to reproduce it and the version (`uv run
karaoke-server --version`). The project is maintained by one person: you will get an answer within a
week, and a fix for a confirmed problem is released as a patch version with credit to you, unless
you prefer otherwise.

## How the server is meant to be used

Knowing the design helps judge what is a vulnerability. The details are in
[`docs/server.md`](docs/server.md) and
[`docs/plan-v3/decisiones/011-servidor.md`](docs/plan-v3/decisiones/011-servidor.md).

- The server runs on the owner's own computer and serves the home network on port 8765. Port 8766
  listens on `127.0.0.1` only, for a tunnel such as Tailscale Serve (HTTPS, the owner's tailnet).
- Requests fall into three zones: **local** (the computer itself), **home** (a private address
  on port 8765) and **remote** (everything through the tunnel port, proxy headers or another
  address). Only the owner — the local zone or a **paired device** — creates, edits, deletes and
  exports songs. Home devices can browse, sing and run a party; remote devices that are not paired
  see only the app and the pairing page.
- Pairing uses a one-time code of 8 letters that expires after 10 minutes; repeated failures are
  blocked per client. The device token is stored hashed and travels in an `HttpOnly`,
  `SameSite=Lax` cookie (`Secure` over HTTPS). Requests that change something must come from the
  server's own `Origin`.
- Party guests join with a QR code and can only queue songs and act as a remote.
- Each karaoke is made in its own process with a memory limit; the server process never loads
  the models.

Known limits, by design for now: on the home network the app is plain HTTP, so the owner's cookie
is not encrypted on the Wi-Fi; with `--open-home` everyone at home is treated as the owner; there
are no limits on the length of a party queue.

## Supply chain

GitHub Actions are pinned to a commit and run with read-only permissions (checked by zizmor);
Dependabot raises security updates as soon as an advisory is published; every Python dependency's
licence is checked in CI ([`scripts/licenses.py`](scripts/licenses.py)); the models are pinned to a
revision of their Hugging Face repository.
