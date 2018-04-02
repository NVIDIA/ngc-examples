#!/bin/bash
#
# aws_create_instance.sh                         10/26/2017 13:15:00
#
# Copyright (c) 2017, NVIDIA CORPORATION.  All rights reserved.
#
# Example code to show how to 
#  1) conditionally create Security group for SSH if one doesn't exist
#  2) create a AWS P3 (or ubuntu test) image, and 
#  3) optionally create a persistent EBS (Elastic Block Storage) volume to it.
#  4) optionally mount EFS (Elastic File System) volumes to it
#  5) how to get IP address of instance and ssh into it
#  6) optionally shut down or terminate instance when exit ssh session.
#
# There is a companion script "aws_last.sh", that using infomation written to a
# small file here, can reconnect to a stopped or running instance based on 
# the saved InstanceId in that file. 
#
# This is example code only, it shows just the basic ways to script to the 
# aws commands in bash. It does little error checking. The code here just 
# provides the basic framework of how to start and control an aws instance
# in a bash command. It is not intended for production systems.
#
# Bringing up a aws instance and mounting multiple types of drives to it
# requires good number of custom parameters. The default values of these
# are all specified below. 
#
# A copy of this section, with all the paramters commented out is supplied 
# in a file "sample.cfg". It is read right after these default values are
# initialized, allowing the user to easly change the default behavior 
# without changing the setting in this file. This config file is read
# in optionally on the command line
#
# aws_create_instance [options] [sample.cfg] 
#
        # when creating all the parts, this is used as the prefix
        # to the "Name" tags that are placed on all those created
        # parts - this name has a partial timestamp in it. 

    NAME_TAG_PREFIX="$USER $(date +'%a %H:%M')"

        # ssh key defaults

        # where the .pem keys are on your machine
        # For example: "~/.ssh"

    KEY_PATH="<PATH WHERE YOU PUT THE AWS KEY>"

        # the name of the key you are going to use
        # For example: "me-key-pair-uswest2"

    KEY_NAME="<AWS SSH KEY NAME, NOT FILENAME>"

        # full path to ssh public key file
        # Using the examples above, it would be "/.ssh/me-key-pair-uswest2.pem"

    KEY_FILE=$KEY_PATH/$KEY_NAME.pem

        # instance information

        # region where you will run your instances
        # For example: "us-west-2" or "us-east-1"

    REGION="<WHERE YOU WILL RUN YOUR INSTANCE>"

        # Published AMI NAME 
        # This is the name that NVIDIA publishes to on the AWS MarketPlace

    IMAGE_NAME_FULL="NVIDIA Volta Deep Learning AMI-46a68101-e56b-41cd-8e32-631ac6e5d02b-ami-655e831f.4"
    IMAGE_NAME_WILD="NVIDIA Volta Deep Learning AMI*"
    AWS_MARKETPLACE_OWNER_ID="679593333241"  

    IMAGE_NAME="$IMAGE_NAME_WILD"        # wild card works if done right. Code is returing FIRST if multiple finds
    OWNER_ID=""                          # owner id can be supplied, but slower, so don't

        # So it only needs to be update in one place, here is the name of
        # the default AWS Ubuntu image that not support GPUs. It's here for
        # use by cfg files.  

    IMAGE_NAME_UBUNTU='ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-20170721'

        # login name burned into the above AMI at it's creation
        # Note that "ubuntu" is the default user of 'NVIDIA Volta Deep Learning AMI'

    LOGIN_NAME="ubuntu"

        # The NVIDIA AMI images have included the ubuntu 'nfs-common' package
        # which is used to connect to EFS volumes. The default AWS Ubuntu AMI does
        # not. This flag is used here to install it for you if you use non-NVIDIA ami

    INSTALL_NFS_COMMON="false"

        # Security group for instance, to allow SSH, pinging and digits
        # can use an existing security group, or can defined your own privite one here

    USE_EXISTING_SECURITY_GROUP="true"
    if [ "$USE_EXISTING_SECURITY_GROUP" == "true" ]; then

            # pre-existing security group - we will not delete it when done

            # Security Group Name - don't forget rhe single quotes!
            # For example: 'me_SG_uswest2'

        SSH_SECURITY_GROUP_NAME="<MY SECURITY GROUP NAME>"

        SECURITY_GROUP_CREATE_IF_NEEDED="false"    # if don't find group by given name stop 
    else

            # create your own security group.  
            # can delete it when exit SSH session (or use 'aws-last') if flag below set
            # pull timestamp out of NAME here if you want to reuse it across your sessions

            # My Security Group Name
            # This is the "Group Name" column in the EC2 Security Group GUI console.
            # This Group Name can not be changed once it is created.
            # For example: "$NAME_TAG_PREFIX me_SG_uswest2"

        SSH_SECURITY_GROUP_NAME="<MY NEW SECURITY GROUP NAME>"

            # These are flags that control this auto-create of a security
            # group by this script. 
            #
            # ..CREATE_IF_NEEDED:   if don't find group by given name, will create one
            # ..DELETE_IF_CREATED:  true to delete security group we create, IF we created it

        SECURITY_GROUP_CREATE_IF_NEEDED="true"
        SECURITY_GROUP_DELETE_IF_CREATED="true"

            # My Security Group Description
            # This is the "Description" column in the EC2 Security Group GUI console
            # This Description can not be changed once it is created.
            # For example: "Generated NVIDIA Volta SSH/Ping Security group"

        SSH_SECURITY_GROUP_DESCP="<MY SECURITY GROUP DESCRIPTION>"

            # My Security Group Name Tag
            # This is the "Name" column in the EC2 Security Group GUI console
            # This Name may be changed later after it is created.
            # For example: "$NAME_TAG_PREFIX me_SG_uswest2"

        SSH_SECURITY_GROUP_NAME_TAG="<MY SECURITY GROUP NAME TAG>"
               
            # Sample setup to:
            #  - enable only SSH, SSL, DIGITS6, and ping ingress ports
            #  - enable all exgress ports
            # Note that for the code in this script to work, that the ability i
            # to ping the instance must be enabled.

            #                    protocol,    to, from,         cidr_ip, description
        SSH_SECURITY_INGRESS_RULES=( "tcp,    22,   22,       0.0.0.0/0, For SSH"
                                     "tcp,   443,  443,       0.0.0.0/0, For SSL"
                                     "tcp,  5000, 5000,       0.0.0.0/0, For NVIDIA DIGITS6"
                                     "icmp,    8,   -1,       0.0.0.0/0, To allow to be pinged" 
                                   )
            #                    protocol,    to, from,         cidr_ip, description
        SSH_SECURITY_EGRESS_RULES=(
                                  )
    fi 

        # These are parameters that specify type of instance that is to be
        # created. This name indicates the number of CPUs, GPUs and memory
        # that will be allocated to the instance when it is created

    NAME_TAG="$NAME_TAG_PREFIX P3"             # what name we are calling it

        # these define the instance typpe, and the boot volume size
        # and type. 

    INSTANCE_TYPE=p3.2xlarge                   # p3 are Voltas, 2xLarge is 1GPU, 16xLarge is 8GPUs
    EBS_BOOT_VOLTYPE='gp2'                     # default 'gp2' or faster 'io1'
    EBS_BOOT_VOLSIZE=32                        # in GB
    EBS_BOOT_VOLIOPS_RATIO=25                  # for 'io1' only, max Ratio=50 (2017) Actual IOPS=SizeG*Ratio 

        # EFS (elastic file system) volumes are probably a better solution
        # for the NVIDIA Deep Learning usage as you can have a common data
        # source that's usable by mutiple instance. But in case you the instance
        # needs some private storage, a EBS (Elastic Block Storage) can be 
        # used. 
        # The biggest disadvantage of EBS is that they can't be shared
        # between running instances... 
        #
        # setting this field to "true" will create and add a private EBS
        # volume to the instance. Note that we set up this volume below to
        # auto delete when the instance is deleated. For boot volumes, this
        # makes sense, but AWS does provide was to prevent this if needed.

    CREATE_PRIVATE_EBS_VOLUME="false"          # true to create private EBS volume

        # parameter that specify the EBS volume type and size if 
        # it is enabled above

    EBS_DATA_VOLTYPE='gp2'                     # default 'gp2' or faster 'io1' Provisioned IOPS SSD
    EBS_DATA_VOLSIZE=32                        # in GiB
    EBS_DATA_VOLIOPS_RATIO=25                  # for 'io1' only, max Ratio=50 (2017) Actual IOPS=SizeG*Ratio 

        # These are parameters that the EFS will be mounted with.

    MOUNT_EFS_VOLUME="false"

        # quick and dirty way to assocatate a mount point with a EFS volume name
        #  <volume name>,<mount point>.. simple bash magic to follow  
        # EFS volume ID's are determined by looking up the name, and are thus not required
        # you can supply as many names as you like here, but (10/2017) AWS will by default
        # limit you to 10 EFS mounts on one instance, unless you request an increase
        #
        # Volume name can have spaces in it, but don't put it in qoutes. Spaces around comma ok

    EFS_VOLUME_NAME_LIST=(  "Test Volume1 EFS,  /efs/test_vol1" \
                            "Test Volume2 EFS,  /efs/test_vol2" \
                            "Test Volume3 EFS,  /efs/test_vol3" \
                         )

        # these are parameters used in the 'mount' command for the above EFS volumes
        # see 'man nfs' for details. These are the most common parameters, you can
        # add additonal ones by modifying the script. 

    EFS_TYPE="nfs4 nfsvers=4.1"
    EFS_RSIZE="rsize=1048576"
    EFS_WSIZE="wsize=1048576"
    EFS_TIMEO="timeo=600"
    EFS_RETRANS="retrans=2"
    EFS_HARD="hard"

        # script runtime/state save parameters
        #
        # A couple of variables used by the code, and "aws_last" to know what
        # to do when the exit our ssh shell into the instance. 
        # note this is only true when in the session that started the shell,
        # but demonstrate using the aws InstanceID to minipulate the image.
        
    STOP_ON_SSH_EXIT="ask"                     # "yes, no or ask"
    TERMINATE_ON_SSH_EXIT="no"                 # "yes, no or ask"

        # where to save our 'state' file, used by aws_connect script to
        # restart a  instance that may have been stopped
        # Values must be same in aws_connect script

    OPT_DIR=/tmp/awsami                        # directory to hold persistent files
    OPT_FILE=$OPT_DIR/state                    # name of file
    OPT_CFG_FILE=""                            # default config file. "" for none

        # some know AWS limits that are checked for in the script

    IOPT_MAX_RATIO=50                          # IOPTs value = DiskSizeG * Ratio
    IOPT_MIN_VALUE=25                          # lower limit, I made this up
    IOPT_MAX_VALUE=20000                       # upper limit, saw in spec

