#!/bin/bash             
#
# aws_create_efs.sh                              10/23/2017 17:15:00
#
# Copyright (c) 2017, NVIDIA CORPORATION.  All rights reserved.
#
# Example code to show how to create a new EFS (Elastic File System)
# volume and mount it. 
#
# This script uses the the hardcoded defaults, or can take a config
# file containing the non-default parameters
#
# usage:
#
#    aws_create_efs.sh [config file]
#
#

        # region where you will run your instances
        # For example: "us-west-2" or "us-east-1"

    REGION="<WHERE YOU WILL RUN YOUR INSTANCE>"

        # this is the public name that the volume will be given.
        # you can search for this name, using "aws efs describe-file-systems"
        # to get the file-system id. 
        # For example: "$USER $(date +'%a %H:%M') Test"

    EFS_VOLUME_TAG_NAME="<THE NAME OF YOUR VOLUME>"

        # Name of pre-created security group for the Volume
        # This group must open port 2049 for NFS

    NFS_SECURITY_GROUP_NAME="<YOUR NFS ENABLED SECURITY GROUP NAME>"

        # Unique token used to know if to create new EFS volume, or not
        # Must be unique to create a new volume, or same to skip
        # For example: CREATION_TOKEN="$USER-$(date +%A%Y%m$d%I%m%S)"

    CREATION_TOKEN="<MY CREATION TOKEN STRING>"  

        # This is the disk perfomance mode
        # this can either be "generalPurpose" or "maxIO"

    PERFORMANCE_MODE="generalPurpose"

        # EFS mount settings - see 'man nfs' for details
        # these are used in the mount and /etc/fstab command strings
        # additional parameters could be defined if you change the script 
        # In this script, these are just recommendations that are printed out
        # in the example mount strings once the mount point was created. 

    EFS_TYPE="nfs4 nfsvers=4.1"
    EFS_RSIZE="rsize=1048576"
    EFS_WSIZE="wsize=1048576"
    EFS_TIMEO="timeo=600"
    EFS_RETRANS="retrans=2"
    EFS_HARD="hard"

       # Recommended mount point -- not as with the settings above, it's 
       # only printed out in the example strings at the end, not a real setting

    EFS_MOUNT_POINT="/efs/mount-point"


###############################################################################

