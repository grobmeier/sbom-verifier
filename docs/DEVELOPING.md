<!--
Copyright © 2026 Christian Grobmeier

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# Develop SBOM Verifier

This guide describes local builds and verification. See [RELEASING.md](RELEASING.md) for signing and Maven Central publication.

## Project identity

| Item | Value |
| --- | --- |
| Project | SBOM Verifier |
| Maven group | `de.grobmeier` |
| Maven plugin artifact | `sbom-verifier-maven-plugin` |
| Java package | `de.grobmeier.sbom.verifier` |
| Goal | `sbom-verifier:check` |
| Source repository | `https://github.com/grobmeier/sbom-verifier` |

## Build requirements

Use JDK 21 to match CI. The source targets Java 17. The Maven Wrapper selects Maven 3.9.9.
Python 3 and Git are required for the release-command tests. GPG is required for artifact signing.

Run verification from the repository root:

```sh
./mvnw -B verify
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p 'test_*.py' -v
```

Install the source build in the local Maven repository:

```sh
./mvnw -B install
```

The `revision` property in `pom.xml` defines the source version. The `install` goal writes to the local Maven repository.

## Source map

| Location | Purpose |
| --- | --- |
| [CheckMojo](../maven-plugin/src/main/java/de/grobmeier/sbom/verifier/CheckMojo.java) | Find supported attached SBOMs and execute the configured rules |
| [Rules](../maven-plugin/src/main/java/de/grobmeier/sbom/verifier/rules) | Completeness, checksum, and reference checks |
| [CycloneDX support](../maven-plugin/src/main/java/de/grobmeier/sbom/verifier/internal/cyclonedx) | Parse XML/JSON and map components to Maven artifacts |
| [Maven integration builds](../maven-plugin/src/it) | Consumer builds with passing and failing checks |
| [Rule reference](../maven-plugin/src/site/asciidoc/rules.adoc) | Rule configuration |
| [Release tools](../tools) | Bundle verification and Maven Central publication |

## Verify a consuming project

Use the configuration in [README](../README.adoc) to generate and attach a CycloneDX SBOM before the `check` goal runs.
Run `mvn verify` in the consuming project. Confirm that its log includes `sbom-verifier:VERSION:check` for the configured plugin version.

CycloneDX requires `skipNotDeployed=false` for modules that skip deployment. Check inherited CycloneDX executions to avoid duplicate generation.

## Rule behaviour

- The `check` goal reads supported CycloneDX XML and JSON attachments for the current Maven module.
- `requireSbom=true` requires at least one supported attachment. The goal checks every supported attachment.
- The `completeness` rule checks project identity and resolved compile/runtime dependency coverage, including transitive dependencies.
- Completeness excludes provided, test, and system dependencies. It permits extra SBOM components.
- The `checksum` rule verifies recorded checksums against dependency artifacts.
- HTTP 429, HTTP 5xx, and connection failures produce unavailable-reference warnings by default. `failOnUnavailable=true` makes these failures fatal.
- Dependency reference findings also require `failOnDependencies=true` to fail the build.

Completeness compares the Maven dependency graph with the SBOM. It does not inspect the contents of packaged or shaded archives.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| A consuming project cannot resolve a source build | Install the source version and match its coordinates in the consuming POM |
| No verifier output | Check the plugin execution and confirm that the build reaches `verify` |
| No SBOM attached | Check generator execution order and `skipNotDeployed` |
| Duplicate SBOM generation | Check inherited CycloneDX executions |
| Rule-loading error with an older Maven distribution | Use the Maven Wrapper, which selects Maven 3.9.9 |
| GPG signing fails | Follow the [signing-key procedure](RELEASING.md#unlock-the-signing-key) |
| Central authentication fails | Check the Portal token variables and the dedicated Maven settings |

Maven API dependencies use `provided` scope. The executing Maven distribution supplies these libraries.