###############################################################################
# Helpful scripts

# check_prerequisites 
#
# Verifies that necessary prerequisites features are avalable on the machine
# In this case, aws of the proper version and the jq utility to parse JSON
#
check_prerequisites() {
    ERROR=0
    AWS_V1=1		# required aws version number
    AWS_V2=11
    AWS_V3=164

       # quick check user forgot to set options 

    if [ "$REGION" == "<WHERE YOU WILL RUN YOUR INSTANCE>" ]; then
        echo "ERROR: this script's placeholder parameters need to be set, or provide a config file"
        exit 1
    fi

       # check that aws is installed, and it's version

    command -v "aws" > /dev/null
    if [ $? -ne 0 ]; then
        ERROR=1 
        echo "ERROR: missing application \"aws\" require to interface with AWS cloud. Please download" >&2
    else  
            # aws --version
            # aws-cli/1.11.164 Python/3.5.2 Linux/4.4.0-93-generic botocore/1.7.22
            # .164 provides ways to update tag fields, required

        VERINFO=$( aws --version 2>&1 )    # get both stdout and stderr, different version do differntly
        VER=$(echo $VERINFO | cut -d' ' -f 1 | cut -d'/' -f 2)     # just the 1.11.164
        V1=$(echo $VER | cut -d'.' -f 1)
        V2=$(echo $VER | cut -d'.' -f 2)
        V3=$(echo $VER | cut -d'.' -f 3)
        if [ $V1 -lt $AWS_V1 ] || [ $V2 -lt $AWS_V2 ] || [ $V3 -lt $AWS_V3 ]; then
            ERROR=1
            echo "ERROR: installed \"aws\" version is $VER, need at least $AWS_V1.$AWS_V2.$AWS_V3. Please upgrade" >&2
        fi   
    fi

        # aws output config format needs to be "json", can "text" or "table". If set wrong
        # all the expected json format output here won't work. Default if not set is "json"
        # see: From http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html

    AWS_CFG_FILENAME=~/.aws/config        # no qoutes, ~ won't be expanded from "~/.aws/.." 
    if [ -e "$AWS_CFG_FILENAME" ]; then

             # expecting a line like "output = json"

        OUTPUT_MODE=$(cat "$AWS_CFG_FILENAME" | grep "output" | cut -d'=' -f 2 | sed 's/ *//g')
        if [ "$OUTPUT_MODE" != "json" ] && [ "$OUTPUT_MODE" != "" ]; then
            echo "ERROR: aws output mode is must be \"json\" for this script to work. run \"aws configure\" to set"
            ERROR=1
        fi
    fi

        # verify that .pem key specified in cfg files exist

    if ! [ -e "$KEY_FILE" ]; then
        echo "ERROR: did not find key file \"$KEY_FILE\""
        ERROR=1
    fi

        # check for jq json parsing application

    command -v "jq" > /dev/null
    if [ $? -ne 0 ]; then
        ERROR=1

        echo "ERROR: missing application \"jq\", used to parse JSON output. Please download" >&2
    fi

        # silent errors if io1 EBS disk and IOPTS_RATIO > 50  (as of 2017)
        # so warn if exceed

    IOPS_RATIO_MAX=50        # as of 2017
    if [ $EBS_BOOT_VOLIOPS_RATIO -gt $IOPS_RATIO_MAX ] || [ $EBS_BOOT_VOLIOPS_RATIO -gt $IOPS_RATIO_MAX ]; then
        ERROR=1
        echo "ERROR: EBS VOLIOPS_RATIOs must be <= $IOPS_RATIO_MAX - not BOOT:$EBS_BOOT_VOLIOPS_RATIO DATA:$EBS_BOOT_VOLIOPS_RATIO"
    fi    

        # and errors? if so, exit 
 
    if [ $ERROR != 0 ]; then
        exit 1                # WARNING: don't put $(check_prerequisites) in subshell, exits don't work
    fi
}
# usage
#
# Prints usage message
#
usage() {
   echo "aws_create_instance:  Creates aws instance, optionally mounts EFS or EBS volumes"
   echo ""
   echo "usage:"
   echo "   [options] [config-file]"
   echo ""
   echo "Options:"
   echo "    -h, help               prints this help message"
   echo ""
   exit 1
}
# parse_args
#
# pulls in command line args and parses them into variables
# calls usage if any problem is found and exits
#
parse_args() {
    while [ "$1" != "" ]; do
        case "$1" in
            "help" )
                usage
                ;;
            "-h" )
                usage
                ;;
            *)
                OPT_CFG_FILE="$1"
                ;;
        esac
        shift          # next arg
    done
}
# ask (returnval, question, prompt, default, [timeout])
#
# case insensitive y/n or yes/no question prompter
# args: 1:returnval 2:question 3:y/n prompt string, 4:default return. 5:optional timeout in secs
#
# returns: "yes" or "no"
# usage: ask answer "Do you like cupcakes?" "(y/N) : " "yes"   # no timeout
ask() {
    local __result=$1
    echo -n "$2" " "            # -n is a bash extension not to write newline, not in sh
    if [ -z $5 ]; then          # prompt and read users response, no timeout
        read -p "$3" CONFIRM;
    else                        # $4 is the timeout in sections or fractions
        read -t $5 -p "$3" CONFIRM;
        ret=$?
        if [ $ret -gt 0 ]; then
            echo "timeout"      # send newline if timeout
            ANSWER=$4           # default
        fi
    fi
    shopt -u nocasematch        # restore back to default casematch
    case "$CONFIRM" in          # case insensitive matching, different froms of yes and no
        "y"   ) ANSWER="yes" ;;
        "yes" ) ANSWER="yes" ;;
        "n"   ) ANSWER="no" ;;
        "no"  ) ANSWER="no" ;;
        *     ) ANSWER=$4 ;;    # default answer, should be "yes" or "no"
    esac
    shopt -u nocasematch        # restore back to default casematch
    eval $__result=$ANSWER      # pass back answer - "yes" or "no"
}

