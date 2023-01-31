# 20. Improve PyPI package security with 2FA

Date: 2023-01-23

## Status

Accepted

## Context

During the threat- and risk assessment of the DDS, the following possible threat was discovered regarding the CLI:

| Threat                                     | Cause                      | Consequence                     |
| ------------------------------------------ | -------------------------- | ------------------------------- |
| An unauthorized (by us) change in the code | The change is not detected | Sensitive data is not encrypted |

In order to mitigate this threat, we decided to investigate the following possible improvements:

- Provide a checksum for the package published on PyPI and recommend that the users installing `dds-cli` also verify the integrity of the package
- Cryptographically sign the package published on PyPI and allow users installing `dds-cli` to verify the packages origin

Both generating the checksum and signing the package needs to occur prior to publishing the CLI to PyPI.

### Providing a checksum

- Hashes are automatically generated and uploaded to PyPI upon publishing packages. These hashes are available on the ["Download files" page](https://pypi.org/project/dds-cli/#files)

  - You can view the hashes by clicking "view hashes", either in the _Source Distribution_ or _Built Distribution_ section
  - The hashes are also available via the PyPI API

- Installing `dds-cli` with `pip install dds-cli` (as the documentation currently states) followed by generating the hash with e.g. `pip hash <path to dds>` does not generate a checksum matching the hash displayed on PyPI.

  ```bash
  # SHA256 hash for dds_cli-2.2.5-py3-none-any.whl: 8ba6495b73d759e96c35652273cf4e4158acba02f1cf64f012cc67cf2e346cae

  # 1. Install dds-cli
  pip install dds-cli

  # 2. Get path to dds command
  which dds
  # /home/<user>/dds-venv/bin/dds

  # 3. Generate checksum for dds
  pip hash /home/<user>/dds-venv/bin/dds
  # /home/<user>/dds-venv/bin/dds:
  # --hash=sha256:88dd1285dacb2c2bcf314aec2c940a774c801167a26e5f93f90c649fbed2e9a0
  ```

- Downloading `dds-cli` with `pip download dds-cli` downloads the `whl` distribution files for _all_ the `dds-cli` requirements. An additional `--dest` option to specify the destination of all files would be needed in the command. The checksum verification is performed on the whl distribution file. An installation command after the download is required in order for the package to be usable: `pip install <path to dds_cli whl>.`.

  ```bash
  # SHA256 hash for dds_cli-2.2.5-py3-none-any.whl: 8ba6495b73d759e96c35652273cf4e4158acba02f1cf64f012cc67cf2e346cae

  # 1. Download dds-cli
  pip download dds-cli --dest dds-downloaded

  # 2. Generate checksum for dds whl
  pip hash dds-downloaded/dds_cli-2.2.5-py3-none-any.whl
  # dds_cli-2.2.5-py3-none-any.whl:
  # --hash=sha256:8ba6495b73d759e96c35652273cf4e4158acba02f1cf64f012cc67cf2e346cae

  # 3. Verify that the hashes match
  if [ "<correct hash>" = "<generated hash>" ]; then echo "Package integrity verified"; else echo "Package compromised!"; fi
  # Package integrity verified

  # 4. Install the dds-cli
  pip install dds-downloaded/dds_cli-2.2.5-py3-none-any.whl
  ```

  - Downloading the package (step 1) via the browser is possible, the following steps (2-4) are only possible via the terminal.

- The main principal of adding the hashes is that we should not blindly trust third party software.

  - Regarding PyPI: We do not ourselves generate the hashes available on PyPI - PyPI does. Therefore, verifying the hashes cannot guarantee that what we intend to publish is installed by the users.
  - Regarding dependencies: If the CLI is installed via `pip install dds-cli`, there's a file with hashes for each package. If it's installed by first downloading with `pip download dds-cli`, all dependency `whl` distribution files are also downloaded. These package checksums could be verified by creating- and running a custom shell- or python script.
    - It's possible to require matching hashes from all dependencies. This blocks the installation if a package either does not have a hash, or the hash does not match.

- Many users are not familiar with (or happy about) using the terminal and a high priority item in our backlog is to implement a UI (e.g. web interface) allowing the users to collect their data without needing to execute shell commands. Recommending additional commands prior to running `dds` will not only be unpopular but also lead to an increase in support tickets to both us and the units.

### Cryptographically sign package

- The development version of `dds-cli` is automatically published to TestPyPI when a PR is created or when there's a change in the `dev` branch. The production version is (also automatically) published to PyPI when a new release is made.
- The publishing of the package is handled by the GitHub Action [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish). This runs `twine` which is what runs the publication to PyPI / TestPyPI. Twine itself has the `--sign` option which tells twine to sign the package prior to publishing it. At this time, it appears the GitHub Action used does not support this. This is likely due to that the functionality is discouraged and barely usable: https://github.com/pypa/gh-action-pypi-publish/discussions/67.
- Despite being discouraged, it's technically possible to sign the package; You can generate the signature prior to the upload and place it next to the distribution. This will upload both the package and the signature. See the link above.
- If one was to sign the package, it would not be available on PyPI via the browser. It is, however, possible to collect them via the PyPI API.
- There is no proper tool for working with signatures for PyPI, and during the investigation to find a solution for this we have not found an example, clear suggestion or instructions on how to do it. We would therefore need to create our own solution.
- Signatures on PyPI appear to be very rare, likely due to the points above. We have asked within Data Centre, NBIS and systems developers in general, and also done extensive research; No one seems to have experience with this, or know how to do do it.

## Decision

- We will _not_ change the recommended installation procedure from `pip install dds-cli` to `pip download dds-cli`, followed by hash verification.
- We _will_ add instructions to the documentation showing how you can verify the package integrity, _if they want to_.
- We will _not_ require hashes for all package dependencies; Not all packages provide hashes and those that do have stored them in varying files and formats, thus not all hashes will be found or recognized.
- We will _not_ spend time on signing the `dds-cli` package prior to publishing it to PyPI; We should not implement any functionality which is barely used, PyPI itself does not support in a good way, there are no proper available tools for, are marked as discouraged and will possibly be phased out.
- We _will_ secure our PyPI account by activating 2FA.

## Consequences

- Users will have the option to choose which installation method they want to use and if they want to verify the package integrity prior to running it.
- 2FA will reduce the risk of a breach and thereby prevent an unauthorized entity creating a new API key on our account. A new API key would allow the unauthorized entity to impersonate the SciLifeLab Data Centre and publish a new, fake, and possibly harmful version of the CLI.

## Relevant links

- https://pypi.org/project/dds-cli/#files
- https://peps.python.org/pep-0541/
- https://github.com/pypa/gh-action-pypi-publish/discussions/67
- https://security.stackexchange.com/questions/79326/which-security-measures-does-pypi-and-similar-third-party-software-repositories
- https://pip.pypa.io/en/stable/topics/secure-installs/
- https://security.stackexchange.com/questions/175425/pip-verify-packet-integrity
- https://github.com/pypi/warehouse/issues/3356
