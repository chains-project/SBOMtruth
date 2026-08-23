import json

def install(ls: list[str], _rname: str) -> list[str]:
    return [
        f"RUN python -m ensurepip --upgrade",
        f"RUN pip install {" ".join(ls)} --report /gt/py.json"
        ]

def collect(f, src: str) -> list[dict]:
    obj = json.load(f)
    l = []
    if "install" not in obj:
        return l

    for p in obj["install"]:
        m = p["metadata"]
        l.append({"name": m["name"], "version": m["version"], "source": src})

    return l
