###############################################################################
# Sign and upload distribution files to XSEDE distribution locations
#
# Note: these instructions will be further developed as part of SDIACT-124, 
# which will be ready later in Increment 5, and are included temporarily here 
# so that they are available in this package.
###############################################################################

1. Sign files to be distributed with your GnuPG personal developer/packager
    key. If desired have others sign them also. Put the signed files in the
    original directories with the same file names as created above. Steps:

 a) RPMs under rpmbuild/RPMS and SRPM under rpmbuild/SRPMS
    # First make sure your ~/.rpmmacros has:
    %_signature gpg
    %_gpg_name <the_name_of_the_gpg_signing_key>

    # if you are running on a CentOS 6 or higher, also add the following to
    # ~/.rpmmacros in order force rpm to sign with a v3 signature
    %__gpg_sign_cmd %{__gpg} \
        gpg --force-v3-sigs --digest-algo=sha256 --batch --no-verbose --no-armor \
            --passphrase-fd 3 --no-secmem-warning -u "%{_gpg_name}" \
            -sbo %{__signature_filename} %{__plaintext_filename}

    Then for each RPM under rpmbuild/ run:
    $ rpm --addsign rpmbuild/<subpath>/<file_name>.rpm

 b) Source tar under rpmbuild/SOURCES
    # If you have multiple keys use "--local-user <name>" to select one
    $ gpg --output rpmbuild/SOURCES/xsede-sso-usage-<VERSION>.tar.gz.sig \
        --detach-sign rpmbuild/SOURCES/xsede-sso-usage-<VERSION>.tar.gz

2. Email software-serv-admin@xsede.org and ask that your host's IP address be
   added to hosts.allow on software.xsede.org so that your machine doesn't
   get automatically blocked when running the repository management scripts
   repeatedly.  Also setup ssh-agent access to software.xsede.org so that the
   scripts can connect multiple times without you having to repeatedly type
   the passphrase.  An example of running ssh-agent:

    $ exec /usr/bin/ssh-agent $SHELL
    $ ssh-add
<enter passphrase for key>

    Then test access by executing a simple command via SSH and verify that it
    does not prompt for a passphrase
    $ ssh software.xsede.org hostname
software.xsede.org

3. Upload RPMs, source tar, JKS files, and their signatures, to development
    repository, and automatically rebuild the YUM repositories as follows:
    
    ./sbin/upload [-u <username on software.xsede.org]

    Use the -u argument if you are running on a host with a different username
    than the one you have on software.xsede.org.  If you re-upload the same
    version and release ignore this error: mkdir: cannot create directory ...
    File exists If you are testing after another tester, ignore errors with
    this string: Operation not permitted

4. If packages are intended for development notify developers.
   If packages need to be tested notify the testing team.

5. When packages are ready for production release, sign them with the XSEDE
    Software signature, copy them to production repositories and rebuild the
    YUM repositories as follows:

    ./sbin/copy_development_to_production [-t] [-u <username on software.xsede.org]

    Use the -t option to run in testing mode (i.e., puts the files in 
    http://software.xsede.org/production-test/repo) and the -u argument if you
    are running on a host with a different username than the one you have on
    software.xsede.org.  
    Ignore 'gpg: WARNING: standard input reopened' messages
    Look for success messages 'Pass phrase is good.'

6. Announce new RPM, tar, and JKS availability to Service Providers and other users.
