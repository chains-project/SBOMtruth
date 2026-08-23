import json

def install(ls: list[str], _rname: str) -> list[str]:
    return [
        "WORKDIR /npmapp",
        f"RUN npm install {" ".join(ls)} && npm list --all --json > /gt/npm-gt.json",
        "RUN cd /usr/local/lib/ && npm list --all --json > /gt/npm-main.json",
        "WORKDIR /",
    ]

def collect(f, src: str) -> list[dict]:
    return collect_internal(json.load(f), src)

def collect_internal(obj: dict, src: str, cur=None):
    l = []
    if obj is not None and "version" in obj:
        l.append({"name": cur, "version": obj["version"], "source": src})
    if "dependencies" in obj:
        for d in obj["dependencies"]:
            l.extend(collect_internal(obj["dependencies"][d], src, d))
    return l
