
RPMBUILD= /usr/bin/rpmbuild

RPMBUILD_TOPDIR= $(PWD)/rpmbuild

VER= $(shell cat VERSION)
REL= $(shell cat RELEASE)
#VER= $(shell echo `grep -i "^Version:" xsede-sso-usage.spec | sed -e "s/^Version:[ ]*//"`)

BUNDLE_NAME= xsede-sso-usage-$(VER)-$(REL)
SOURCE_NAME= xsede-sso-usage-$(VER)

all: rpm

rpm: tarball
	echo $(RPMBUILD_TOPDIR)
	mkdir -p $(RPMBUILD_TOPDIR)/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
	mv $(SOURCE_NAME).tar.gz $(RPMBUILD_TOPDIR)/SOURCES/
	cp docs/USER_GUIDE.txt $(RPMBUILD_TOPDIR)/SOURCES/
	chmod 444 $(RPMBUILD_TOPDIR)/SOURCES/USER_GUIDE.txt
	sed -e "s/%VER%/$(VER)/g" -e "s/%REL%/$(REL)/g" \
		xsede-sso-usage.spec.in \
		>$(RPMBUILD_TOPDIR)/SPECS/xsede-sso-usage.spec
	$(RPMBUILD) --define '_topdir $(RPMBUILD_TOPDIR)' --buildroot $(RPMBUILD_TOPDIR)/BUILDROOT -ba $(RPMBUILD_TOPDIR)/SPECS/xsede-sso-usage.spec

tarball: clean
	mkdir -p $(BUNDLE_NAME)
	cp sso-gsissh-logins.py $(BUNDLE_NAME)/sso-gsissh-logins
	cp sso-max-sim-logins.py $(BUNDLE_NAME)/sso-max-sim-logins
	cp sso-num-logins.py $(BUNDLE_NAME)/sso-num-logins
	cp sso-num-unique-users.py $(BUNDLE_NAME)/sso-num-unique-users
	cp gsissh.rules $(BUNDLE_NAME)/gsissh.rules
	tar cvzf $(BUNDLE_NAME).tar.gz $(BUNDLE_NAME)
	ln -s $(BUNDLE_NAME) $(SOURCE_NAME)
	tar cvzf $(SOURCE_NAME).tar.gz $(SOURCE_NAME) $(BUNDLE_NAME)

clean:
	rm -fr $(SOURCE_NAME)
	rm -fr $(BUNDLE_NAME).tar.gz
	rm -fr $(BUNDLE_NAME)
	rm -fr $(RPMBUILD_TOPDIR)
