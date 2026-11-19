#!/usr/bin/env python3
# Copyright © 2026 Christian Grobmeier
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test installed plugin metadata and Maven's runtime requirement error."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maven-home', type=Path, required=True)
    parser.add_argument('--expect', choices=('supported', 'unsupported'), required=True)
    parser.add_argument('--local-repository', type=Path, default=Path.home() / '.m2/repository')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    source = ET.parse(root / 'pom.xml').getroot()
    version = source.findtext('m:properties/m:revision', namespaces=ns)
    minimum = source.findtext('m:properties/m:minimumMavenVersion', namespaces=ns)
    coordinates = f'de.grobmeier:sbom-verifier-maven-plugin:{version}'
    artifact = args.local_repository.resolve() / 'de/grobmeier/sbom-verifier-maven-plugin' / version
    pom = ET.parse(artifact / f'sbom-verifier-maven-plugin-{version}.pom').getroot()
    if pom.findtext('m:prerequisites/m:maven', namespaces=ns) != minimum:
        raise RuntimeError('The installed plugin POM does not declare the supported Maven minimum.')
    with ZipFile(artifact / f'sbom-verifier-maven-plugin-{version}.jar') as jar:
        descriptor = ET.fromstring(jar.read('META-INF/maven/plugin.xml'))
    if descriptor.findtext('requiredMavenVersion') != minimum:
        raise RuntimeError('The plugin descriptor and POM declare different Maven minimums.')

    executable = args.maven_home.resolve() / 'bin' / ('mvn.cmd' if os.name == 'nt' else 'mvn')
    if not executable.is_file():
        parser.error(f'Maven executable does not exist: {executable}')
    with tempfile.TemporaryDirectory(prefix='sbom-verifier-runtime-') as temp:
        consumer = Path(temp)
        (consumer / 'pom.xml').write_text(f'''<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>example</groupId>
  <artifactId>runtime-check</artifactId>
  <version>1</version>
  <packaging>pom</packaging>
  <build><plugins><plugin>
    <groupId>de.grobmeier</groupId>
    <artifactId>sbom-verifier-maven-plugin</artifactId>
    <version>{version}</version>
    <configuration><rules><completeness/></rules></configuration>
  </plugin></plugins></build>
</project>
''', encoding='utf-8')
        result = subprocess.run(
            [str(executable), '-B', '-ntp', '--show-version',
             f'-Dmaven.repo.local={args.local_repository.resolve()}', coordinates + ':check'],
            cwd=consumer, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(result.stdout, end='')
    if args.expect == 'unsupported':
        message = f'The plugin {coordinates} requires Maven version {minimum}'
        if result.returncode == 0 or message not in result.stdout:
            raise RuntimeError('Unsupported Maven did not report the required version.')
        if 'NoSuchElementException' in result.stdout or 'Failed to instantiate' in result.stdout:
            raise RuntimeError('Unsupported Maven reached rule loading before the version check.')
        if 'PluginIncompatibleException' not in result.stdout:
            raise RuntimeError('Maven did not reject the plugin through its prerequisite check.')
    elif result.returncode != 0 or 'BUILD SUCCESS' not in result.stdout:
        raise RuntimeError('Supported Maven could not load and execute the completeness rule.')
    print(f'Runtime requirement verified: {args.expect}.')


if __name__ == '__main__':
    main()
