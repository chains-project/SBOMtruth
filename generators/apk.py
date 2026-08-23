def install(ls: list[str]) -> list[str]:
    return [f"RUN apk add {" ".join(ls)}"]

def collect(f, src: str) -> list[dict]:
    lst = []
    pkgs = f.read().split("\n\n")

    for p in pkgs:
        n, v = None, None
        pkg = p.split("\n")
        for line in pkg:
            if line.startswith("P:"):
                n = line[2:]
            elif line.startswith("V:"):
                v = line[2:]

        if not n:
            continue
        lst.append({"name": n, "version": v, "source": src})

    return lst
