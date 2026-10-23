"""Parsers for SNDlib native-format topology and demand files."""
import re

_SECTION = re.compile(r"^(NODES|LINKS|DEMANDS)\s*\($")


def _sections(text):
    out, cur = {}, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = _SECTION.match(line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif line == ")":
            cur = None
        elif cur:
            out[cur].append(line)
    return out


def parse_topology(text):
    """Return nodes (list) and undirected links [(u, v, capacity_mbps, id)]."""
    sec = _sections(text)
    nodes = [ln.split()[0] for ln in sec["NODES"]]
    links = []
    for ln in sec["LINKS"]:
        lid, rest = ln.split("(", 1)
        ends, rest = rest.split(")", 1)
        u, v = ends.split()
        nums = re.findall(r"[-\d.]+", rest.split("(", 1)[0])
        cap = float(nums[0]) if nums else 0.0
        if cap <= 0:  # no pre-installed capacity: use the largest module
            mods = re.findall(r"[-\d.]+", rest.split("(", 1)[1])
            cap = max(float(mods[i]) for i in range(0, len(mods), 2))
        links.append((u, v, cap, lid.strip()))
    return nodes, links


def parse_demands(text):
    """Return {(src, dst): value} from a DEMANDS section."""
    sec = _sections(text)
    dem = {}
    for ln in sec.get("DEMANDS", []):
        _, rest = ln.split("(", 1)
        ends, rest = rest.split(")", 1)
        s, t = ends.split()
        val = float(rest.split()[1])
        dem[(s, t)] = dem.get((s, t), 0.0) + val
    return dem
