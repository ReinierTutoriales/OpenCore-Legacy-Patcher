"""Detach a known mounted disk image, retrying only a transient busy error."""

import errno
import subprocess
import time


def detach_disk_image(mount_point):
    for attempt in range(3):
        result = subprocess.run(
            ["/usr/bin/hdiutil", "detach", mount_point, "-force"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
        )
        if result.returncode != errno.EBUSY or attempt == 2:
            return result
        time.sleep(1)