# SaveRunningInstanceId
#
# Just saves the id to a file, used by anoter script to restart/bring it up
#
SaveRunningInstanceId() {
    local ID="$1"             # instance ID 
    local NAME="$2"           # name of the instance
    local STOP="$3"           # stop instance on exit ssh
    local TERMINATE="$4"      # terminate instance on exit ssh
    local KEY="$5"            # full path to ssh pem key
    local LOGIN="$6"          # login account name like "ubuntu"
    local SGRP_ID="$7"        # security group id
    local SGRP_NAME="$8"      # name of security group, info
    local SGRP_DEL="$9"       # 'true' to delete security group if terminate

        # make sure directory exists

    mkdir -p $OPT_DIR               

        # save necesary values

    echo "# $(date)"                                        > $OPT_FILE
    echo "INSTANCE_ID=$ID"                                 >> $OPT_FILE
    echo "NAME_TAG_INSTANCE=\"$NAME\""                     >> $OPT_FILE
    echo "STOP_ON_SSH_EXIT=$STOP"                          >> $OPT_FILE
    echo "TERMINATE_ON_SSH_EXIT=$TERMINATE"                >> $OPT_FILE
    echo "KEY_FILE=\"$KEY\""                               >> $OPT_FILE
    echo "LOGIN_NAME=$LOGIN"                               >> $OPT_FILE
    echo "SSH_SECURITY_GROUP_NAME=\"$SGRP_NAME\""          >> $OPT_FILE
    echo "SSH_SECURITY_GROUP_CREATED_ID=$SGRP_ID"          >> $OPT_FILE  # empty if not created
    echo "SECURITY_GROUP_DELETE_IF_CREATED=$SGRP_DEL"      >> $OPT_FILE  # empty if not created

         # record any optional config file if one was specified

    if [ "$OPT_CFG_FILE" != "" ]; then
        echo "OPT_CFG_FILE=\"$OPT_CFG_FILE\""	>> $OPT_FILE
    fi
}

