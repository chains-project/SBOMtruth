#! /usr/bin/env python3

import json
from sys import argv

import common

scanners = ["syft", "trivy", "sbomtool", "bom", "scout"]
nameMap = {"syft": "Syft", "trivy": "Trivy", "sbomtool": "sbom-tool", "bom": "bom", "scout": "Docker scout"}

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

def pad(s, l):
    return s + " " * (l - len(s))

def printLatex(f, result, image, target) -> None:
    columns = []
    columns.append(["Measure", "True positives", "False positives", "Precision", "False negatives", "Recall"])
    for scanner in result:
        o = result[scanner]
        col = []
        col.append(nameMap[scanner])
        col.append(o["tp"])
        col.append(o["fp"])
        if o["precision"] != None:
            col.append(f"${round(o["precision"] * 100, 1)}\\%$")
        else:
            col.append("N/A")
        col.append(o["fn"])
        if o["recall"] != None:
            col.append(f"${round(o["recall"] * 100, 1)}\\%$")
        else:
            col.append("N/A")

        columns.append([str(cell) for cell in col])

    for i in range(len(columns)):
        columns[i][0] = f"\\textbf{{{columns[i][0]}}}"


    lengths = [max([len(cell) for cell in col]) for col in columns]

    for col in range(len(columns)):
        columns[col] = [pad(cell, lengths[col]) for cell in columns[col]]

    rows = [[None for b in range(len(columns))] for i in range(len(columns[0])) ]

    for col in range(len(columns)):
        for row in range(len(columns[col])):
            rows[row][col] = columns[col][row]

    rows = ["\t\t\t" + " & ".join(row) + " \\\\ \\hline" for row in rows]

    rqguess = "rq2" if target == "base" else "rq3"

    preamble = f"""\\begin{{table}}[!ht]
    \\begin{{center}}
        \\caption{{Results for {image} - {target}}}
        \\label{{{f"tab:res-{rqguess}-{image}{f"-{target}" if rqguess == "rq3" else ""}"}}}
        \\begin{{tabular}}{{{f"|{"|".join(["l" for _ in columns])}|"}}}
            \\hline
"""
    postamble = """        \\end{tabular}
    \\end{center}
\\end{table}
"""

    f.write(f"{image} - {target}")
    f.write("\n")
    f.write(preamble)
    for row in rows:
        f.write(row)
        f.write("\n")
    f.write(postamble)
    f.write("\n\n")

def main() -> None:
    latex = "--latex" in argv
    if latex:
        argv.remove("--latex")

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
                file = f"{path}/sbom/{scanner}-{target}.spdx.json"
                try:
                    discovered = extractVersionsFromSPDX(file)
                except json.JSONDecodeError:
                    print("Could not parse JSON in file", file)
                    continue
                except FileNotFoundError as e:
                    print("Could not find file", file)
                    continue

                filteredSources = targets[target]
                tmpTruth = truth[:]
                if "*" not in filteredSources:
                    tmpTruth = [comp for comp in truth if comp["source"] in filteredSources]

                comp = computeMatches(tmpTruth, discovered)
                print(f"{scanner:.<16}: tp: {len(comp["tp"]): >5}, fp: {len(comp["fp"]): >5}, fn: {len(comp["fn"]): >5}")

                if scanner not in output[recipe["name"]][target]:
                    precision = len(comp["tp"]) + len(comp["fp"])
                    precision = len(comp["tp"]) / precision if precision > 0 else None
                    recall = len(comp["tp"]) + len(comp["fn"])
                    recall = len(comp["tp"]) / recall if recall > 0 else None
                    output[recipe["name"]][target][scanner] = {
                        "tp": len(comp["tp"]), "fp": len(comp["fp"]), "fn": len(comp["fn"]),
                        "precision": precision, "recall": recall,
                        "tp_list": comp["tp"],"fp_list": comp["fp"], "fn_list": comp["fn"]}
            print()

    with open("report.json", "w") as f:
        json.dump(output, f, indent='\t')

    if latex:
        with open("latex.txt", "w") as f:
            for recipe in output:
                for target in output[recipe]:
                    printLatex(f, output[recipe][target], recipe, target)


if __name__ == "__main__":
    main()
