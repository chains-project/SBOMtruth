#! /usr/bin/env python3
"""
Builds docker images of the dockerfiles generated from the recipes.
Extracts the produced images into tar files, as well as the ground truth produced during the image build.
Collects the ground truth sources into one file.
"""

import json
import os
import subprocess
from sys import argv
from imp import *

import common

truthMap = {
    "npm-gt.json": (npm, "npm"),
    "npm-main.json": (npm, "npmcore"),
    "py.json": (python, "python"),
    "dpkgstatus.txt": (apt, "apt"),
    "alpineinstalled.txt": (apk, "apk"),
    "mvn.json": (maven, "maven"),
    "mvnjar.txt": (mvnjar, "mvnjar"),
    "rust.json": (rust, "rust"),
    "go.txt": (go, "go"),
}

def buildDocker(path: str, imageName: str, target: str) -> None:
    subprocess.run(["docker", "build",
                    "--target", target,
                    "--load",
                    "-f", "Dockerfile",
                    "--tag", f"sbom/{imageName}:{target}",
                    "../../files"
                    ], cwd=path, check=True)

def extractTruth(path: str, imageName: str) -> None:
    subprocess.run(["docker", "build",
                    "--target", "extract",
                    "--output", f"./truth",
                    "-f", "Dockerfile",
                    "../../files"
                    ], cwd=path, check=True)

def collectTruth(path: str) -> None:
    truthpath = f"{path}/truth"
    truth = []
    for t in truthMap:
        if os.path.exists(f"{truthpath}/{t}"):
            with open(f"{truthpath}/{t}", "r") as f:
                (eco, src) = truthMap[t]
                truth.extend(eco.collect(f, src))

    # dedupe
    truth.sort(key=lambda x: (x["name"], x["version"]))
    i = 1
    while i < len(truth):
        if truth[i] == truth[i-1]:
            truth.pop(i)
        else:
            i += 1

    with open(f"{path}/truth.json", "w") as f:
        json.dump(truth, f, indent=4)

def main() -> None:
    with open("recipes.json", "r") as f:
        full = json.load(f)
        recipes = common.recipes(full)
        confounders = full["confounders"]

    common.sanity(recipes, confounders)

    for recipe in recipes:
        if len(argv) > 1:
            if not any(a in recipe["name"] for a in argv[1:]):
                continue
        print(recipe["name"])

        path = f"out/{recipe["name"]}"

        targets = common.targets(recipe, confounders)

        extractTruth(path, recipe["name"])
        collectTruth(path)

        for target in targets:
            print(recipe["name"], target)
            buildDocker(path, recipe["name"], target)



if __name__ == "__main__":
    main()