# usage
#
# Prints usage message
#
usage() {
   echo "aws_create_efs:  Creates efs volume and assigns mount points to it"
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

# check_prerequisites 
#
# Verifies that necessary prerequisites features are avalable on the machine
# In this case, aws of the proper version and the jq utility to parse JSON
#
check_prerequisites() {
    ERROR=0
    AWS_V1=1            # required aws version number
    AWS_V2=11
    AWS_V3=164

       # quick check user forgot to set options 

    if [ "$REGION" == "<WHERE YOU WILL RUN YOUR INSTANCE>" ]; then
        echo "ERROR: this script's placehold parameters need to be set, or provide a config file"
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

        # check for jq json parsing application

    command -v "jq" > /dev/null
    if [ $? -ne 0 ]; then
        ERROR=1

        echo "ERROR: missing application \"jq\", used to parse JSON output. Please download" >&2
    fi

        # and errors? if so, exit 

    if [ $ERROR != 0 ]; then
        exit 1                # WARNING: don't put $(check_prerequisites) in subshell, exits don't work
    fi
}
###############################################################################
# MAIN: command line argument parsing
#
# argument is provided, it's expected to be a configuration file
# sourced to override any of the above values

    parse_args $@
    if [ "$OPT_CFG_FILE" != "" ]; then
        if ! [ -e "$OPT_CFG_FILE" ]; then
            echo "ERROR: cannot find config file \"$OPT_CFG_FILE\"" >&2
            exit 1
        fi
        source $OPT_CFG_FILE     # update parameters with user specified values
        if [ $? -ne 0 ]; then    # errors?
           exit $?
        fi
    fi

    check_prerequisites          # proper tools installed on the machine

# first get the VPC your AWS account is assigned to

    VPC_JSON=$(aws ec2 describe-vpcs --region $REGION)
    VPC_ID=$(echo $VPC_JSON | jq .Vpcs[0].VpcId | sed 's/\"//g')
    echo REGION=$REGION
    echo VPC_ID=$VPC_ID        # vpc-0db1206a

# Get Existing Security Group id -- this group must open port 2049 for NFS

    NFS_SECURITY_JSON=$(aws ec2 describe-security-groups --group-name "$NFS_SECURITY_GROUP_NAME" --region $REGION)
    RC=$?
    if [ $RC -ne 0 ]; then
        echo "ERROR: Security group \"$NFS_SECURITY_GROUP_NAME\" could not be found" >&2
        exit $RC
    fi
    NFS_SECURITY_GROUP_ID=$(echo $NFS_SECURITY_JSON | jq .SecurityGroups[0].GroupId |  sed 's/\"//g')  
    echo "NFS_SECURITY_GROUP_ID=$NFS_SECURITY_GROUP_ID  # \"$NFS_SECURITY_GROUP_NAME\"" # sg-a3d16fde
    
# Create an empty EFS file system in your current region. The EFS_CREATION_TOKEN
# is used by AWS to ensure idempotent creation - I.E. if you call it with the
# same TOKEN a second time, then you will get a FileSystemAlreadyExists error
#
# Use CREATION_TOKEN to either create new volumes each time, or make sure you
# only create one volume


    CREATE_FILESYS_JSON=$(aws efs create-file-system --creation-token $CREATION_TOKEN --region $REGION --performance-mode $PERFORMANCE_MODE)
    RC=$?
    if [ $RC -ne 0 ]; then
          echo "ERROR: create_file_system failed" >&2
          exit $RC
    fi
    EFS_FILESYS_ID=$(echo $CREATE_FILESYS_JSON | jq .FileSystemId | sed 's/\"//g')
    echo "EFS_FILESYS_ID=$EFS_FILESYS_ID    # \"$EFS_VOLUME_TAG_NAME\""           # fs-2d963884

# Tag the file system with something descriptive 

    aws efs create-tags --file-system-id $EFS_FILESYS_ID --region=$REGION --tags Key=Name,Value="$EFS_VOLUME_TAG_NAME"
    sleep 2                        # time to come out of 'create' state

# You will have multiple subnets in the region us-west-2a, 2b, 2c...
# Since you may not be able to specify exactly which subnet your runtime
# instances get added to, (and my want to spread them around) we
# will setup our EFS to conect to every subnet. So enumerate through them
#
# Example:
#
#      us-west-2b subnet-9acd01d3
#      us-west-2c subnet-9c4269c4
#      us-west-2a subnet-fc802a9b


    SUBNET_JSON=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" )
    IDX=0
    while [ 1 ]; do
        SUBNET=$(echo $SUBNET_JSON | jq .Subnets[$IDX])
        if [ "$SUBNET" == "null" ]; then
            break            # end of list of subnets
        fi
        SUBNET_ID=$(echo $SUBNET_JSON | jq .Subnets[$IDX].SubnetId | sed 's/\"//g')
        AVAIL_ZONE=$(echo $SUBNET_JSON | jq .Subnets[$IDX].AvailabilityZone | sed 's/\"//g')
        if [ "$SUBNET_ID" == "null" ]; then
           break          # end of list of subnets
        fi

        echo "# " $AVAIL_ZONE $SUBNET_ID

             # Mount EFS on each subnet in the region
         
        CREATE_MOUNT_TARGET_JSON=$(aws efs create-mount-target --file-system-id $EFS_FILESYS_ID \
                                                               --subnet-id $SUBNET_ID \
                                                               --security-groups $NFS_SECURITY_GROUP_ID \
                                                               --region $REGION)

             # check for error -- already created EFS but if error, can't mount it
             # decide if you want to abort and cleanup, or continue here. 

        RC=$?
        if [ $RC != 0 ]; then
            echo "ERROR: creating mount target for SubnetID:$SUBNET_ID $AVAIL_ZONE - Volume mounts may fail. Please check" >&2
        fi
        IDX=$(($IDX+1))
    done

# Spin till all the mount target are created

    DONE=0
    MAX_ATTEMPTS=150                                 # for polling waiting for AWS to respond
    echo "# Waiting for subnets to be mounted"
    for ((ATTEMPT=0; ATTEMPT<MAX_ATTEMPTS && DONE==0; ATTEMPT++)); do
        DESCRIBE_TARGETS_JSON=$(aws efs describe-mount-targets --file-system-id $EFS_FILESYS_ID --region $REGION)
        IDX=0
        DONE=1
        sleep 1
        echo -ne  "\r $ATTEMPT "
        while [ 1 ]; do 
            SUBNET_ID=$(echo $DESCRIBE_TARGETS_JSON | jq .MountTargets[$IDX].SubnetId | sed 's/\"//g') 
            if [ "$SUBNET_ID" == "null" ]; then
                break          # end of list of subnets
            fi
            SUBNET_AVAIL_ZONE_JSON=$(aws ec2 describe-subnets --subnet-id=$SUBNET_ID --region $REGION)
            AVAIL_ZONE=$(echo $SUBNET_AVAIL_ZONE_JSON | jq .Subnets[0].AvailabilityZone | sed 's/\"//g')
            LIFE_CYCLE_STATE=$(echo $DESCRIBE_TARGETS_JSON | jq .MountTargets[$IDX].LifeCycleState | sed 's/\"//g') 
            echo -n " $AVAIL_ZONE:$LIFE_CYCLE_STATE"
            if [ "$LIFE_CYCLE_STATE" != "available" ]; then
                DONE=0    # not done yet
            fi
            IDX=$(($IDX+1))
         done 
    done
    echo ""

# This is the full DNS name to the mount target
# these are parameters used in the 'mount' command for the above EFS volumes
# see 'man nfs' for details. These are the most common parameters, you can
# add additonal ones by modifying the script. 

    EFS_MOUNT_VALUE=$EFS_FILESYS_ID.efs.$REGION.amazonaws.com

    echo ""
    echo "# Successfully created efs mount $EFS_MOUNT_VALUE"
    echo "# To mount this in your AWS instance, run the following commands there"
    echo ""
    echo "    EFS_MOUNT_POINT=$EFS_MOUNT_POINT"
    echo "    EFS_MOUNT_VALUE=$EFS_MOUNT_VALUE"
    echo "    sudo mkdir -p \$EFS_MOUNT_POINT"
    echo "    sudo mount -t nfs4 -o nfsvers=4.1,$EFS_RSIZE,$EFS_WSIZE,$EFS_TIMEO,$EFS_RETRANS,$FS_HARD \$EFS_MOUNT_VALUE:/ \$EFS_MOUNT_POINT" 

    FSTAB_LINE="$EFS_MOUNT_VALUE:/ $EFS_MOUNT_POINT $EFS_TYPE,$EFS_RSIZE,$EFS_WSIZE,$EFS_TIMEO,$EFS_RETRANS,$EFS_HARD,_netdev 0 0"

    echo ""
    echo "# Example of line to add to /etc/fstab for automount"
    echo ""
    echo "    # EFS mount point \"$EFS_VOLUME_TAG_NAME\""
    echo "    $FSTAB_LINE" 
    echo ""

# To Destroy EFS along with it's mountpoints. 
# This code is an example, and is not run a part of the above 'create' feature

    DESTROY="false"                               # destroy just created file system if "true"
    if [ "$DESTROY" == "true" ]; then

            # first remove the mount targets

        DESCRIBE_TARGETS_JSON=$(aws efs describe-mount-targets --file-system-id $EFS_FILESYS_ID --region $REGION)

        IDX=0
        while [ 1 ]; do
            MOUNT_TARGET_ID=$(echo $DESCRIBE_TARGETS_JSON | jq .MountTargets[$IDX].MountTargetId | sed 's/\"//g')
            if [ "$MOUNT_TARGET_ID" == "null" ]; then
                break;         # hit the end of the list
            fi
            echo "Deleting mount target $MOUNT_TARGET_ID"
            aws efs delete-mount-target --mount-target-id $MOUNT_TARGET_ID --region $REGION
            IDX=$((IDX+1))
        done

             # looks like NumberOfMountTargets must be empty before volume can
             # be deleted. This takes about 6 seconds.. poll for it

        MAX_ATTEMPTS=10
        for ((ATTEMPT=0; ATTEMPT<MAX_ATTEMPTS; ATTEMPT++)); do
            DESCRIBE_FILE_SYS_JSON=$(aws efs describe-file-systems --file-system-id $EFS_FILESYS_ID --region $REGION)
            NUM_OF_TARGETS=$(echo $DESCRIBE_FILE_SYS_JSON | jq .FileSystems[0].NumberOfMountTargets)
            if [ $NUM_OF_TARGETS -eq 0 ]; then 
                break;
            fi
            echo -ne "$ATTEMPT Wait for $NUM_OF_TARGETS mount targets to be destroyed  \r"
            sleep 1
        done

            # now destroy the file system

        echo "Deleting file system $EFS_FILESYS_ID \"$EFS_VOLUME_TAG_NAME\"     "
        aws efs delete-file-system --file-system-id $EFS_FILESYS_ID --region $REGION
    fi


