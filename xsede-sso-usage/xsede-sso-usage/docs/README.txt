0. This document explains how to:

   A) Make XSEDE SSO Usage distribution files (RPMS, SRPMS, source)
      Prerequisites:
        rpmbuild

   B) Sign and upload distribution files to XSEDE distribution locations
      Prerequisites:
        A personal developer/packager GnuPG/GPG key:
           4096 bit RSA with SHA2 digest preference
           Submitted to SD&I for addition to XSEDE's known developer keys package
        RPM 4.4.x or newer (CentOS 5, RHEL 5, etc.) to generate V3 signatures
        To upload to Development repository:
           A software.xsede.org account in the 'devsoft' group
              With "sudo -u xsedesig" ability to rebuild YUM developmen repo
        To upload/copy to Production repository:
           A software.xsede.org account in the 'prodsoft' and 'gigsec' groups
              With "sudo -u xsedesig" ability to sign RPMs with XSEDE signature
              With "sudo -u xsedesig" ability to rebuild YUM production repo

To set SHA2 digest preference set these options in your ~/.gnupg/gpg.conf:
   personal-digest-preferences SHA256
   cert-digest-algo SHA256
   default-preference-list SHA256 SHA512 SHA384 SHA224 AES256 AES192 AES CAST5
ZLIB BZIP2 ZIP Uncompressed

###############################################################################
# Making XSEDE SSO Usage distribution files (RPMS, SRPMS, source)
###############################################################################

1. Increment the contents of the VERSION file, for example from 1.0 to 1.1.
   Set the contents of the RELEASE file to 1 if releasing a new version, or
   increment the contents by 1 if you are fixing an existing version.

2. Update the %changelog section at the end of xsede-sso-usage.spec.in
   maintaining the format shown in earlier messages. Make sure the latest
   log entry is at the top of the section. Make sure there's a blank line
   separating one log entry from the previous one.

3. Run "make". A successful build will result in the the following being created:

   a. RPM in rpmbuild/RPMS/noarch directory
   b. tar-ball with the tar.gz suffix in the current directory

4. Test-install the RPM as below; make sure $HOME/tmp has the right contents:
   $ sudo rpm -Uvh --prefix $HOME/tmp/ <rpm-file>

5. View the changelog:
   $ rpm -q --changelog <rpm-name-version>

6. Verify the contents of $HOME/tmp/ for the updates noted in the changelog.

7. After verifying the contents in $HOME/tmp/, delete the package.
   (NOTE: substitute version and release in the below command).
   $ sudo rpm -e <xsede-sso-usage-version-release>

###############################################################################
# Sign and upload distribution files to XSEDE distribution locations
# Using the instructions in the README-yum.txt file
###############################################################################
