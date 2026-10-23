"""Download raw SNDlib topologies and dynamic traffic matrices.

Every file is fetched by script and its SHA-256 is stored in data/MANIFEST.json,
so the raw inputs of every later phase can be checked.
"""
import hashlib
import json
import tarfile
import urllib.request
from datetime import datetime, timezone

from lira import DATA_RAW, ROOT

BASE = "https://sndlib.put.poznan.pl/download/"
SOURCES = {
    "abilene": {
        "topology": BASE + "sndlib-networks-native/abilene.txt",
        "dynamic": BASE + "directed-abilene-zhang-5min-over-6months-ALL-native.tgz",
    },
    "geant": {
        "topology": BASE + "sndlib-networks-native/geant.txt",
        "dynamic": BASE + "directed-geant-uhlig-15min-over-4months-ALL-native.tgz",
    },
    "nobel": {
        "topology": BASE + "sndlib-networks-native/nobel-germany.txt",
        "dynamic": BASE + "directed-nobel-germany-DFN-aggregated-5min-over-1day-native.tgz",
    },
}
MANIFEST = ROOT / "data" / "MANIFEST.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url, dest):
    if not dest.exists():
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, dest)
    return dest


def main():
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for topo, srcs in SOURCES.items():
        tdir = DATA_RAW / topo
        tdir.mkdir(parents=True, exist_ok=True)
        for kind, url in srcs.items():
            dest = fetch(url, tdir / url.rsplit("/", 1)[1])
            manifest[f"{topo}/{dest.name}"] = {
                "url": url, "sha256": sha256(dest), "bytes": dest.stat().st_size,
                "retrieved": manifest.get(f"{topo}/{dest.name}", {}).get(
                    "retrieved", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            }
            if dest.suffix == ".tgz":
                out = tdir / "dynamic"
                if not out.exists():
                    with tarfile.open(dest) as tf:
                        tf.extractall(out, filter="data")
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {len(manifest)} files")


if __name__ == "__main__":
    main()