# AddSecurityRule
#
# Add the ingress or egress rules -- at the time I'm writing this they look like
# they have the same interface.. 
#
# the input  an array that has multiple lines,  each containing comma seperated 
# values that look like. List can be empty, in which nothing is added
#
#           protocol,to,from,cidrip,description
#
# parse values out of each line, then add each security rule to our security group
# 
# (couldn't find easy way to pass array of space-containing strings.. do each line one at a time)
AddSecurityRule() {
    DIRECTION=$1
    GROUP_ID=$2
    RULE=$3

#   echo "AddSecurityRule $1 $2 \"$3\""

    if [ "$RULE" == "" ]; then
        return 0                   # empty item
    fi

        # parse the string to pull out each comma seperated value from it
        # strip any spaces around token, or starting spaces for description
        # allows the table defining these values to look pretty.

    IP_PROTOCOL=$(echo $RULE | cut -d',' -f 1 | sed 's/ //g' )  # before 1st comma, remove any spaces
    FROM_PORT=$(echo $RULE | cut -d',' -f 2 | sed 's/ //g' )
    TO_PORT=$(echo $RULE | cut -d',' -f 3 | sed 's/ //g' )
    CIDR_IP=$(echo $RULE | cut -d',' -f 4 | sed 's/ //g' )
    DESCRIPTION=$(echo $RULE | cut -d',' -f 5 | sed 's/^ *//g' ) # description, remove leading spaces
    IP_PERMISSION="[{\"IpProtocol\":\"$IP_PROTOCOL\", \"FromPort\":$FROM_PORT, \"ToPort\":$TO_PORT,
                       \"IpRanges\": [{\"CidrIp\":\"$CIDR_IP\", \"Description\":\"$DESCRIPTION\"}] \
                   }]"

#    echo $IP_PERMISSION | jq .      # nice way to debug the line

    case "$DIRECTION" in
        "ingress" )
            CMD="authorize-security-group-ingress"
            ;;
        "egress" )
            CMD="authorize-security-group-egress"
            ;;
        * )
            echo "ERROR: unknown Security Rule cmd \"$DIRECTION\""
            exit 1
            ;;
    esac

        # create the single security group rule 

    aws ec2 $CMD --group-id $GROUP_ID --ip-permissions "$IP_PERMISSION"
    return $?
}
# CreateSecurityGroup
#
# Creates a security group along with a description, and adds a Name tag to it
# The group is initally created with no rules.
#
CreateSecurityGroup() {
    local VPC_ID=$1
    local NAME=$2
    local DESCP=$3
    local TAG_NAME=$4

    local RC GROUP_JSON GROUP_ID
    local VPC_JSON=$(aws ec2 describe-vpcs --region $REGION)
    local VPC_ID=$(echo $VPC_JSON | jq .Vpcs[0].VpcId | sed 's/\"//g')

        # generate a new security group

    local GROUP_JSON=$(aws ec2 create-security-group  \
                               --group-name "$NAME" \
                               --description "$DESCP" \
                               --vpc-id $VPC_ID)
    RC=$?
    GROUP_ID=$(echo $GROUP_JSON | jq .GroupId | sed 's/\"//g')
    if [ $RC != 0 ] || [ "GROUP_ID" == "" ] || [ "$GROUP_ID" == "null" ]; then
        echo "ERROR: could not create SSH Security Group \"$NAME\"" >&2
        exit 1       # if call in subshell  V=$(CreateSecrityGroup params), will not exit out of full script
    fi

        # add name tag to group

    aws ec2 create-tags --resource $GROUP_ID --tags Key=Name,Value="$TAG_NAME"
    echo $GROUP_ID   # pass back group id
    return 0
}
###############################################################################
# MAIN: command line argument parsing
#
# Simple for now, if argument is provided, it's expected to be a
# configuration file that is sourced to override any of the above values

    parse_args $@
    if [ "$OPT_CFG_FILE" != "" ]; then
        if ! [ -e "$OPT_CFG_FILE" ]; then
            echo "ERROR: cannot find config file \"$OPT_CFG_FILE\"" >&2
            exit 1
        fi
        source $OPT_CFG_FILE     # update parameters with user defined value
        if [ $? -ne 0 ]; then    # errors?
           exit $?
        fi
    fi

        # this test also verifies some input parameters... do after source

    check_prerequisites          # proper tools installed on machine

###############################################################################
# All the parameters are specified... 

###############################################################################
# From here on, this does the following
# 
# 1) Verify that the EFS mount volumes are correct
# 2) From it's name, Find the ID of the AMI instance that will be loaded
# 3) From it's name, find the ID of the Security Group assocated with the instance 
# 4) Create the instance, and it's boot volume and start it running
# 5) Wait for the instance to enter the 'running' state
# 6) Name the boot volume, by default this wasn't given a name 
# 7) Get the full public IP address of instance so can ssh into it
# 8) IF optional EBS volume is to be created, do it here
# 9) Try pinging the instance till it responds. (linux network is up)
# 10) Wait till we can ssh into the instance. Can take time if large # gpus/memory
# 11) If optional EBS volume is created, initialize and mount it within the instance
# 12) Mount any EFS volumes that were requested
# 13) ssh into instance, and show the command line to do so
# 14) Determine what to do once the shell exits -- stop, terminate and if to prompt
###############################################################################


# 1) Verify that the EFS mount volumes are correct
#
# If EFS volumes are to be mounted, the this section is called before the instance
# is created to verify that those volumes exist. Note that they are specifed by more
# human readable name, not the EFS volume id.
#
# Multiple Volumes can be specified to be mounted here in the EFS_VOLUME_NAME_LIST
# It's format is <AWS EFS Volume Name>,<mount point> [...].
# 
# Note that all volumes must be found, and there EFS ID's determined before the 
# instance is allowed to be created. That EFS ID is used in the /etc/fstab that 
# will be written to the instance after it come up

    if [ "$MOUNT_EFS_VOLUME" == "true" ]; then
        echo "# Finding EBS volumes to be mounted"

            # note the ..NAME_LIST is an array since it contains space-carrying strings
            # can use simple appended list with FileSystem ID's we are collecting, 

        ERROR=0
        for EFS_NAME_AND_MOUNT in "${EFS_VOLUME_NAME_LIST[@]}"; do            # allow spaces both sides ','
            EFS_VOLUME_NAME=$(echo $EFS_NAME_AND_MOUNT | sed 's/ *,.*//')     # EFS Name is before the ','
            EFS_MOUNT_POINT=$(echo $EFS_NAME_AND_MOUNT | sed 's/.*, *//')     # MountPoint is after the ','

            FILE_SYS_JSON=$(aws efs describe-file-systems)    # no '--filters' by name on this cmd
            IDX=0
            while [ 1 ]; do
                EFS_FILESYS_ID=$(echo $FILE_SYS_JSON | jq .FileSystems[$IDX].FileSystemId | sed 's/\"//g' )

                    # the "Name" field picked up below is and optional tag that the user's may not 
                    # fill in -- can't use it for "end of list" -- use FileSystemId instead

                if [ "$EFS_FILESYS_ID" == "null" ]; then       # end of list
                    break;
                fi
             
                    # The "Name" is what we are really interested in

                FOUND_NAME=$(echo $FILE_SYS_JSON | jq .FileSystems[$IDX].Name | sed 's/\"//g' )
                if [ "$FOUND_NAME" == "$EFS_VOLUME_NAME" ]; then
                    break;
                fi
                IDX=$((IDX+1))                  # didn't find, try the next one
            done
            if [ "$EFS_FILESYS_ID" == "" ]; then
                echo "Could not find EFS volume by name of \"$EFS_VOLUME_NAME\"" >&2
                ERROR=1
            else      # append found id to list
                EFS_ID_AND_MOUNT="$EFS_FILESYS_ID,$EFS_MOUNT_POINT"  # should have no internal spaces
                EFS_FILESYS_ID_MOUNT_LIST="$EFS_FILESYS_ID_MOUNT_LIST $EFS_ID_AND_MOUNT"
                echo "  $EFS_FILESYS_ID \"$EFS_VOLUME_NAME\""
            fi
        done
        if [ $ERROR -ne 0 ]; then
            echo "Error: could not find all specified EFS file systems, aborting" >&2
            exit 1
        fi
    fi

