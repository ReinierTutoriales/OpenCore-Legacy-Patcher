"""Merge official changes into a dedicated candidate branch, never into main."""

import subprocess


BRANCH = "auto-sync/dortania"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def checked(root, *args):
    result = git(root, *args)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def prepare(root, base="origin/main", upstream="dortania/main", candidate="origin/auto-sync/dortania"):
    if checked(root, "status", "--porcelain"):
        raise RuntimeError("Refusing to merge in a dirty working tree")
    existing = git(root, "rev-parse", "--verify", candidate)
    if git(root, "merge-base", "--is-ancestor", upstream, base).returncode == 0:
        if existing.returncode or git(root, "merge-base", "--is-ancestor", candidate, base).returncode == 0:
            return None
    start = existing.stdout.strip() if existing.returncode == 0 else checked(root, "rev-parse", base)
    checked(root, "switch", "--create", BRANCH, start)
    for ref in (base, upstream):
        result = git(root, "merge", "--no-ff", "--no-edit", ref)
        if result.returncode:
            conflicts = checked(root, "diff", "--name-only", "--diff-filter=U")
            checked(root, "merge", "--abort")
            raise RuntimeError(f"Merge blocked; no remote branch was changed. Conflicts:\n{conflicts}\n{result.stderr}")
    head = checked(root, "rev-parse", "HEAD")
    return {"head": head, "changed": head != start, "upstream": checked(root, "rev-parse", upstream)}


if __name__ == "__main__":
    import json
    print(json.dumps(prepare(".")))
