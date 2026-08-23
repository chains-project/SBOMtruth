"""
Common functions used in multiple files.
"""

def _chain(chn: list, cf: str, confounders: dict) -> None:
    con = confounders[cf]
    if cf in chn:
        print("FATAL: discovered confounder loop", chn + [cf])
        exit()
    if "chained" in con:
        for ch in con["chained"]:
            _chain(chn + [cf], ch, confounders)


def sanity(recipes: dict, confounders: dict) -> None:
    # check confounders aren't cyclical
    for cf in confounders:
        _chain([], cf, confounders)

def _targ(t: dict, con: dict, history: str, confounders: dict, sources=["*"]) -> None:
    if "maketarget" in con and not con["maketarget"]:
        pass
    else:
        if "keepdeps" in con:
            if any([keeps not in sources for keeps in con["keepdeps"]]) and not "*" in sources:
                print(f"Invalid source purge in confounder \"{con["friendly"]}\"")
                exit()
            sources = con["keepdeps"]

        if history in t:
            existing = set(t[history])
            newSources = set(sources)
            t[history] = list(existing.union(newSources))
        else:
            t[history] = sources

    if "chained" in con:
        for cf in con["chained"]:
            _targ(t, confounders[cf], f"{history}-{confounders[cf]["name"]}", confounders, sources)

def targets(recipe: dict, confounders: dict) -> list[str]:
    t = {"base": ["*"], "export": ["*"]}

    if "confounders" not in recipe:
        return t

    if "*" in recipe["confounders"]:
        t.extend([c["name"] for c in confounders if not "maketarget" in c or not c["maketarget"]])
    else:
        for c in recipe["confounders"]:
            con = confounders[c]
            _targ(t, con, con["name"], confounders)

    # out = []
    # for c in t:
    #     if c not in out:
    #         out.append(c)

    return t

def recipes(full: dict) -> list[dict]:
    r = full["recipes"]
    bases = full["bases"]

    output = []

    for recipe in r:
        base = recipe["base"]
        for b in bases[base]:
            c = recipe.copy()
            if "postfix" in b:
                c["name"] += f"-{b["postfix"]}"
            c["base"] = b["image"]

            if "confounders" in b:
                if "confounders" not in c:
                    c["confounders"] = []
                c["confounders"] = c["confounders"].copy()
                c["confounders"].extend(b["confounders"])

            output.append(c)

    return output
