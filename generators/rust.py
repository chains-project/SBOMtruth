import json

def install(ls: list[str], _rname: str) -> list[str]:
    return [
        "WORKDIR /rustapp",
        "RUN cargo init",
        f"RUN cargo add {" ".join([f"{p["package"]}{f"@{p["version"] if "version" in p else ""}"}" for p in ls])}",
        "WORKDIR /",
        ]

def collect(f, src: str) -> list[dict]:
    obj = json.load(f)
    l = []

    for pkg in obj["packages"]:
        l.append({"name": pkg["name"], "version": pkg["version"], "source": src})

    return l
