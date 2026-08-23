def install(ls: list[str], _rname: str) -> list[str]:
    return [f"RUN apt install {" ".join(ls)}"]

def collect(f, src: str) -> list[dict]:
    lst = []
    pkgs = f.read().split("\n\n")

    for p in pkgs:
        n, v = None, None
        pkg = p.split("\n")
        for line in pkg:
            if line.startswith("Package: "):
                n = line[9:]
            elif line.startswith("Version: "):
                v = line[9:]

        if not n:
            continue
        lst.append({"name": n, "version": v, "source": src})

    return lst
