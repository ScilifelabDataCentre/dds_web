# 20. Improve PyPI package security with 2FA

Date: 2023-01-23

## Status

Accepted

## Context

During the threat- and risk assessment of the DDS, the following possible threat was discovered regarding the CLI: 

| Threat | Cause | Consequence |
|--------|-------|-------------|
| An unauthorized (by us) change in the code | The change is not detected | Sensitive data is not encrypted |

In order to mitigate this threat, we decided to investigate the following possible improvements:

* Provide a checksum for the package published on PyPi and recommend that the users installing `dds-cli` also verify the integrity of the package
* Cryptographically sign the package published on PyPi and allow users installing `dds-cli` to verify the packages origin

Both generating the checksum and signing the package needs to occur prior to publishing the CLI to PyPi.

### Providing a checksum 

* Hashes are automatically generated and uploaded to PyPI upon publishing packages. These hashes are available on the ["Download files" page](https://pypi.org/project/dds-cli/#files)

    * You can view the hashes by clicking "view hashes", either in the *Source Distribution* or *Built Distribution* section
    * The hashes are also available via the PyPI API

* Installing `dds-cli` with `pip install dds-cli` (as the documentation currently states) followed by generating the hash with e.g. `pip hash <path to dds>` does not generate a checksum matching the hash displayed on PyPI. 
    
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

* Downloading `dds-cli` with `pip download dds-cli` downloads the `whl` distribution files for *all* the `dds-cli` requirements. An additional `--dest` option to specify the destination of all files would be needed in the command. The checksum verification is performed on the whl distribution file. An installation command after the download is required in order for the package to be usable: `pip install <path to dds_cli whl>.`. 

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

    * Downloading the package (step 1) via the browser is possible, the following steps (2-4) are only possible via the terminal.

* The main principal of adding the hashes is that we should not blindly trust third party software.
    * Regarding PyPI: We do not ourselves generate the hashes available on PyPI; PyPI does. Therefore, verifying the hashes cannot guarantee that what we intend to publish is installed by the users. 
    * Regarding dependencies: If the CLI is installed via `pip install dds-cli`, there's a file with hashes for each package. If it's installed by first downloading with `pip download dds-cli`, all dependency `whl` distribution files are also downloaded. These package checksums could be verified by creating- and running a custom shell- or python script. 
        * It's possible to require matching hashes from all dependencies. This blocks the installation if a package either does not have a hash, or the hash does not match. 

### Cryptographically sign package





Att signera paketen innan publicering till PyPi är väldigt ovanligt bland alla paket på PyPi. Det är tekniskt möjligt att göra detta men det är inte uppmuntrat ("discouraged" https://github.com/pypa/gh-action-pypi-publish/discussions/67 eftersom att det knappt är användbart), det finns inga riktiga verktyg för det, och det finns i princip inga instruktioner om hur man gör det. Jag har även frågat runt både inom DC men också NBIS och generellt bland utvecklare, ingen verkar veta hur man gör. Om vi skulle göra detta trots att PyPi verkar ta bort funktionaliteten lite allt eftersom, så skulle jag behöva komma fram till en egen lösning på hur man gör detta och hoppas på att det bidrar till någon sorts säkerhet - det känns inte speciellt bra.

## Decision

* Vi borde inte ändra vårat rekommenderade installationskommando för att tillåta hash verifiering. Däremot kan vi lägga till en mening som förklarar hur man gör, ifall att någon vill detta.
    - Våra användare klarar knappt av att köra det vanliga pip install dds-cli  ibland så det är inte rimligt att ändra rekommendationen till pip download osv.
    - Samma tema: Att köra ytterligare ett kommando för att kolla hashes - 1. de kan inte 2. de kommer inte att göra det
    - Det finns möjlighet att kräva att alla paket som dds-cli behöver för att fungera ska ha en hash, vilket isf blockerar installationen om något paket saknar en hash, men alla paket har inte det, och de som har det har lagrat dem i olika typer av filer och format, så alla hashes känns inte igen, dvs vi kan inte använda detta för att verifiera riktigheten i våra requirements.

* Vi borde inte spendera tid på att signera paketet innan publicering till PyPi - det är inte uppmuntrat och vi ska inte börja implementera saker som officiella sidor markerat som "discouraged" och "not to be relied on long term".
* Vi borde säkra upp kontot på PyPi med 2FA så att vi gör vad vi kan för att undvika intrång och att någon annan skapar en ny API key (vilket skulle ge någon möjlighet att publicera en "fake"/skadlig dds-cli version) - Denna del har jag redan gjort. :white_check_mark:

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
