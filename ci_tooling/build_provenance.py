"""Record the exact source, dependency and payload identities of a candidate."""

import json
import platform
import subprocess
import sys
from pathlib import Path

from verify_components import verify


if __name__ == "__main__":
    lock = verify()
    provenance = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "upstream": lock["upstream"],
        "python": sys.version,
        "architecture": platform.machine(),
        "versions": lock["versions"],
        "payload_sha256": lock["files"],
        "signing": "unsigned candidate; privileged operations require a trusted signed build",
    }
    Path("dist/build-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
