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

def latexTable(f, rows, image, target) -> None:
    sectionEnds = []
    for row in range(len(rows)):
        if rows[row][0] not in ["Base", ""]:
            sectionEnds.append(row-1)

        for col in range(len(rows[row])):
            if type(rows[row][col]) == float:
                rows[row][col] = f"${round(rows[row][col] * 100, 1)}\\%$"

            # make first row bold
            if (row == 0) and rows[row][col] != "":
                rows[row][col] = f"\\textbf{{{rows[row][col]}}}"

    cols = len(rows[0])

    compacted = []
    for row in range(len(rows)):
        ending = f"\\cline{{2-{len(rows[row])}}}" if row not in sectionEnds and row != len(rows)-1 else "\\hline"
        compacted.append("\t\t\t" + " & ".join(rows[row]) + " \\\\ " + ending)


    rqguess = "rq2" if target == "base" else "rq3"

    preamble = f"""\\begin{{table}}[!ht]
    \\begin{{center}}
        \\caption{{Results for {image} - {target}}}
        \\label{{{f"tab:res-{rqguess}-{image}{f"-{target}" if rqguess == "rq3" else ""}"}}}
        \\begin{{tabular}}{{{f"|{"|".join(["l" for _ in range(cols)])}|"}}}
            \\hline
"""
    postamble = """        \\end{tabular}
    \\end{center}
\\end{table}
"""

    f.write(f"{image} - {target}")
    f.write("\n")
    f.write(preamble)
    for row in compacted:
        f.write(row)
        f.write("\n")
    f.write(postamble)
    f.write("\n\n")

def collectRecalls(instance: dict) -> dict:
    tps = {}
    fns = {}
    sources = set()

    for tp in instance["tp_list"]:
        if tp["source"] not in sources:
            sources.add(tp["source"])
        if tp["source"] not in tps:
            tps[tp["source"]] = 0
        tps[tp["source"]] += 1

    for fn in instance["fn_list"]:
        if fn["source"] not in sources:
            sources.add(fn["source"])
        if fn["source"] not in fns:
            fns[fn["source"]] = 0
        fns[fn["source"]] += 1

    out = {}
    for source in sources:
        tp = tps[source] if source in tps else 0
        fn = fns[source] if source in fns else 0
        out[f"recall-{source}"] = tp / (tp + fn) if tp + fn > 0 else 0

    return out

def printLatex(results: dict) -> None:
    # output[lang][target][distro][scanner]
    output = {}

    for recipe in results:
        recipeParts = recipe.split("-")
        lang = "-".join(recipeParts[:-1]) if len(recipeParts) > 1 else recipe
        distro = recipeParts[-1] if len(recipeParts) > 1 else "default"

        if lang not in output:
            output[lang] = {}

        for target in results[recipe]:
            if target not in output[lang]:
                output[lang][target] = {}
            if distro not in output[lang][target]:
                output[lang][target][distro] = {}

            for scanner in results[recipe][target]:
                recalls = {}
                recalls["precision"] = results[recipe][target][scanner]["precision"]
                recalls["recall"] = results[recipe][target][scanner]["recall"]
                r2 = collectRecalls(results[recipe][target][scanner])
                if len(r2) > 1:
                    recalls.update(r2)

                output[lang][target][distro][scanner] = recalls

    with open("latex.txt", "w") as f:
        for lang in output:
            for target in output[lang]:
                rows = []
                # extract sbom scanners for this image-lang-target
                scans = list(list(output[lang][target].values())[0].keys())
                rows.append(["Base", "Measure"] + scans) # first row

                for distro in output[lang][target]:
                    inv = {}
                    scanners = output[lang][target][distro]

                    # invert from scanner -> measure to measure -> scanner
                    for scanner in scanners:
                        for measure in scanners[scanner]:
                            if measure not in inv:
                                inv[measure] = {}
                            inv[measure][scanner] = scanners[scanner][measure]

                    insideRows = [["", measure] + [inv[measure][scanner] if scanner in inv[measure] else "N/A" for scanner in scans] for measure in inv]
                    insideRows[0][0] = f"\\multirow{{{len(insideRows)}}}{{4em}}{{{distro}}}"

                    rows.extend(insideRows)
                latexTable(f, rows, lang, target)
    exit()

def main() -> None:
    latex = "--latex" in argv
    if latex:
        argv.remove("--latex")

    spam = "--print" in argv
    if spam:
        argv.remove("--print")

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
        if spam:
            print(f"{recipe["name"]}: ", end="")
        for target in targets:
            if len(argv) > 1:
                if target not in argv[1:]:
                    continue
            if spam:
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
                if spam:
                    print(f"{scanner:.<16}: tp: {len(comp["tp"]): >5}, fp: {len(comp["fp"]): >5}, fn: {len(comp["fn"]): >5}")

                if scanner not in output[recipe["name"]][target]:
                    precision = len(comp["tp"]) + len(comp["fp"])
                    precision = len(comp["tp"]) / precision if precision > 0 else "N/A"
                    recall = len(comp["tp"]) + len(comp["fn"])
                    recall = len(comp["tp"]) / recall if recall > 0 else "N/A"
                    output[recipe["name"]][target][scanner] = {
                        "tp": len(comp["tp"]), "fp": len(comp["fp"]), "fn": len(comp["fn"]),
                        "precision": precision, "recall": recall,
                        "tp_list": comp["tp"],"fp_list": comp["fp"], "fn_list": comp["fn"]}
            if spam:
                print()

    with open("report.json", "w") as f:
        json.dump(output, f, indent='\t')

    if latex:
        printLatex(output)


if __name__ == "__main__":
    main()
