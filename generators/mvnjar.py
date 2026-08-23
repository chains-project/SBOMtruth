def collect(f, src: str) -> list[dict]:
    lst = []
    pkgs = f.read().split("-----")

    for p in pkgs:
        artifact, group, version = None, None, None
        pkg = p.split("\n")
        for line in pkg:
            if line.startswith("artifactId="):
                artifact = line[11:]
            elif line.startswith("groupId="):
                group = line[8:]
            elif line.startswith("version="):
                version = line[8:]

        if not artifact:
            continue
        lst.append({"name": group + ":" + artifact, "version": version, "source": src, "accepted": [artifact]})

    return lst
