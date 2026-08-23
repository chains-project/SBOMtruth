import generators.apt as apt
import generators.python as python
import generators.npm as npm
import generators.go as go
import generators.maven as maven
import generators.mvnjar as mvnjar
import generators.apk as apk
import generators.rust as rust

gens = {
    "apt": apt,
    "python": python,
    "npm": npm,
    "go": go,
    "maven": maven,
    "mavenjar": mvnjar,
    "apk": apk,
    "rust": rust,
}
