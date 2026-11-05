"""Everything a request handler may need, built once per server and kept on `app.state`."""

from dataclasses import dataclass

from karaoke_server.access import Devices
from karaoke_server.config import Settings
from karaoke_server.db import Database
from karaoke_server.jobs.queue import JobQueue
from karaoke_server.library import Library
from karaoke_server.network import Network
from karaoke_server.parties import Parties


@dataclass
class Services:
    settings: Settings
    db: Database
    library: Library
    devices: Devices
    network: Network
    # The Windows side of WSL's NAT network (see access.classify).
    gateways: frozenset[str]
    parties: Parties
    jobs: JobQueue
