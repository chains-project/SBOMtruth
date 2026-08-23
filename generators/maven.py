import json
import os

preamble = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>app</groupId>
  <artifactId>app</artifactId>
  <version>1.0-SNAPSHOT</version>

  <name>app</name>
  <url>http://www.example.com</url>

  <properties>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    <maven.compiler.release>17</maven.compiler.release>
  </properties>

  <dependencies>
"""

dep = """    <dependency>
      <groupId>{package}</groupId>
      <artifactId>{artifact}</artifactId>
      <version>{version}</version>
    </dependency>
"""

postamble = """  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-shade-plugin</artifactId>
        <version>3.6.2</version>
        <executions>
          <execution>
            <phase>package</phase>
            <goals>
              <goal>shade</goal>
            </goals>
            <configuration>
              <transformers>
                <transformer implementation="org.apache.maven.plugins.shade.resource.ManifestResourceTransformer">
                  <mainClass>app.Main</mainClass>
                </transformer>
              </transformers>
            </configuration>
          </execution>
        </executions>
      </plugin>
    </plugins>
  </build>
</project>
"""

javaprogram = """package app;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}
"""

def install(ls: list[str], rname: str) -> list[str]:
    if not os.path.exists(f"files/{rname}"):
        os.mkdir(f"files/{rname}")

    with open(f"files/{rname}/pom.xml", "w") as f:
        f.write(preamble)
        for d in ls:
            f.write(dep.format(package=d["group"], artifact=d["artifact"], version=d["version"]))
        f.write(postamble)

    with open(f"files/{rname}/Main.java", "w") as f:
        f.write(javaprogram)

    return [
        "WORKDIR /mvnapp",
        f"COPY {rname}/pom.xml pom.xml",
        f"COPY {rname}/Main.java src/main/java/app/Main.java",
        "WORKDIR /"
    ]

def collect_internal(ls: list[dict], obj: dict, src: str) -> None:
    n = obj["groupId"] + ":" + obj["artifactId"]
    v = obj["version"]

    ls.append({"name": n, "version": v, "source": src, "accepted": [obj["artifactId"]]})

    if "children" in obj:
        for child in obj["children"]:
            collect_internal(ls, child, src)

def collect(f, src: str) -> list[dict]:
    l = []
    obj = json.load(f)

    collect_internal(l, obj, src)

    return l
