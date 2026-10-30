"""Publish immutable, verified artifacts from a successful main-branch build."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


PACKAGES = ("OpenCore-Patcher.pkg", "AutoPkg-Assets.pkg", "OpenCore-Patcher-Uninstaller.pkg")
INFO = ("SHA256SUMS.txt", "build-provenance.json", "resolved-dependencies.txt")


def digest(path):
    with path.open("rb") as stream:
        return "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()


def validate_files(folder, commit, version):
    provenance = json.loads((folder / "build-provenance.json").read_text())
    if provenance["commit"] != commit or provenance["versions"]["patcher_version"] != version:
        raise ValueError("Build provenance does not match the requested source/version")
    checksums = {}
    for line in (folder / "SHA256SUMS.txt").read_text().splitlines():
        checksum, name = line.split(None, 1)
        if not re.fullmatch(r"[a-f0-9]{64}", checksum) or name not in {"dist/" + p for p in PACKAGES} or name in checksums:
            raise ValueError("Invalid or duplicate checksum entry")
        checksums[name] = checksum
    if set(checksums) != {"dist/" + p for p in PACKAGES}:
        raise ValueError("The build must contain all three package checksums")
    identities = {name: {"digest": digest(folder / name), "size": (folder / name).stat().st_size} for name in PACKAGES + INFO}
    for name in PACKAGES:
        if identities[name]["digest"] != "sha256:" + checksums["dist/" + name]:
            raise ValueError(f"Package checksum mismatch: {name}")
    return identities


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def api(endpoint, optional=False):
    result = subprocess.run(["gh", "api", endpoint], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if optional and result.returncode and "HTTP 404" in result.stderr:
        return None
    if result.returncode:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


def verify_assets(release, expected):
    actual = {asset["name"]: asset for asset in release["assets"]}
    if set(actual) != set(expected):
        raise ValueError("Release assets do not match the verified file set")
    for name, identity in expected.items():
        if any(actual[name].get(key) != value for key, value in identity.items()):
            raise ValueError(f"Uploaded asset digest/size mismatch: {name}")


def find_release(repo, version):
    page = 1
    while True:
        releases = api(f"repos/{repo}/releases?per_page=100&page={page}")
        for release in releases:
            if release["tag_name"] == version:
                return release
        if len(releases) < 100:
            return None
        page += 1


def create_release(repo, version, commit):
    # Use the creation response: release-list caches may not show a new draft yet.
    return json.loads(command(
        "gh", "api", f"repos/{repo}/releases", "--method", "POST",
        "-f", f"tag_name={version}", "-f", f"target_commitish={commit}",
        "-f", f"name=OpenCore Legacy Patcher {version} — ReinierTutoriales",
        "-F", "draft=true", "-F", "prerelease=true",
        "-f", "body=" + Path(f"ci_tooling/release-notes-{version}.md").read_text(),
    ))


def main():
    repo, run_id, commit, version = (os.environ[k] for k in ("GH_REPO", "CANDIDATE_RUN_ID", "SOURCE_COMMIT", "RELEASE_VERSION"))
    if not re.fullmatch(r"[0-9]+", run_id) or not re.fullmatch(r"[a-f0-9]{40}", commit) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+", version):
        raise ValueError("Expected a main build ID, full source SHA and RC version")
    run = api(f"repos/{repo}/actions/runs/{run_id}")
    if (run["status"], run["conclusion"], run["event"], run["head_branch"], run["head_sha"], run["path"], run["repository"]["full_name"]) != ("completed", "success", "push", "main", commit, ".github/workflows/build-release.yml", repo):
        raise ValueError("Only a successful push build of this repository's main branch can be published")
    command("git", "merge-base", "--is-ancestor", commit, "origin/main")
    folder = Path("release-dist")
    folder.mkdir()
    for artifact in PACKAGES + ("OpenCore-Patcher-Intel-build-info",):
        command("gh", "run", "download", run_id, "--name", artifact, "--dir", str(folder))
    expected = validate_files(folder, commit, version)
    release = find_release(repo, version)
    tag = api(f"repos/{repo}/git/ref/tags/{version}", optional=True)
    if tag is not None and api(f"repos/{repo}/commits/{version}")["sha"] != commit:
        raise ValueError("The existing tag points to a different source commit")
    if release is not None and not release["draft"]:
        verify_assets(release, expected)
        print(f"Already published and verified: {release['html_url']}")
        return
    if release is None:
        release = create_release(repo, version, commit)
    elif release["target_commitish"] != commit:
        raise ValueError("The existing draft targets a different source commit")
    endpoint = f"repos/{repo}/releases/{release['id']}"
    uploaded = {asset["name"]: asset for asset in release["assets"]}
    for name, identity in expected.items():
        if name in uploaded:
            if any(uploaded[name].get(key) != value for key, value in identity.items()):
                raise ValueError(f"Refusing to overwrite an existing release asset: {name}")
        else:
            command("gh", "release", "upload", version, str(folder / name))
    verify_assets(api(endpoint), expected)
    command("gh", "release", "edit", version, "--draft=false", "--prerelease")
    print(f"Published verified prerelease: {api(endpoint)['html_url']}")


if __name__ == "__main__":
    main()
