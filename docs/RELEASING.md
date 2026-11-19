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

# Release SBOM Verifier

The release tools build, sign, verify, and publish artifacts to Maven Central. Run commands from the repository root with JDK 21 and the Maven Wrapper.

Replace `VERSION` in the commands below with the release version.

## Requirements

- Maven Central Portal access to the `de.grobmeier` namespace.
- A Central Portal user token.
- A GPG signing key whose public key is available on a public keyserver.
- A clean Git checkout at the matching `sbom-verifier-VERSION` tag for publication.

The publication command reads these environment variables:

| Variable | Value |
| --- | --- |
| `CENTRAL_USERNAME` | Portal token username |
| `CENTRAL_PASSWORD` | Portal token password |
| `RELEASE_SIGNING_KEY` | Full primary fingerprint of the signing key |

[The Maven settings](maven-release-settings.xml) map the token variables to the `central-sbom-verifier` server ID.
Keep credentials outside Git and command-line arguments.

## Unlock the signing key

List the available signing keys:

```sh
gpg --list-secret-keys --keyid-format long
```

Set `RELEASE_SIGNING_KEY` to the full primary fingerprint of the selected key. Confirm its identity:

```sh
gpg --fingerprint "$RELEASE_SIGNING_KEY"
```

Run a signing check through the GPG agent:

```sh
export GPG_TTY=$(tty)
printf 'SBOM Verifier release signing check\n' |
  gpg --local-user "$RELEASE_SIGNING_KEY" --armor --clearsign \
  > /tmp/sbom-verifier-signing-check.asc
```

Enter the passphrase or hardware-key PIN in the GPG prompt. The agent cache can expire between commands.

## Verify release artifacts locally

Run tests and build signed artifacts:

```sh
./mvnw -B -Prelease -Drevision=VERSION -Dgpg.keyname="$RELEASE_SIGNING_KEY" clean verify
```

Assemble and inspect the bundle:

```sh
python3 tools/prepare-central-bundle.py --version VERSION --signing-fingerprint "$RELEASE_SIGNING_KEY"
unzip -l maven-plugin/target/release/central-bundle.zip
```

The bundle tool verifies coordinates, the goal prefix, POM metadata, source/Javadoc contents, and six signatures.
The bundle contains the flattened POM, plugin JAR, sources, Javadoc, and CycloneDX XML/JSON attachments with checksums.
The flattened POM has no parent dependency. The build parent is excluded from publication.

This check verifies the local bundle. Maven Central performs its own validation during publication.

## Publish to Maven Central

The `release` profile builds signed artifacts. The `central-upload` profile enables automatic upload and publication through the Central publisher.
Both profiles are required for publication.

Inspect the publication command without running Maven:

```sh
python3 tools/release-to-central.py --dry-run VERSION
```

Publish from a clean checkout at the matching `sbom-verifier-VERSION` tag:

```sh
python3 tools/release-to-central.py VERSION
```

The command checks the tag, working tree, and required environment variables.
It invokes Maven with the release version, signing key, dedicated settings, and `release,central-upload` profiles.
Maven signs the artifacts, uploads the bundle, waits for Central validation, and publishes it automatically.
The command waits for the published result.

Pushes, merges, and tag creation do not invoke publication. The release-preflight workflow runs tests and release-profile verification with signing skipped.

## Verify publication

Confirm that Maven reports publication. Resolve the published coordinates from a clean Maven repository.
Maven Central release versions are immutable.

## References

- [Central artifact requirements](https://central.sonatype.org/publish/requirements/)
- [Central Maven publisher](https://central.sonatype.org/publish/publish-portal-maven/)
- [Central namespace access](https://central.sonatype.org/register/namespace/)
