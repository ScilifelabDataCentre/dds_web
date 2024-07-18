# For Linux and MacOS users only and assumes brew is already installed
TECH_MARKDOWN_FILE := doc/technical-overview.md
PDF_OUTFILE := dds_web/static/dds-technical-overview.pdf

install_pandoc:
	brew install pandoc

update_tlmgr:
	tlmgr update --self
	tlmgr install cm-super fontaxes lato pdflscape xkeyval

build_tech_overview_pdf: update_tlmgr $(TECH_MARKDOWN_FILE)
	pandoc $(TECH_MARKDOWN_FILE) -o $(PDF_OUTFILE)

.PHONY: update_tlmgr build_tech_overview_pdf all