# 2) From it's name, Find the ID of the AMI instance that will be loaded
#
# Get the image ID of the “NVIDIA Volta(TM) Deep Learning AMI” that we created.
# Note that currently (10/2017) the ID of this image changes whenever we update 
# the image. This query here does a name-to-id lookup. The name should remain constant. 

    if [ "$OWNER_ID" == "" ]; then
       OWNER_OPT=""                      # full name must be used if don't supply OWNER_ID
    else
       OWNER_OPT="--owners $OWNER_ID"    # supplying OWNER_ID slows search way down
    fi

    IMAGE_JSON=$(aws ec2 describe-images $OWNER_OPT --filters "Name=name,Values=\"$IMAGE_NAME\"")
    IMAGE_ID=$(echo $IMAGE_JSON | jq .Images[0].ImageId | sed 's/\"//g')                  # no quotes

         # interesting type of error here -- is if the name given to packer has
         # two spaces "  ", then the echo commands that are used by the script
         # will convert it to 1 space, and it won't be found by it's published
         # name. Moral of the story, don't have two spaces "  " in the name anywhere"

    if [ "$IMAGE_ID" == "null" ]; then
        echo "ERROR: could not find AMI by \"$IMAGE_NAME\""
        exit 1
    fi
    echo "IMAGE_ID=$IMAGE_ID     # \"$IMAGE_NAME\""      # ami-8ee326f6

# 3) From it's name, find the ID of the Security Group assocated with the instance 
#
# If we can't find the group by the given name, then one will be created. Idea here is
# to avoid re-creating the saem rules over and over. That means that the security
# rules should not have timestamps as part of their name. Note that there is
# a flag SECURITY_GROUP_DELETE_IF_CREATED that will be checked on terminate
# if we actually create the security group here
#
# See http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

    SSH_SECURITY_JSON=$(aws ec2 describe-security-groups --group-name "$SSH_SECURITY_GROUP_NAME" 2> /dev/null)
    RC=$?
    SSH_SECURITY_GROUP_ID=$(echo $SSH_SECURITY_JSON | jq .SecurityGroups[0].GroupId |  sed 's/\"//g')

         # If the security group doesn't exist, then it will be created if NEEDED flag is set

    if [ $RC != 0 ] || [ "$SSH_SECURITY_GROUP_ID" == "" ] || [ "$SSH_SECURITY_GROUP_ID" == "null" ]; then
        if [ "$SECURITY_GROUP_CREATE_IF_NEEDED" != "true" ]; then
            echo "ERROR: could not find SSH Security Group \"$SSH_SECURITY_GROUP_NAME\""  >&2
            exit 1
        fi
        GROUP_ID=$(CreateSecurityGroup "$VPC_ID" \
                                       "$SSH_SECURITY_GROUP_NAME"  \
                                       "$SSH_SECURITY_GROUP_DESCP" \
                                       "$SSH_SECURITY_GROUP_NAME_TAG" )
        RC=$?
        if [ $RC -ne 0 ] || [ "$GROUP_ID" == "" ]; then 
            exit "ERROR: Unable to create security group \"SSH_SECURITY_GROUP_NAME\""
            exit 1
        fi

            # set the global variables for what we just did

        SSH_SECURITY_GROUP_CREATED_ID=$GROUP_ID  # this is one we will delete, if asked to
        SSH_SECURITY_GROUP_ID=$GROUP_ID          # one used to create - won't override prior
        echo "SSH_SECURITY_GROUP_ID=$SSH_SECURITY_GROUP_ID  # created"

            # add the ingress and egress rules, one at a time. passing arrays was not working.

        for RULE in "${SSH_SECURITY_INGRESS_RULES[@]}"; do
            AddSecurityRule "ingress" $GROUP_ID "$RULE"
        done
        for RULE in "${SSH_SECURITY_EGRESS_RULES[@]}"; do
            AddSecurityRule "egress" $GROUP_ID "$RULE"
        done

            # re-grab the description after adding rules, in case we use it later

        SSH_SECURITY_JSON=$(aws ec2 describe-security-groups --group-ids $SSH_SECURITY_GROUP_CREATED_ID)
    else
        echo "SSH_SECURITY_GROUP_ID=$SSH_SECURITY_GROUP_ID  # prexisting"
    fi

    echo "SSH_SECURITY_GROUP_NAME=\"$SSH_SECURITY_GROUP_NAME\""

    # echo $SSH_SECURITY_JSON | jq .   # verbose print the structure

