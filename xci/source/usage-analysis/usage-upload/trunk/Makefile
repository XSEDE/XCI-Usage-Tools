.PHONY: install uploadapp package upload python-virtualenv upload_APP.cron upload_APP.conf upload_APP.sh usage_tools APP_history_parser.py APP_parser.py
VER= $(shell cat VERSION)
REL= $(shell cat RELEASE)
SHELL= /bin/bash
PYTHON ?= python
PREFIX ?= /usr/local/usage-upload

BUNDLE_NAME= usage-upload-$(VER)-$(REL)
SOURCE_NAME= usage-upload-$(VER)
BUILD_BASE= /tmp/usage-upload-build
BUNDLE_DIR= $(BUILD_BASE)/$(BUNDLE_NAME)

VENV_BASE= $(PREFIX)/python

ifeq (, $(shell which $(PYTHON)))
$(error "Missing required $(PYTHON)")
endif
ifeq (, $(shell which virtualenv))
$(error "Missing required virtualenv in $(PATH)")
endif

all: help

help:
	@echo
	@echo 'Available Targes:'
	@echo '  make install'
	@echo '  make APP=<myapp> uploadapp'
	@echo '  make package'
	@echo '  make upload'
	@echo
	@echo 'Optionally use:'
	@echo '   make PYTHON=python3 install'

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

python-virtualenv:
	@echo "** Initializing Python Virtualenv in $(VENV_BASE)"
	virtualenv $(VENV_BASE)
	( source $(VENV_BASE)/bin/activate ; \
	    $(VENV_BASE)/bin/pip --disable-pip-version-check install --upgrade pip )
	( source $(VENV_BASE)/bin/activate ; \
	    $(VENV_BASE)/bin/pip install numpy )
	( source $(VENV_BASE)/bin/activate ; \
	    $(VENV_BASE)/bin/pip install paramiko )
	( source $(VENV_BASE)/bin/activate ; \
	    $(VENV_BASE)/bin/pip install pytz )

ifeq ($(APP),glue2)
CRON_SRC=bin/upload_glue2.cron.in
uploadapp: uploadapp_var usage_tools upload_APP.cron upload_APP.conf APP_history_parser.py upload_APP.sh
else ($(APP),rabbitmqadmin)
uploadapp: uploadapp_var rabbitmq_admin_merge
else
CRON_SRC=bin/upload_template.cron.in
uploadapp: uploadapp_var usage_tools upload_APP.cron upload_APP.conf APP_parser.py
endif

uploadapp_var:
	$(if $(APP),, $(error APP variable not set))

usage_tools:
	@echo "** Generating bin tools"
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	   bin/usage_sync.py.in >$(PREFIX)/bin/usage_sync.py
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	   bin/usage_splitter.py.in >$(PREFIX)/bin/usage_splitter.py
    
upload_APP.cron:
	@echo "** Generating $(PREFIX)/bin/upload_$(APP).cron"
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
 	     -e "s|%LD_LIBRARY_PATH%|$(LD_LIBRARY_PATH)|g" \
	     -e "s|%APP%|$(APP)|g" \
	     -e "s|%PYTHON%|$(PYTHON)|g" \
	     $(CRON_SRC) >$(PREFIX)/bin/upload_$(APP).cron.new
	@chmod 755 $(PREFIX)/bin/upload_$(APP).cron.new
	@cp -p --backup=numbered $(PREFIX)/bin/upload_$(APP).cron.new $(PREFIX)/bin/upload_$(APP).cron

upload_APP.sh:
	@cp -p bin/upload_$(APP).sh $(PREFIX)/bin/upload_$(APP).sh

upload_APP.conf:
	@echo "** Generating $(PREFIX)/etc/upload_$(APP).conf"
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	     -e "s|%LD_LIBRARY_PATH%|$(LD_LIBRARY_PATH)|g" \
	     -e "s|%APP%|$(APP)|g" \
	     -e "s|%PYTHON%|$(PYTHON)|g" \
	   etc/upload_template.conf.in >$(PREFIX)/etc/upload_$(APP).conf.new
	@chmod 644 $(PREFIX)/etc/upload_$(APP).conf.new
	@cp -p --backup=numbered $(PREFIX)/etc/upload_$(APP).conf.new $(PREFIX)/etc/upload_$(APP).conf

APP_history_parser.py:
	@echo "** Generating $(PREFIX)/bin/$(APP)_history_parser.py"
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	     -e "s|%PYTHON%|$(PYTHON)|g" \
	   bin/$(APP)_history_parser.py >$(PREFIX)/bin/$(APP)_history_parser.py
	@chmod 755 $(PREFIX)/bin/$(APP)_history_parser.py

APP_parser.py:
	@if [ -a bin/$(APP)_parser.py.in ] ; \
        then \
	    echo "** Generating $(PREFIX)/bin/$(APP)_parser.py" ; \
	    sed -e "s|%PREFIX%|$(PREFIX)|g" \
	        -e "s|%PYTHON%|$(PYTHON)|g" \
	       bin/$(APP)_parser.py.in >$(PREFIX)/bin/$(APP)_parser.py ; \
	    chmod 755 $(PREFIX)/bin/$(APP)_parser.py ; \
        fi;

rabbitmq_admin_merge:
	@echo "** Generating $(PREFIX)/bin/rabbitmq_merge_access_log ..."
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
 	     -e "s|%LD_LIBRARY_PATH%|$(LD_LIBRARY_PATH)|g" \
	   bin/rabbitmq_merge_access_log.cron.in >$(PREFIX)/bin/rabbitmq_merge_access_log.cron
	@chmod 755 $(PREFIX)/bin/rabbitmq_merge_access_log.cron
	@sed -e "s|%PREFIX%|$(PREFIX)|g" \
	   bin/rabbitmq_merge_access_log.py.in >$(PREFIX)/bin/rabbitmq_merge_access_log.py
	@chmod 755 $(PREFIX)/bin/rabbitmq_merge_access_log.py

package:
	@echo "** Building package $(BUILD_BASE)/$(BUNDLE_NAME).tgz"
	@if [ ! -d $(BUILD_BASE) ] ; then mkdir $(BUILD_BASE) ; fi
	@if [ ! -d $(BUNDLE_DIR) ] ; then mkdir $(BUNDLE_DIR) ; fi
	@if [ -z "$(ls -A $(BUNDLE_DIR))" ] ; then rm -fr $(BUNDLE_DIR)/* ; fi
	@mkdir $(BUNDLE_DIR)/bin
	cp -p bin/* $(BUNDLE_DIR)/bin/
	@mkdir $(BUNDLE_DIR)/etc
	cp -p etc/* $(BUNDLE_DIR)/etc/
	cp -p VERSION RELEASE Makefile $(BUNDLE_DIR)/
	sed -e "s|%VER%|$(VER)|g" \
	    -e "s|%REL%|$(REL)|g" \
       README.in >$(BUNDLE_DIR)/README
	tar -C $(BUILD_BASE) -czf $(BUILD_BASE)/$(BUNDLE_NAME).tgz $(BUNDLE_NAME)/

upload:
	scp -p $(BUILD_BASE)/$(BUNDLE_NAME).tgz software.xsede.org:/local/software.xsede.org/development/usage-analysis/
	scp -p $(BUILD_BASE)/$(BUNDLE_NAME)/README software.xsede.org:/local/software.xsede.org/development/usage-analysis/$(BUNDLE_NAME).README
