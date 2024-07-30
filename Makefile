# For Linux and MacOS users only and assumes brew is already installed
TECH_MARKDOWN_FILE := doc/technical-overview.md
TECH_OVERVIEW_PDF := dds_web/static/dds-technical-overview.pdf
TROUBLE_MARKDOWN_FILE := doc/troubleshooting.md
TROUBLE_PDF := dds_web/static/dds-troubleshooting.pdf

install_pandoc:
	brew install pandoc

update_tlmgr:
	tlmgr update --self
	tlmgr install cm-super fontaxes lato pdflscape xkeyval

build_tech_overview_pdf: update_tlmgr $(TECH_MARKDOWN_FILE)
	pandoc $(TECH_MARKDOWN_FILE) -o $(TECH_OVERVIEW_PDF)

build_troubleshooting_pdf: update_tlmgr $(TROUBLE_MARKDOWN_FILE)
	pandoc $(TROUBLE_MARKDOWN_FILE) -o $(TROUBLE_PDF)

build_docs: build_tech_overview_pdf build_troubleshooting_pdf

.PHONY: update_tlmgr build_tech_overview_pdf build_troubleshooting_pdf build_docs all