# 4) Create the instance, and it's boot volume and start it running
#
# Launch P3 instance with NGC AMI, creating a boot volume of $BOOT_VOLSIZE
# VolumeName /dev/sda1 maps inside running instance as /dev/xvda 

        # Create a mini-json string that defines type of the boot device.
        # The cheap/default version is 'gp2', but a considerablly faster version
        # is 'io1'. Note that if use 'io1', then IOPS must also be defined
        # The size of the boot device in G is another paramter specified here

    NAME_VAL="\"DeviceName\":\"/dev/sda1\""
    if [ "$EBS_BOOT_VOLTYPE" == "gp2" ]; then
        EBS_VAL="\"Ebs\":{\"VolumeType\":\"$EBS_BOOT_VOLTYPE\",\"VolumeSize\":$EBS_BOOT_VOLSIZE}"
    else   # max IOPS is (sizeG * 50) as of 2017 -- specify ratio, do math here to get IOPS value
        IOPS=$(($EBS_BOOT_VOLIOPS_RATIO * $EBS_BOOT_VOLSIZE))
        if [ $IOPS -lt $IOPT_MIN_VALUE ]; then IOPS=$IOPT_MIN_VALUE; fi     # min check
        if [ $IOPS -gt $IOPT_MAX_VALUE ]; then IOPS=$IOPT_MAX_VALUE; fi    # max check
        EBS_VAL="\"Ebs\":{\"VolumeType\":\"$EBS_BOOT_VOLTYPE\",\"VolumeSize\":$EBS_BOOT_VOLSIZE,\"Iops\":$IOPS}"
    fi 

        # this creates the instance on the block device of type specified.

    INSTANCE_JSON1=$(aws ec2 run-instances \
                     --image-id $IMAGE_ID \
                     --instance-type $INSTANCE_TYPE \
                     --region $REGION  \
                     --key-name $KEY_NAME \
                     --security-group-ids $SSH_SECURITY_GROUP_ID \
                     --block-device-mapping "[{"$NAME_VAL","$EBS_VAL"}]")

        # Attempt to pull the InstanceID out of the json string that was 
        # returned. Note the network information to talk to the instance
        # is not ready yet. -- will poll for it becomming ready in a bit

    INSTANCE_ID=$(echo $INSTANCE_JSON1 | jq .Instances[0].InstanceId | sed 's/\"//g')       # no quotes
    if [ "$INSTANCE_ID" == "null" ] || [ "$INSTANCE_ID" == "" ]; then
        echo "ERROR: unable to create a InstanceID from this ImageID $IMAGE_ID"
        exit 1
    fi
    echo INSTANCE_TYPE=$INSTANCE_TYPE
    echo INSTANCE_ID=$INSTANCE_ID                            # i-005265962297ada85

        # Name your instance! . Done here instead of in run-instances call 
        # so that env variables could be used (it's tricky in bash to get space/qoutes right)

    NAME_TAG_INSTANCE="$NAME_TAG instance"
    echo NAME_TAG_INSTANCE=\"$NAME_TAG_INSTANCE\"
    aws ec2 create-tags --resource $INSTANCE_ID --tags Key=Name,Value="$NAME_TAG_INSTANCE"

        # Saves id/name to file, so can refer to them later in 'ats_last' app. 
        # Everything to connect to a stoped instance, or terminate it full is
        # held within this file, as are the what-to-to if stopped/terminated

    SaveRunningInstanceId "$INSTANCE_ID" "$NAME_TAG_INSTANCE" "$STOP_ON_SSH_EXIT" \
                          "$TERMINATE_ON_SSH_EXIT" "$KEY_FILE" "$LOGIN_NAME" \
                          "$SSH_SECURITY_GROUP_CREATED_ID" "$SSH_SECURITY_GROUP_NAME" \
                          "$SECURITY_GROUP_DELETE_IF_CREATED"

# 5) Wait for the instance to enter the 'running' state
#
# The instance doesn't enter a "running" state till its fully created and 
# launched. At this point uboot begins running, and as far as AWS is concerned
# it is now "running". At this point we can get it's Public IP address
# and the ID of it's boot volume. Need both of them for the next steps

    MAX_ATTEMPTS=40
    for (( ATTEMPT=0; ATTEMPT<$MAX_ATTEMPTS; ATTEMPT++)); do 
        DESCRIBE_INSTANCE_STATUS_JSON=$(aws ec2 describe-instance-status --instance-id $INSTANCE_ID)
        STATE=$(echo $DESCRIBE_INSTANCE_STATUS_JSON | jq .InstanceStatuses[0].InstanceState.Name | sed 's/\"//g')
        if [ "$STATE" == "running" ]; then
            break;
        fi
        echo -ne "$ATTEMPT $INSTANCE_ID $STATE\r"
        sleep 1
    done
    if [ "$STATE" != "running" ]; then
        echo "Timeout, did not enter \"running\" state       " >&2
        exit 1
    fi

    INSTANCE_JSON2=$(aws ec2 describe-instances --instance-id $INSTANCE_ID)

# 6) Name the boot volume, by default this wasn't given a name 
#
# Note that the Boot volume ID is not available at initial create
# Needed to wait till instance was in running state to do this

    BOOT_VOLUME_ID=$(echo $INSTANCE_JSON2 | \
                           jq .Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId | sed 's/\"//g' )
    echo BOOT_VOLUME_ID=$BOOT_VOLUME_ID              # vol-0f090e771e0f7ab26

    NAME_TAG_BOOT_VOL="$NAME_TAG boot volume"
    echo NAME_TAG_BOOT_VOL=\"$NAME_TAG_BOOT_VOL\"
    aws ec2 create-tags --resource $BOOT_VOLUME_ID  --tags Key=Name,Value="$NAME_TAG_BOOT_VOL"

# 7) Get the full public IP address of instance so can ssh into it
#
# Grabing the full long dns name from thei instance data itself
# Again, we needed to wait till instance was in 'running' state to get this

    PUBLIC_ID=$(echo $INSTANCE_JSON2 | jq '.Reservations[0].Instances[0].PublicDnsName' | sed 's/\"//g' )
    echo PUBLIC_ID=$PUBLIC_ID                        # ec2-35-164-247-54.us-west-2.compute.amazonaws.com

