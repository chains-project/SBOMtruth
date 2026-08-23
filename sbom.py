#! /usr/bin/env python3
"""
Builds SBOMs for the generated images.
"""

import json
import os
import subprocess
from sys import argv

import common

def syft(path: str, name: str, target: str) -> None:
    if not os.path.exists("work"):
        os.mkdir("work")
    subprocess.run(["syft", f"docker:sbom/{name}:{target}", "-o", f"spdx-json=syft.spdx.json"], cwd="work")
    with open("work/syft.spdx.json", "r") as i, open(f"{path}/sbom/syft-{target}.spdx.json", "w") as o:
        json.dump(json.load(i), o, indent=2)

def trivy(path: str, name: str, target: str) -> None:
    subprocess.run(["trivy", "image", f"sbom/{name}:{target}", "-f", "spdx-json", "-o", f"sbom/trivy-{target}.spdx.json"], cwd=path)

scanners = [syft, trivy]

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

        targets = common.targets(recipe, confounders)

        print(f"handling {recipe["name"]}")
        path = f"out/{recipe["name"]}"
        for target in targets:
            for scanner in scanners:
                scanner(path, recipe["name"], target)

if __name__ == "__main__":
    main()
