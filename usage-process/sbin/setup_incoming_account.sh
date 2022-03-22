#!/bin/bash
###############################################################################
# Create an account for uploading usage information
###############################################################################

ME=$(basename "${0}")
USAGE="Usage: ${ME} -l LOGIN -d DESCRIPTION [-k]"

GENKEY=0
while getopts "l:d:k" arg; do
    case "$arg" in
        l)  LOGIN=$OPTARG
            ;;
        d)  DESCRIPTION=$OPTARG
            ;;
        k)  GENKEY=1
            ;;
        \?)
            echo ${USAGE}
            exit 1
            ;;
    esac
done

if [[ "${LOGIN}" == "" ]]; then
    echo "Missing LOGIN"
    echo ${USAGE}
    exit 1
fi

if [[ "${DESCRIPTION}" == "" ]]; then
    echo "Missing DESCRIPTION"
    echo ${USAGE}
    exit 1
fi

id ${LOGIN} &>/dev/null
if [[ $? == 0 ]]; then
    echo "Account '${LOGIN}' already exists"
    exit 1
fi

BASE="/incoming/home"

useradd --create-home --base-dir ${BASE} --comment "${DESCRIPTION}" --gid incoming --shell /bin/scponly --skel /soft/XCI-Usage-Tools/PROD/usage-process/skel ${LOGIN}
if [[ $? != 0 ]]; then
    echo "useradd failed with rc=$?"
    exit 1
fi
echo "useradd ${LOGIN} worked"

HOME=${BASE}/${LOGIN}
semanage fcontext -at user_home_t ${HOME}
if [[ $? != 0 ]]; then
    echo "semanage fcontext .. of ${HOME} failed with rc=$?"
    exit 1
fi

chown root.root ${HOME}/.ssh
if [[ $? != 0 ]]; then
    echo "chown root .ssh failed with rc=$?"
    exit 1
fi

semanage fcontext -at ssh_home_t ${HOME}/.ssh
if [[ $? != 0 ]]; then
    echo "semanage fcontext .. of .ssh failed with rc=$?"
    exit 1
fi

if [[ ${GENKEY} == 1 ]];then
    echo "Generating ssh key pair"
    ssh-keygen -q -N '' -t rsa -f ${HOME}/.ssh/id_rsa
    if [[ $? != 0 ]]; then
        echo "ssh-keygen failed with rc=$?"
        exit 1
    fi
    echo "Populating authorized_keys"
    cp -p ${HOME}/.ssh/id_rsa.pub ${HOME}/.ssh/authorized_keys
    if [[ $? != 0 ]]; then
        echo "Populate authorized_keys failed with rc=$?"
        exit 1
    fi
    chmod 444 ${HOME}/.ssh/authorized_keys
    if [[ $? != 0 ]]; then
        echo "chmod authorized_keys failed with rc=$?"
        exit 1
    fi
    semanage fcontext -at ssh_home_t /incoming/home/info/.ssh/authorized_keys
    if [[ $? != 0 ]]; then
        echo "semanage fcontext .. of authorized_keys failed with rc=$?"
        exit 1
    fi
fi

restorecon -Rv ${HOME}
if [[ $? != 0 ]]; then
    echo "restorecon ${HOME} failed with rc=$?"
    exit 1
fi
echo "Success"