# 8) IF optional EBS volume is to be created, do it here
#
# Most of the following steps are only needed if we are going to create a
# private EBS data volume and attach it to the new instance that we just 
# created above
#
# NOTE: the 'DeleteOnTermination' flag is set on this created volume so that
#       it is automatically destroyed when the VM instance is terminated

    if [ "$CREATE_PRIVATE_EBS_VOLUME" == "true" ]; then

    # actual zone where the instance was built. We need to create volume in same location

        AVAIL_ZONE=$(echo $INSTANCE_JSON2 | jq  '.Reservations[0].Instances[0].Placement.AvailabilityZone' | sed 's/\"//g' )
        echo AVAIL_ZONE=$AVAIL_ZONE                      #"us-west-2a"

    # To Create EBS Volume of size $EBS_DATA_VOLSIZE and mount it. Don’t use --iops flags if no value specified

        if [ "$EBS_DATA_VOLTYPE" ==  "gp2" ]; then 
            IOP_OPT=""; 
        else               # max ratio 2017 was 50, so for 10G disk, max IOPS=500
            IOPS=$(($EBS_DATA_VOLIOPS_RATIO * $EBS_DATA_VOLSIZE))
            if [ $IOPS -lt $IOPT_MIN_VALUE ]; then IOPS=$IOPT_MIN_VALUE; fi    # min check
            if [ $IOPS -gt $IOPT_MAX_VALUE ]; then IOPS=$IOPT_MAX_VALUE; fi    # max check
            IOP_OPT="--iops $IOPS"
        fi

        EBS_VOLUME_JSON=$(aws ec2 create-volume --size $EBS_DATA_VOLSIZE \
                                                --region $REGION \
                                                --availability-zone $AVAIL_ZONE \
                                                --volume-type $EBS_DATA_VOLTYPE $IOP_OPT)
        EBS_VOLUME_ID=$(echo $EBS_VOLUME_JSON | jq .VolumeId |  sed 's/\"//g')
        echo EBS_VOLUME_ID=$EBS_VOLUME_ID     # vol-0c84295eb6d7076a1

    # Give the volume a Name tag so you can find it - note same way as we do with instance

        NAME_TAG_EBS_DATA_VOL="$NAME_TAG data volume"
        echo NAME_TAG_EBS_DATA_VOL=\"$NAME_TAG_EBS_DATA_VOL\"
        aws ec2 create-tags --resource $EBS_VOLUME_ID --tags Key=Name,Value="$NAME_TAG_EBS_DATA_VOL"

    # attach the new volume to the instance. Volume must be destroyed independent of instance
    # /dev/sdb reports “already in use” during mount, so use xvdb.  Rem: boot vol is seen as /dev/xvd

         EBS_VOLUME_NAME="/dev/xvdb"
         sleep 3              # need time for volume to be created 
         ATTACH_JSON=$(aws ec2 attach-volume --volume-id $EBS_VOLUME_ID --instance-id $INSTANCE_ID --device /dev/xvdb)

    # By default, these non-root EBS volumes do not have there 'delete-on-termination' 
    # flags set, so they are not automagicly removed when the instance terminates.
    # Lets be consistent here and do that.

         aws ec2 modify-instance-attribute --instance-id $INSTANCE_ID \
                --block-device-mappings "[{\"DeviceName\": \"/dev/xvdb\",\"Ebs\":{\"DeleteOnTermination\":true}}]" 
       
    fi

# 9) Try pinging the instance till it responds. (linux network is up)
#
# It's going to take up to 5 minutes or so to allow the instance to finish 
# booting till we can ssh into it. -- first step, wait till we can ping 
# (meaning that the network portion of the kernel is up and reponding)
# NOTICE: The SecurityGroup we used  must enable Pings for this to work!

    MAX_ATTEMPTS=300
    for (( ATTEMPT=0; ATTEMPT<$MAX_ATTEMPTS; ATTEMPT++)); do
        ping -c 1 -W 1 $PUBLIC_ID &> /dev/null
        if [ $? -eq 0 ]; then
            break;                # we can ping
        fi
        echo -ne "$ATTEMPT ping $PUBLIC_ID    \r"
        sleep 1
    done
    if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
        echo "Timeout waiting for SSH to $PUBLIC_ID"
        exit 1
    fi

# 10) Wait till we can ssh into the instance. Can take time if large # gpus/memory
#
# Next step is to wait till we can SSH into the instance. If this is first
# boot of a NVIDIA GPU instance, it may take a bit more time for it to go
# from being ping-able to when it can ssh, due to the fact that the drivers
# have to be linked and loaded that first boot time.
# send output of ssh uptime to dev/null -- its initally telling us that ssh 
# is failing. Ignore that, want a 0 return to indicate that ssh succeeded

    for (( ATTEMPT=0; ATTEMPT<$MAX_ATTEMPTS; ATTEMPT++)); do
        STR=$(ssh -oStrictHostKeyChecking=no -i $KEY_FILE $LOGIN_NAME@$PUBLIC_ID "uptime" 2> /dev/null )
        RC=$?
        if [ $RC == 0 ]; then    # no error
            break
        fi
        echo -ne "$ATTEMPT ssh $PUBLIC_ID    \r"
        sleep 1
    done
    if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
        echo "Timeout waiting for SSH to $PUBLIC_ID"
        exit 1
    fi

# 11) If optional EBS volume is created, initialize and mount it within the instance
# 
# If we attached a EBS volume to the instance, we need to format it, and then
# mount it

     if [ "$CREATE_PRIVATE_EBS_VOLUME" == "true" ]; then
         CMD="lsblk;       
              sleep 2;
              sudo mkfs -t ext4 /dev/xvdb; 
              sudo mkdir /datavol; 
              sudo mount /dev/xvdb /datavol; 
              df -h;
              echo \"\""
          ssh -i $KEY_PATH/$KEY_NAME.pem $LOGIN_NAME@$PUBLIC_ID $CMD

         # NOTE: AWS puts an entry in /etc/fstab that mounts this volume on /mnt
         # we don't appear to need to setup fstab ourselfs -- fstab entry looks like:
         #
         # /dev/xvdb /mnt auto defaults,nofail,x-systemd.requires=cloud-init.service,comment=cloudconfig 0 2
         #
      fi

