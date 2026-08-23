#! /usr/bin/env python3

import json
from sys import argv

import common

scanners = ["syft", "trivy"]

def extractVersionsFromSPDX(sbomPath: str) -> list[dict]:
    with open(sbomPath, "r") as f:
        sbom = json.load(f)
    packages = sbom['packages']
    v = [{"name": p['name'].lower(), "version": p['versionInfo'] if 'versionInfo' in p else 'UNKNOWN'} for p in packages]
    v.sort(key=lambda x: (x["name"], x["version"]))
    idx = 0
    while idx < len(v) - 1:
        if v[idx] == v[idx + 1]:
            v.pop(idx)
        else:
            idx += 1
    return v

def computeMatches(truth: list[dict], sbom: list[dict]) -> dict:
    falsePositives, truePositives, falseNegatives = [], [], []

    sbom = sbom[:]

    for p1 in truth:
        i = 0
        skip = False
        while i < len(sbom):
            p2 = sbom[i]
            if (p1["name"] == p2["name"] and p1["version"] == p2["version"]) or ("accepted" in p1 and p2["name"] in p1["accepted"] and p1["version"] == p2["version"]):
                truePositives.append(p1)
                sbom.pop(i)
                skip = True
                break
            i += 1
        if not skip:
            falseNegatives.append(p1)
    falsePositives.extend(sbom)

    return {"tp": truePositives, "fp": falsePositives, "fn": falseNegatives}

def main() -> None:
    with open("recipes.json", "r") as f:
        full = json.load(f)
        recipes = common.recipes(full)
        confounders = full["confounders"]

    common.sanity(recipes, confounders)

    output = {}

    for recipe in recipes:
        path = f"out/{recipe["name"]}"
        with open(f"{path}/truth.json", "r") as f:
            truth = json.load(f)

        targets = common.targets(recipe, confounders)
        print(f"{recipe["name"]}: ", end="")
        for target in targets:
            if len(argv) > 1:
                if target not in argv[1:]:
                    continue
            print(target)

            if recipe["name"] not in output:
                output[recipe["name"]] = {}
            if target not in output[recipe["name"]]:
                output[recipe["name"]][target] = {}
            for scanner in scanners:
                discovered = extractVersionsFromSPDX(f"{path}/sbom/{scanner}-{target}.spdx.json")

                filteredSources = targets[target]
                tmpTruth = truth[:]
                if "*" not in filteredSources:
                    tmpTruth = [comp for comp in truth if comp["source"] in filteredSources]

                comp = computeMatches(tmpTruth, discovered)
                print(f"{scanner:.<16}: tp: {len(comp["tp"]): >5}, fp: {len(comp["fp"]): >5}, fn: {len(comp["fn"]): >5}")

                if scanner not in output[recipe["name"]][target]:
                    output[recipe["name"]][target][scanner] = {
                        "tp": len(comp["tp"]), "fp": len(comp["fp"]), "fn": len(comp["fn"]),
                        "tp_list": comp["tp"],"fp_list": comp["fp"], "fn_list": comp["fn"]}
            print()

    with open("report.json", "w") as f:
        json.dump(output, f, indent='\t')

if __name__ == "__main__":
    main()
