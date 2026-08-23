#! /usr/bin/env python3

import json
import os
from imp import *
import common

def beautify(df: list[str]) -> None:
    """Adds newlines between mismatching declarations to create groupings and make the dockerfile slightly more human-readable"""
    i = 1
    while i < len(df):
        if df[i].split()[0] != df[i-1].split()[0]:
            df.insert(i, "")
            i += 1
        i += 1

def preamble(recipe: dict) -> list[str]:
    pa = []
    if recipe["base"] != "scratch":
        pa.append("RUN mkdir /gt")
    return pa

def postamble(recipe: dict) -> list[str]:
    pa = []
    pa.append("FROM base AS export")
    if recipe["base"] != "scratch":
        pa.append("RUN rm -rf /gt")
    return pa

def _conf(m: dict, cf: str, con: dict, name: str, base: str, confounders: dict) -> None:
    if name in ["extract", "prep"]:
        base = "base"
    if name not in m:
        base2 = "scratch" if "scratch" in con and con["scratch"] else base
        m[name] = {"commands": [f"FROM {base2} AS {name}"], "confounders": []}

    m[name]["confounders"].append(cf)
    c = m[name]["commands"]

    if "copy" in con:
        for cop in con["copy"]:
            src = " "
            if "prev" in cop and cop["prev"]:
                src = f" --from={base} "
            elif "prep" in cop and cop["prep"]:
                src = f" --from=prep "
            cmd = f"COPY{src}{cop["path"]} {cop["target"]}"
            c.append(cmd)

    if "run" in con:
        c.extend([f"RUN {com}" for com in con["run"]])

    if "chained" in con:
        for cf2 in con["chained"]:
            con2 = confounders[cf2]
            name2 = f"{name}-{con2["name"]}"
            _conf(m, cf2, con2, name2, name, confounders)


def confounder(recipe: dict, confounders: dict) -> list[str]:
    if "confounders" not in recipe:
        return []

    cfs = recipe["confounders"]

    if "*" in cfs:
        cfs = confounders.keys()

    m = {}

    for cf in cfs:
        con = confounders[cf]
        name = con["name"]
        _conf(m, cf, con, name, "export", confounders)

    output = []

    for t in m:
        output.extend(m[t]["commands"])
        if len(c := m[t]["confounders"]) > 1:
            print(f"INFO: Multiple confounders ({", ".join(c)}) all contribuing to target {t}")

    return output

def main() -> None:
    with open("recipes.json", "r") as f:
        full = json.load(f)
        recipes = common.recipes(full)
        confounders = full["confounders"]

    common.sanity(recipes, confounders)

    for recipe in recipes:
        # ensure paths exist
        path = f"out/{recipe["name"]}"
        truthpath = f"{path}/truth"
        sbompath = f"{path}/sbom"
        if not os.path.exists("out"):
            os.mkdir("out")
        if not os.path.exists(path):
            os.mkdir(path)
        if not os.path.exists(truthpath):
            os.mkdir(truthpath)
        if not os.path.exists(sbompath):
            os.mkdir(sbompath)

        # store dockerfile in array
        df = [f"FROM {recipe["base"]} AS base"]

        df.extend(preamble(recipe))

        files = recipe["files"] if "files" in recipe else []
        for file in files:
            if type(file["path"]) == list:
                df.append(f"COPY {" ".join(file["path"])} {file["target"]}")
            else:
                df.append(f"COPY {file["path"]} {file["target"]}")

        deps = recipe["deps"] if "deps" in recipe else []
        for src in deps:
            df.extend(gens[src].install(deps[src], recipe["name"]))

        run = [f"RUN {r}" for r in recipe["run"]] if "run" in recipe else []
        df.extend(run)

        df.extend(postamble(recipe))

        df.extend(confounder(recipe, confounders))

        # make dockerfile slightly more human-readable
        beautify(df)

        with open(f"{path}/Dockerfile", "w") as f:
            f.write("\n".join(df))
            f.write("\n")

        print(f"Generated dockerfile for {recipe["name"]}")

if __name__ == '__main__':
    main()