# 12) Mount any EFS volumes that were requested
#
# This section mounts any EFS volumes that may have been requested. Note that 
# multiple volumes can be mounted here. Updates the /etc/fstab file, then calls
# 'mount -a' to actually perform the mount. See EFS_VOLUME_NAME_LIST above

    if [ "$MOUNT_EFS_VOLUME" == "true" ]; then

             # go through list if EFS ids that were picked up before creating the instance

        if [ "$EFS_FILESYS_ID_MOUNT_LIST" != "" ]; then         # anything in the list?
            TMP_FILE="/tmp/efs_setup"
            FSTAB_FILE="/etc/fstab"

            echo "# generated script to setup AWS EFS mounts on instance"    > $TMP_FILE

                # One minor little problem.. the standard ubuntu 16.04 server image that
                # we are loading with this simple test version doesn't have the nfs
                # utilities loaded -- we need load that package here manually
                # The NVIDIA AMI's have this preloaded... this is a special case only 
                # for this test mode

            if [ "$INSTALL_NFS_COMMON" == "true" ]; then
                echo "echo nfs-common package was not installed for ubuntu image, do now" >> $TMP_FILE
                echo "sudo apt-get -q -y install nfs-common"                 >> $TMP_FILE 
                echo ""                                                      >> $TMP_FILE 
            fi
                # end of workaround -- not needed for NVIDIA AMI

            echo "sudo chmod 666 $FSTAB_FILE"                                >> $TMP_FILE # TODO: permisson problems, better way?
            echo "sudo echo \"\" >> $FSTAB_FILE"                             >> $TMP_FILE
            echo "sudo echo \"# nvidia efs setup: $(date)\" >> $FSTAB_FILE"  >> $TMP_FILE
            echo "sudo echo \"\" >> $FSTAB_FILE"                             >> $TMP_FILE
            echo ""                                                          >> $TMP_FILE

            for EFS_ID_AND_MOUNT in $EFS_FILESYS_ID_MOUNT_LIST; do
                EFS_FILESYS_ID=$(echo $EFS_ID_AND_MOUNT  | sed 's/,.*//')   # EFS ID is before the ','
                EFS_MOUNT_POINT=$(echo $EFS_ID_AND_MOUNT | sed 's/.*,//')   # MountPoint is after the ','

                EFS_MOUNT_VALUE=$EFS_FILESYS_ID.efs.$REGION.amazonaws.com

                    # format the line needs to be appended to the fstab file, for each EFS device

                FSTAB_LINE="$EFS_MOUNT_VALUE:/ $EFS_MOUNT_POINT $EFS_TYPE,$EFS_RSIZE,$EFS_WSIZE,$EFS_TIMEO,$EFS_RETRANS,$EFS_HARD,_netdev 0 0"
                    # these two lines need to be ssh'ed into the instance for each EFS being mounted
                    # confusing qouting going on if simply try to ssh, so create a small script file
                    # scp it over to instance and run it there..

                echo "sudo mkdir -p \"$EFS_MOUNT_POINT\""                  >> $TMP_FILE
                echo "sudo echo \"$FSTAB_LINE\" >> $FSTAB_FILE"            >> $TMP_FILE
                echo ""                                                    >> $TMP_FILE
            done
            echo "sudo chmod 644 $FSTAB_FILE"                              >> $TMP_FILE # TODO: see above 
            echo "sudo mount -a         # start up new mounts"             >> $TMP_FILE

               # copy over single file and execute it to update fstab and make dirs

            scp -q -i $KEY_FILE $TMP_FILE $LOGIN_NAME@$PUBLIC_ID:$TMP_FILE
            ssh -i $KEY_FILE $LOGIN_NAME@$PUBLIC_ID "source $TMP_FILE" # run here
            echo "# mounted EFS volumes"
        fi
    fi

# 13) ssh into instance
#
# now SSH into our brand new instance

    echo ""
    echo "Entering $NAME_TAG_INSTANCE"
    echo ""
    echo "ssh -i $KEY_FILE $LOGIN_NAME@$PUBLIC_ID"
    ssh -i $KEY_FILE $LOGIN_NAME@$PUBLIC_ID
    RC_SSH_EXIT=$?       # safe this for final exit

# 14) Determine what to do once the shell exits -- stop, terminate and if to prompt
#
# The STOP/TERMINATE flags may be "yes", "no" or "ask". If the resulting 
# state is "yes", then that action will done. Note that you can ask to
# "stop" and also "terminate" -- terminate is done after stop

    if [ "$TERMINATE_ON_SSH_EXIT" == "ask" ]; then
         ask TERMINATE_ON_SSH_EXIT "terminate           $INSTANCE_ID -- $NAME_TAG_INSTANCE ?" "(y/N) : " "no"
    fi
    if [ "$TERMINATE_ON_SSH_EXIT" != "yes" ]; then
        if [ "$STOP_ON_SSH_EXIT" == "ask" ]; then
             ask STOP_ON_SSH_EXIT   "stop                $INSTANCE_ID -- $NAME_TAG_INSTANCE ?" "(Y/n) : " "yes"
        fi
    else
        STOP_ON_SSH_EXIT=false       # don't need to stop if we are terminating 
    fi

        # perform the requested action

    if [ "$STOP_ON_SSH_EXIT" == "yes" ]; then
        printf "%-17s %21s -- %s\n" "stopping" "$INSTANCE_ID" "$NAME_TAG_INSTANCE"
        STOP_JSON=$(aws ec2 stop-instances --instance-ids  $INSTANCE_ID)
        STATE_TO_CHECK="stopped"
    fi
    if [ "$TERMINATE_ON_SSH_EXIT" == "yes" ]; then
        printf "%-17s %21s -- %s\n" "terminating" "$INSTANCE_ID" "$NAME_TAG_INSTANCE"
        TERMINATE_JSON=$(aws ec2 terminate-instances --instance-ids  $INSTANCE_ID)
        STATE_TO_CHECK="terminated"
    fi

        # spin waiting of instance to go to state

    if [ "$STATE_TO_CHECK" == "" ]; then 
        echo ""
        echo "To reconnect to \"$NAME_TAG_INSTANCE\""
        echo "    ssh -i $KEY_FILE $LOGIN_NAME@$PUBLIC_ID"
        echo ""
    else 
            # wait till instance goes into requested state 

        MAX_ATTEMPTS=200
        for (( ATTEMPT=0; ATTEMPT<$MAX_ATTEMPTS; ATTEMPT++)); do
            DESCRIBE_INSTANCE_JSON=$(aws ec2 describe-instances --instance-id $INSTANCE_ID)
            STATE=$(echo $DESCRIBE_INSTANCE_JSON | jq .Reservations[0].Instances[0].State.Name | sed 's/\"//g')
            if [ "$STATE" == "$STATE_TO_CHECK" ]; then
                break
            fi
            printf "%3d %-9s %21s -- %s\r" $ATTEMPT "$STATE" "$INSTANCE_ID" "$NAME_TAG_INSTANCE"
            sleep 1
        done
        if [ "$STATE" != "$STATE_TO_CHECK" ]; then
            echo "Timeout, did not enter \"$STATE_TO_CHECK\" state       " >&2
            exit 1
        fi
        printf "%-17s %21s -- %s\n" "$STATE_TO_CHECK" "$INSTANCE_ID" "$NAME_TAG_INSTANCE"

            # should the SSH security group be deleted after the instance was terminated?

        if [ "$TERMINATE_ON_SSH_EXIT" == "yes" ]; then
            if    [ "$SECURITY_GROUP_DELETE_IF_CREATED" == "true" ] \
               && [ "$SSH_SECURITY_GROUP_CREATED_ID" != ""  ]; then
                echo Deleting security group $SSH_SECURITY_GROUP_CREATED_ID \"$SSH_SECURITY_GROUP_NAME\"
                aws ec2 delete-security-group --group-id $SSH_SECURITY_GROUP_CREATED_ID
            fi
        fi

            # just as a note here, code that set up the 2nd EBS volume set it's 'DeleteOnTermination'
            # flag, so it's not necessary to explicidly remove it when instance is terminated

        echo ""
    fi
    exit $RC_SSH_EXIT               # what SSH exited with
