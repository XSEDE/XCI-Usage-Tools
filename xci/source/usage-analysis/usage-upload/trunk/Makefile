.PHONY: python-virtualenv uploadapp usage_tools package upload
VER= $(shell cat VERSION)
REL= $(shell cat RELEASE)
SHELL= /bin/bash
#----------------------------------------------------
# CUSTOMIZE THE FOLLOWING VARIABLES
#
PREFIX= /soft/usage-upload
PYTHON_PREFIX= /
PYTHON_LIB= /lib64
#PYTHON_PREFIX= /Library/Frameworks/Python.framework/Versions/3.6
#PYTHON_LIB= /Library/Frameworks/Python.framework/Versions/3.6/lib
#
# CUSTOMIZE END
#----------------------------------------------------

BUNDLE_NAME= usage-upload-$(VER)-$(REL)
SOURCE_NAME= usage-upload-$(VER)
BUILD_BASE= /tmp/usage-upload-build
BUNDLE_DIR= $(BUILD_BASE)/$(BUNDLE_NAME)

VENV_BASE= $(PREFIX)/python

all: help

help:
	@echo
	@echo 'Available Targes:'
	@echo '  make install'
	@echo '  make APP=<myapp> uploadapp'
	@echo '  make package'
	@echo '  make upload'
	@echo

install: python-virtualenv
	@echo "** Installing usage-upload-$(VER)-$(REL)"
	@if [ ! -d $(PREFIX)/bin ] ; then mkdir $(PREFIX)/bin ; fi
	@if [ ! -d $(PREFIX)/etc ] ; then mkdir $(PREFIX)/etc ; fi
	@if [ ! -d $(PREFIX)/tmp ] ; then mkdir $(PREFIX)/tmp ; fi
	@if [ ! -d $(PREFIX)/upload ] ; then mkdir $(PREFIX)/upload ; fi
	@if [ ! -d $(PREFIX)/var ] ; then mkdir $(PREFIX)/var ; fi
	sed -e "s|%PREFIX%|$(PREFIX)|g" \
	   bin/upload_usage.py.in >$(PREFIX)/bin/upload_usage.py
	chmod 755 $(PREFIX)/bin/upload_usage.py

python-virtualenv: $(VENV_BASE)/bin/python

$(VENV_BASE)/bin/python:
	@echo "** Initializing Python Virtualenv in $(VENV_BASE)"
	LD_LIBRARY_PATH=${PYTHON_LIB} $(PYTHON_PREFIX)/bin/virtualenv $(VENV_BASE)
	( export LD_LIBRARY_PATH=${PYTHON_LIB} ; \
	    source $(VENV_BASE)/bin/activate ; \
	    pip --no-cache-dir install paramiko; \
	    pip --no-cache-dir install pytz )

ifeq ($(APP),glue2)
CRON_SRC=bin/upload_glue2.cron.in
uploadapp: uploadapp_var usage_tools $(PREFIX)/bin/upload_$(APP).cron $(PREFIX)/etc/upload_$(APP).conf $(PREFIX)/bin/$(APP)_history_parser.conf $(PREFIX)/bin/upload_$(APP).sh
else
CRON_SRC=bin/upload_template.cron.in
uploadapp: uploadapp_var usage_tools $(PREFIX)/bin/upload_$(APP).cron $(PREFIX)/etc/upload_$(APP).conf $(PREFIX)/bin/$(APP)_parser.conf
endif

uploadapp_var:
	$(if $(APP),, $(error APP variable not set))

usage_tools:
	@cp -p bin/usage_sync.py $(PREFIX)/bin/usage_sync.py
	@cp -p bin/usage_splitter.py $(PREFIX)/bin/usage_splitter.py
    
$(PREFIX)/bin/upload_$(APP).cron:
	@echo "** Generating $(PREFIX)/bin/upload_$(APP).cron"
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	    -e "s|%PYTHON_PREFIX%|$(PYTHON_PREFIX)|g" \
	    -e "s|%PYTHON_LIB%|$(PYTHON_LIB)|g" \
	    -e "s|%APP%|$(APP)|g" \
	    $(CRON_SRC) >$(PREFIX)/bin/upload_$(APP).cron
	@chmod 755 $(PREFIX)/bin/upload_$(APP).cron

$(PREFIX)/bin/upload_$(APP).sh:
	@cp -p bin/upload_$(APP).sh $(PREFIX)/bin/upload_$(APP).sh

$(PREFIX)/etc/upload_$(APP).conf:
	@echo "** Generating $(PREFIX)/etc/upload_$(APP).conf"
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	    -e "s|%PYTHON_PREFIX%|$(PYTHON_PREFIX)|g" \
	    -e "s|%PYTHON_LIB%|$(PYTHON_LIB)|g" \
	    -e "s|%APP%|$(APP)|g" \
	   etc/upload_template.conf.in >$(PREFIX)/etc/upload_$(APP).conf
	@chmod 644 $(PREFIX)/etc/upload_$(APP).conf

$(PREFIX)/bin/$(APP)_parser.conf:
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	   bin/$(APP)_parser.py.in >$(PREFIX)/bin/$(APP)_parser.py
	chmod 755 $(PREFIX)/bin/$(APP)_parser.py

$(PREFIX)/bin/$(APP)_history_parser.conf:
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	   bin/$(APP)_history_parser.py >$(PREFIX)/bin/$(APP)_history_parser.py
	chmod 755 $(PREFIX)/bin/$(APP)_history_parser.py

package:
	@echo "** Building package $(BUILD_BASE)/$(BUNDLE_NAME).tgz"
	@if [ ! -d $(BUILD_BASE) ] ; then mkdir $(BUILD_BASE) ; fi
	@if [ ! -d $(BUNDLE_DIR) ] ; then mkdir $(BUNDLE_DIR) ; fi
	@if [ -z "$(ls -A $(BUNDLE_DIR))" ] ; then rm -fr $(BUNDLE_DIR)/* ; fi
	@mkdir $(BUNDLE_DIR)/bin
	cp -p bin/* $(BUNDLE_DIR)/bin/
	@mkdir $(BUNDLE_DIR)/etc
	cp -p etc/* $(BUNDLE_DIR)/etc/
	cp -p VERSION RELEASE README Makefile $(BUNDLE_DIR)/
	tar -C $(BUILD_BASE) -czf $(BUILD_BASE)/$(BUNDLE_NAME).tgz $(BUNDLE_NAME)/

upload:
	scp -p $(BUILD_BASE)/$(BUNDLE_NAME).tgz software.xsede.org:/local/software.xsede.org/development/usage-analysis/
	scp -p $(BUILD_BASE)/$(BUNDLE_NAME)/README software.xsede.org:/local/software.xsede.org/development/usage-analysis/$(BUNDLE_NAME).README
