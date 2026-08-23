import os

preamble = """package main

"""

dep = """import _ "{package}"
"""

postamble = """import "fmt"

func main() {
	fmt.Print("hello world")
}
"""

def install(ls: list[str], rname: str) -> list[str]:
    if not os.path.exists(f"files/{rname}"):
        os.mkdir(f"files/{rname}")

    with open(f"files/{rname}/main.go", "w") as f:
        f.write(preamble)
        for d in ls:
            f.write(dep.format(package=d))
        f.write(postamble)

    return [
        "WORKDIR /goapp",
        f"COPY {rname}/main.go main.go",
        "RUN go mod init example.com/sbom",
        f"RUN go get {" ".join(ls)}",
        "WORKDIR /",
        ]

def collect(f, src: str) -> list[dict]:
    lst = []
    for line in f:
        dep = line.strip().split(" ")[-1].split("@")
        lst.append({"name": dep[0], "version": dep[1], "source": src})

    return lst
