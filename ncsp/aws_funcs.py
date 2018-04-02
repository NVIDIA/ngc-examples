# aws_funcs.py                                               3/23/2018
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Amazon (aws) Cloud Service Provider specific functions
#
# HELPTEXT: "Amazon Cloud Service Provider"
#
import json
import time
import sys
from cspbaseclass import CSPBaseClass
from cspbaseclass import Which
from cspbaseclass import error, trace, trace_do, debug, debug_stop
import cmd

##############################################################################
# some Amazon aws defaults values that will vary based on users 
# 
# default_key_name:     User will need to create their own security key and 
#                       specify it's name here.
# region:               The Alibaba region that they wish to run in. Note that
#                       GPU instances might not be avaliable at all sites
# user:                 Login user name for instance. May be hardcoded by ISP 
#                       based on the image_name being selected. 
##############################################################################

default_key_name            = "my-security-key-name"
default_region              = "my-region-name"
default_user                = "my-user-name"

##############################################################################
# What image and instance type to bring up. 
#
# default_image_name:    Name of OS template that instance will be created with
# default_instance_type: The default name that defines the memory and cpu sizes
#                        and the gpu types for the instance. Changes
# default_choices:       Avaliable instance types that user can select with
#                        This will probably be different per region, and will
#                        continue to change over time. Used as a pre-check in  
#                        command parser to verify choice before sending to csp
##############################################################################

if (False):   # non gpu version - quick non-gpu testing
    default_image_name      = "ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server*"
    default_instance_type   = "t2.micro"
    default_choices         = ['t2.micro']
else:        # aws marketplace has nvidia volta image locked to only running on aws p3 type boxes
    default_image_name      = "NVIDIA Volta Deep Learning AMI*"
    default_instance_type   = "p3.2xlarge"   # 1gpu, 4gpu and 8gpu instances
    default_choices         = ['p3.2xlarge', 'p3.8xlarge', 'p3.16xlarge'] 

TIMEOUT_1 = (60 * 4) # create, start, terminate
TIMEOUT_2 = (60 * 4) # stop, ping
    
##############################################################################
# CSPClass
#
# Cloud Service Provided primitive access functions
##############################################################################    
class CSPClass(CSPBaseClass):
    ''' Cloud Service Provider Class '''
    
    ##############################################################################    
    # CSPSetupOK
    #
    # checks to see that user has ability to create and minipulate VM's on this
    # CSP. Want to check that up front, instead of later when actually talking
    # to the CSP. 
    #
    # does things like verifing that the CLI is installed on the machine, and
    # whatever else is quick and easy to check
    #
    # Should also check to see that can actually connect with the CSP provider
    # (network connection) and that network is reliable.
    #
    def CSPSetupOK(self):
        ''' quick check to verify amazon aws command line interface is installed '''

        fullpath = Which("aws")             # does cli application exist?       
        if (fullpath == None):
            return 1                        # error, cli app not found
        else:
            # TODO: verify network connection to CSP
            # TODO: check login setup correctly
            return 0
        
    ##############################################################################
    # ArgOptions
    #
    # aws specific argument parser. This extends or overrides default argument
    # parsing that is set up in ncsp.py/add_common_options() function
    #
    # All arguments set up here and in the common code are saved/restored from
    # the csp specific args file. See my_class.ArgSave/RestoreFromFile(parser) 
    # in the base class for implementation. 
    #
    def ArgOptions(self, parser):  
        ''' Aws specific option parser '''
        region_list = self.GetRegionsCached()
        parser.add_argument('--region', dest='region',
                            default=default_region, required=False,
                            choices=region_list,                        # regions change, queried outpu
                            help='region in which to create the VM')
        parser.add_argument('--instance_type', dest='instance_type',    # 'size' on azure, use 'instance-type' as common name
                            default=default_instance_type, required=False,
                            choices=default_choices,
                            help='VM instance (type) to create')
 
        parser.add_argument('--vpcid', dest='vpcid', 
                            default=None, required=False,
                            help='aws VPC id')
         
            # these override the common/default values from add_common_options
            # with this csp's specific values
            
        parser.set_defaults(image_name=default_image_name);
        parser.set_defaults(key_name=default_key_name)
        parser.set_defaults(user=default_user);
        
            # ping-ability makes starting/stopping more traceable, but this 
            # features is disabled by default, and explicidly needs to be 
            # enabled in the Networks Security Group -- see ICMP option
             
        parser.set_defaults(pingable=1)   # aws instances we created support pings (alibaba not)

    ###########################################################################
    # ArgSanity
    #
    # aws class specific argument checks, Called after the argument parser has run
    # on the user options as a hook to verify that arguments are correct
    #
    # 'parser' is the structure returned from argparse.ArgumentParser()
    #
    # Returns    0    success
    #            1    something is wrong, stop
    # 
    def ArgSanity(self, parser, args):
        ''' AWS Arg sanity checking '''
        
        # print args
        
        return 0    # do nothing for now
          
    ###########################################################################
    # GetRunStatus
    #
    # Returns the running status of the instance as a string, like 'running'
    # 'terminated', 'pending' etc.. This will be somewhat the same across
    # all CSPs, but since it comes from them you should not depend upon
    # an exact value out of CSP specific code
    #
    # Returns:    string describing state
    #
    def GetRunStatus(self, args):
        ''' Returns running-state of instance from describe-instance-status '''
        
        if (self.CheckID(args) == False):
            return 1
        
        cmd  = "aws ec2 describe-instance-status"
        cmd += " --instance-id %s" % args.vm_id   
        retcode, output, errval = self.DoCmd(cmd)
              
        decoded_output = json.loads(output)
        
        state = decoded_output['InstanceStatuses']
        if state.__len__() > 0:
            run_state = decoded_output['InstanceStatuses'][0]['InstanceState']['Name']
        else:
                # if describe-instance-status is empty for stopped states, use more detailed call

            cmd  = "aws ec2 describe-instances"
            cmd += " --instance-id %s" % args.vm_id   
            retcode, output, errval = self.DoCmd(cmd)
            
            if (retcode == 0):
                decoded_output = json.loads(output)
                    
                anyinfo = decoded_output['Reservations']
                if anyinfo.__len__() > 0: 
                    run_state = decoded_output['Reservations'][0]['Instances'][0]['State']['Name']
                else:
                    run_state = "terminated"   # doesn't exist any longer
        
            # return the value, should be something like "running" or "pending" or ""
            
        self.Inform(run_state)
        return(run_state);

    # From image file name, Find the WID of the AMI instance that will be loaded
    #
    # Get the image ID of the "NVIDIA Volta(TM) Deep Learning AMI" that we created.
    # Note that currently (10/2017) the ID of this image changes whenever we update 
    # the image. This query here does a name-to-id lookup. The name should remain constant.         
    def GetImageId(self, args):

        cmd  = "aws ec2 describe-images" 
        cmd += " --region %s" % args.region
        cmd += " --filters Name=name,Values=\"%s\"" % args.image_name
        retcode, output, errval = self.DoCmd(cmd)

        if (retcode != 0):
            error(errval)
            sys.exit(1)             # fail to get name, exit script

            # decode the JSON output
            
        decoded_output = json.loads(output)
        
        # print json.dumps(decoded_output, indent=4, sort_keys=True)
        args.image_id = decoded_output['Images'][0]['ImageId']   # ami-8ee326f6
        
        return(0)  
       
    ###########################################################################
    # GetIPSetupCorrectly
    #
    # Called after the instance is created in order to get if needed, and 
    # verify that a public IP address has been returned for the VM
    #
    # Some CSP's, like azure and alibaba return the IP address from another 
    # function that sets up the public IP. This needs to be called in the
    # CreateVM function in that case.
    #
    # Other CSP's like aws, return the IP address for you "free" of charge
    # as part of the instance information for the VM. This might be returned
    # only after the VM creation has been completed. 
    #
    # This function is genericly called after the VM has been found to be
    # running, to either simply verify that we have a valid IP address in
    # the first case above, or to ask the CSP for it and then verify it
    # in the second case. 
    #
    # public IP value will be in args.vm_id
    #
    # This function can do other cross-checks to validate other setups like
    # checking if the SSH key-name returned from the CSP is the same as we
    # sent it. Checks like this are optional, but highly desirable. 
    #
    # Returns:    0 success
    #             1 fails, invalid IP or can't get it
    #
    def GetIPSetupCorrectly(self, args):
        ''' called after 'running' status to get IP. Does nothing for Alibaba '''
        
            # On aws, IP address change across stop/start cases. 
            #
            # get full description of the instance json record - large
            # from this we can get the public IP address of the instance
        
        cmd  = "aws ec2 describe-instances"
        cmd += " --instance-id %s" % args.vm_id
        cmd += " --region %s" % args.region                 # us-west-2
        
        retcode, output, errval = self.DoCmd(cmd)

            # this return json structure from 'describe-instances' has about 50 values
            # in it that, as the command says, describes the instance. Only need a few
            # of them here.
            
        decoded_output = json.loads(output)
        
        args.vm_ip = decoded_output['Reservations'][0]['Instances'][0]['PublicDnsName']
        key_name   = decoded_output['Reservations'][0]['Instances'][0]['KeyName' ]
        
        debug(1, "ip: %s keyname: \"%s\"" % (args.vm_ip, key_name))
        
            # name of SSH keyfile was sent to Create function when VM was built, and we 
            # get a chance to read it back here. Parinoid check to verify that it is
            # the same. This should never happen, but check for safety
            
        if (key_name != args.key_name):         # cross-check
            error ("args.key_name:\"%s\" != version vm thinks its using:\"%s\"", args.key_name, key_name)
            return 1
     
        return 0
    
##############################################################################
# CSP specific Network Security Group Functions
#
#    ShowSecurityGroups       Displays NSG (network security groups) in region
#    ExistingSecurityGroup    Does NSG exist?
#    CreateSecurityGroup      Creates a NSG from a name, and adds rules
#    DeleteSecurityGroup      Deletes a NSG
##############################################################################

    ##############################################################################
    # ShowSecurityGroups  
    #
    # This function shows basic information about your account's security groups 
    # for your region. 
    #
    # Intended to be informative only, as each CSP will probably supply different
    # type of information.
    #
    # Returns:    0    one or more Netwroks Security Groups found in region
    #             1    error, or no NSG's defined in region
    # 
    def ShowSecurityGroups(self, args):
        ''' Displays all current security groups '''
        
        cmd  = "aws ec2 describe-security-groups "          # build the AWS command to create an instance
        cmd += " --region %s" % args.region                 # us-west-2
        
        retcode, output, errval = self.DoCmd(cmd)           # call the AWS command
        if (retcode != 0):                                  # check for return code
            error ("Problems describing security groups")
            return 1
        decoded_output = json.loads(output)
        items = len(decoded_output["SecurityGroups"])       # number of security groups
        # trace(2, json.dumps(decoded_output["SecurityGroups"][0], 4, sort_keys = True))
    
            # returns a list of security groups. display them
            
        for idx in range(0, items):
            print "%2d %-12s \"%s\" \"%s\"" % (idx,
                                               decoded_output["SecurityGroups"][idx]["GroupId"], 
                                               decoded_output["SecurityGroups"][idx]["GroupName"],
                                               decoded_output["SecurityGroups"][idx]["Description"])
        return 0
    
    ##############################################################################
    # ExistingSecurityGroup
    #
    # Given a name of a security group in args.nsg_name, this function sees
    # if it currently exists on the CSP
    #
    # This entire application is written assuming that once a security group is
    # created, it doesn't need to really change much for the lifetime of the
    # universe. Therefor we don't delete them unless specificly asked for
    #
    # The purpose of this function is to decide if we need to create a Network
    # Security Group, or to return the id of that existing group in args.nsg_id
    #
    # Returns:   0 if security group args.nsg_name currently exists and is valid
    #            1 need to create a group
    #
    def ExistingSecurityGroup(self, args):
        ''' Does the security group name currently exist ? get it if it does'''

        trace(2, "\"%s\"" % (args.nsg_name))

        if (args.nsg_name == "" or args.nsg_name == None or args.nsg_name == "None"):
            error("NetworkSecurityGroup name is \"%s\"" % args.nsg_name)
            return 1

            # Is there a better way to do this than to pull in the entire dictionary
            # and iterate through the keys? 
            
        cmd  = "aws ec2 describe-security-groups "          # build the AWS command to create an instance
        cmd += " --region %s" % args.region                 # us-west-2
        
        retcode, output, errval = self.DoCmd(cmd)           # call the AWS command
        if (retcode != 0):                                  # check for return code
            error ("Problems describing security groups")
            return 1
        decoded_output = json.loads(output)
        
            # number of security groups
            
        items = len(decoded_output["SecurityGroups"])       # number of security groups
        
            # slow search for name 
            
        for idx in range(0, items):
            if (decoded_output["SecurityGroups"][idx]["GroupName"] == args.nsg_name): 
                args.nsg_id = decoded_output["SecurityGroups"][idx]["GroupId"]
                debug(2, "%2d %-12s \"%s\"" % (idx,
                                              decoded_output["SecurityGroups"][idx]["GroupId"], 
                                              decoded_output["SecurityGroups"][idx]["GroupName"]))
                return 0        # found it
            
            # returns 1 if did not find security group
            
        trace(2, "Did not find security group: \"%s\"" % args.nsg_name)
        return 1
        
    ##############################################################################
    # CreateSecurityGroup
    #
    # Creates a full network security group by the name of args.nsg_name, saves the 
    # value in args.nsg_id
    #
    # Any additional rules required for the security group to set up ssh, ssl and 
    # ping are added to the group here before it is returned.
    #
    # If the CSP has object-taging feature, the new security group should be 
    # tagged with a unique name so it can be identified later. 
    #
    # IMPORTANT: if you can create a rule to make the VM pingable (a good thing 
    #            for initial development), be sure to call following in ArgOptions
    #            so that the ping feature will be used when needed by this app
    #           
    #                "parser.set_defaults(pingable=1)"
    #
    def CreateSecurityGroup(self, args):
        ''' creates security group. saves it in args.nsg_id '''
        
        trace(2, "\"%s\" %s" % (args.nsg_name, args.nsg_id))

            # Get the users VPC id if we don't have it
            
        if (args.vpcid == "" or args.vpcid == None or args.vpcid == "None"):
            cmd  = "aws ec2 describe-vpcs"
            cmd += " --region %s" % args.region
            retcode, output, errval = self.DoCmd(cmd)       # call the AWS command
            if (retcode != 0):
                return retcode
            decoded_output = json.loads(output)
            debug(2, json.dumps(decoded_output, indent=4, sort_keys=True))
            args.vpcid = decoded_output["Vpcs"][0]["VpcId"]
            debug(1, "args.vpcid <--- %s" % args.vpcid)
             
            # create the security group, with a meaningful description
            
        desc = "NSG Generated for %s" % args.vm_name
        
        cmd = "aws ec2 create-security-group"
        cmd += " --group-name %s"       % args.nsg_name 
        cmd += " --description \"%s\""  % desc
        cmd += " --vpc-id %s"           % args.vpcid
        cmd += " --region %s"           % args.region
       
        retcode, output, errval = self.DoCmd(cmd)           # call the AWS command
        if (retcode != 0):                                  # check for return code
            return retcode
        
            # get the groupid of the new security group
            
        decoded_output = json.loads(output)  
        debug(2, json.dumps(decoded_output, indent=4, sort_keys=True))
        args.nsg_id = decoded_output["GroupId"]        
        debug(1, "args.nsg_id <--- %s" % args.nsg_id)
        
            # tag new group with our group name
            
        cmd =  "aws ec2 create-tags" 
        cmd += " --resource %s"             % args.nsg_id
        cmd += " --tags Key=Name,Value=%s"  % args.nsg_name

        retcode, output, errval = self.DoCmd(cmd)           # call the AWS command
        if (retcode != 0):                                  # check for return code
            return retcode

            # Security rules -- make a list of ingress and outgress rules - easy to change
            # slow, but this code is rarely used. understandability is more important
            
        ingress = {}
        ingress[0] = {"IpProtocol":"tcp", "ToPort":22,    "FromPort":22,  "CidrIp":"0.0.0.0/0", "Description":"For SSH"     }
        ingress[1] = {"IpProtocol":"tcp", "ToPort":443,   "FromPort":443, "CidrIp":"0.0.0.0/0", "Description":"For SSL"     }
        ingress[2] = {"IpProtocol":"tcp", "ToPort":5000,  "FromPort":5000,"CidrIp":"0.0.0.0/0", "Description":"For NVIDIA DIGITS6" }
        ingress[3] = {"IpProtocol":"icmp","ToPort":-1,    "FromPort":8,   "CidrIp":"0.0.0.0/0", "Description":"To allow to be pinged" }

        egress = {}
        
        outer_retcode = 0
        for idx in range(0, len(ingress)):
            self.Inform("CreateNSG rule %s.%s" % args.nsg_name, ingress[idx]["Name"] )        

            cmd =  "aws ec2 authorize-security-group-ingress"
            cmd += " --group-id %s" % args.nsg_id
            cmd += " --ip-permissions '[{"                                    # mini-embedded json like
            cmd +=   " \"IpProtocol\":\"%s\","  % ingress[idx]["IpProtocol"]
            cmd +=   " \"ToPort\":%s,"          % ingress[idx]["ToPort"]      # KEEP 'To' before 'From' - no effect for tcp, but
            cmd +=   " \"FromPort\":%s,"        % ingress[idx]["FromPort"]    # required for how Wildcard ICMP type is defined
            cmd +=   " \"IpRanges\": [{"
            cmd +=      " \"CidrIp\":\"%s\","       % ingress[idx]["CidrIp"]
            cmd +=      " \"Description\":\"%s\""   % ingress[idx]["Description"]
            cmd +=   " }]"
            cmd += " }]'"

            retcode, output, errval = self.DoCmd(cmd)       # call the AWS command
            if (retcode != 0):
                outer_retcode = retcode                     # keep any non-zero return code
        
        
                # egress rules -- as of 1/2018 there arn't any...
        
        return outer_retcode

    ##############################################################################
    # DeleteSecurityGroup
    # 
    # Delets the security group specified at args.nsg_id, and clears that value
    #
    # If group Rules attached to the NSG need to be individually deleted, that
    # must also be done here if not done automaticly by the CSP
    #
    def DeleteSecurityGroup(self, args):
        ''' deletes the security group '''
        
        trace(2, "\"%s\" %s" % (args.nsg_name, args.nsg_id))
        
        if (args.nsg_id == None):
            error("NSG %s already deleted", args.nsg_name)
            return(1)
        
        cmd =  "aws ec2 delete-security-group" 
        cmd += " --group-id %s"             % args.nsg_id
        retcode, output, errval = self.DoCmd(cmd)           # call the AWS command
        if (retcode != 0):                                  # check for return code
            return retcode
        args.nsg_id = None                                  # remove id from args
        
        return(0)

##############################################################################
# CSP specific VM functions
#
#    CreateVM                Creates a complete fully running VM
#    StartVM                 Starts a VM if it was stopped, returns running
#    StopVM                  Stops the VM if it is currently running
#    RestartVM               Resets VM, may not quite be same as Stop/Start
#    DeleteVM                Removes from the CSP a running or stopped VM
##############################################################################
    
    ##############################################################################
    # CreateVM 
    # 
    # Creates a new VM, and returns when it is fully running.  
    #
    # Note that due to simple way that this code saves it's peristent
    # data (the id, user name, ... ), only 1 instance can be created
    # at a time. Nothing preventing multiple VM's other than way to save/reference
    # the id values. The  CSPClass.Delete function removes the saved references
    #
    # The "args" option specify the CSP specific name, disk size, instance type,
    # or any other parameter required to fully define the VM that is to be created
    # 
    # Before creating the VM, effort is made to verify that all the supplied 
    # parameters, such as the SSH key name are valid.
    #
    # Network Security Group (NSG) is created if needed. 
    #
    # Returns:    0    successful, VM fully created, up and ssh-able
    #             1    failure, VM not created for one of many possible reasons
    #
    def CreateVM(self, args):
        ''' Creates a new VM. 'args' holds parameters '''
    
        if (args.vm_id != "None" and args.vm_id != None):
            error("Instance \"%s\" already exists, run 'deleteVM' first, or 'clean' if stale arg list" % args.vm_id)
            return 1

        args.vm_ip = ""                                             # make sure IP address is clear

            # ssh key file, builds path from options, checks existance
            
        retcode = self.CheckSSHKeyFilePath(args, ".pem")
        if (retcode != 0):
            return(retcode)

            # security group, create if neeeded, does nothing if already exists
            # consider moving this step outside this VM create so that better 
            # reflects real VM timing?

        self.Inform("CreateNSG")
        if (self.CreateNSG(args) != 0):                             # sets args.nsg_id
            return 1
        trace(2, "nsg_id: \"%s\" %s" % (args.nsg_name, args.nsg_id))

            # look up image-name, return region specific image id
 
        self.Inform("GetImageId")
        if (self.GetImageId(args) != 0):
            return 1
        trace(2, "image_id: \"%s\" %s" % (args.image_name, args.image_id))

            # with security group and image id, we can now create the instance
        
        self.Inform("run-instances")
        cmd  = "aws ec2 run-instances"                      # build the AWS command to create an instance
        cmd += " --image-id %s" % args.image_id             # aws image identifer via self.GetImageid()
        cmd += " --instance-type %s" % args.instance_type   # t2.micro
        cmd += " --region %s" % args.region                 # us-west-2
        cmd += " --key-name %s" % args.key_name             # my-security-key
        cmd += " --security-group-ids %s" % args.nsg_id     # Security Group

        retcode, output, errval = self.DoCmd(cmd)           # call the AWS command
        if (retcode != 0):                                  # check for return code
            error ("Problems creating VM \"%s\"" % args.vm_name)
            return 1                                        # nothing to delete, can return
      
            # decode the JSON output
            
        decoded_output = json.loads(output)          # convert json format to python structure
        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
        
        args.vm_id = decoded_output['Instances'][0]['InstanceId']
        args.vm_ip = ""                             # don't have IP we see it running
                       
            # Name your instance! . Done here instead of in run-instances call 
            # it's tricky in bash to get space/qoutes right, at least in original bash code where
            # this was orginally written.. :-)
            
        self.Inform("create-tags")
  
        cmd  = "aws ec2 create-tags"
        cmd += " --resource %s" % args.vm_id
        cmd += " --tags Key=Name,Value=%s" % args.vm_name  # unique time-stamped name

        retcode, output, errval = self.DoCmd(cmd)
           
            # wait till the instance is up and running, pingable and ssh-able
            
        if (retcode == 0):
            retcode = self.WaitTillRunning(args, "running", TIMEOUT_1) 
                        
            # save vm ID and other fields setup here so don't use them if error later
        
        self.ArgSaveToFile(args)
         
        debug(2, "createVM returning %d" % retcode)   
        return retcode                                  # 0: succcess, 1: failure
    
    ##############################################################################
    # StartVM
    #
    # Starts a Stopped VM, returns it in a fully running state, where we have 
    # the correct IP address if it changed, and can ssh into the VM
    #
    # Returns:    0    successful, VM up and ssh-able
    #             1    failure, VM not able to be started, or invalid ID supplied
    #
    def StartVM(self, args):
        ''' Starts the VM '''
        
        rc = 1                                          # assume error
        if (self.CheckID(args) == False):
            return 1
        
            # get run status and check current state
            
        status = self.GetRunStatus(args)
        if (status == "running"):
            return 0                                    # already running, simply return
        elif (status == "stopping"):
            buf = "%s is in %s state, can't start running now" % (args.vm_id, status)
            error(buf)
        elif (status == "stopped" or status == "null"):
            rc = 0                                      # ok to proceed
        else:
            buf = "id %s is in \"%s\" state, not sure can start running" % (args.vm_id, status)
            error(buf)
            
        if (rc != 0):
            return rc                                   # unexpected status
        
        self.Inform("StartVM")   
       
            # start the VM 
            
        cmd = "aws ec2 start-instances"
        cmd += " --instance-id %s" % args.vm_id
        cmd += " --region %s" % args.region             # us-west-2
        retcode, output, errval = self.DoCmd(cmd)
        if (retcode == 0):
            rc = self.WaitTillRunning(args, "running", TIMEOUT_1) 
        
        return rc                                        # 0: succcess, 1: failure
    
    ##############################################################################
    # StopVM
    #
    # Stops a running VM. No persistent resouces are deallocated, as it's expected
    # that the VM will be started again.
    #
    # Note that most CSP's will continue to charge the customer for the allocated
    # resources, even in a Stopped state.
    #
    # Returns:    0    VM fully stopped
    #             1    unable to stop VM. May be invalid ID or connection to CSP
    #
    def StopVM(self, args):
        ''' Stop the VM '''
        
        if (self.CheckID(args) == False):
            return 1
        
        retcode = self.CheckRunStatus(args, "running")
        if (retcode != 0):
            error ("Not running")
            return retcode
        
        self.Inform("StopVM")   
        
        cmd = "aws ec2 stop-instances"
        cmd += " --instance-id %s" % args.vm_id
        cmd += " --region %s" % args.region                 # us-west-2
       
        retcode, output, errval = self.DoCmd(cmd)
        if (retcode == 0):
            status = self.GetRunStatus(args)
            
                # The instance becomes "Stopping" after a successful API request, 
                # and the instance becomes "Stopped" after it is stopped successfully.
                
            if (status != "stopping"):
                error("Asked VM to stop, but status = \"%s\"" % (status))
                retcode = 1
            else:
                retcode = self.WaitForRunStatus(args, "stopped", TIMEOUT_2)
        
        return retcode                       # 0: succcess, 1: failure
    
    ##############################################################################
    # RestartVM
    #
    # This function restarts a currently running VM
    #
    # Returns with the VM in a fully running state, where we have it's public IP
    # address and can ssh into it
    #
    # Returns:    0    successful, VM up and ssh-able
    #             1    failure, VM not able to be reset, or invalid ID supplied
    #
    def RestartVM(self, args):              # also known as 'reboot' on aws
        ''' Restarts the VM '''
        
        if (self.CheckID(args) == False):
            return 1
        
        retcode = self.CheckRunStatus(args, "running")
        if (retcode != 0):
            error ("Not running")
            return retcode
        
        self.Inform("RestartVM")

        cmd = "aws ec2 reboot-instances"
        cmd += " --instance-id %s" % args.vm_id
        cmd += " --region %s" % args.region                 # us-west-2
        
        retcode, output, errval = self.DoCmd(cmd)
        
            # on aws after "reset", the status never becomes "un-running" 
            # anytime durring the reset procss -- so we check when it FAILS 
            # to ping to know if estart actually occured. Then we simply wait 
            # till it's back up again - pingable and ssh-able to know it's 
            # running
                
        if (retcode == 0):
            if (args.pingable == 1):
                retcode = self.WaitForPing(args, False, TIMEOUT_2)
            else:
                time.sleep(5)           # let VM go down enough so SSH stops (we hope)
                retcode = 0             # fake success, since ping isn't supported
                
            if (retcode != 0):
                error("never went un-pingable. Did VM restart?")
            else:
                retcode = self.WaitTillRunning(args, "running", TIMEOUT_1) 
        return retcode                  # 0: succcess, 1: failure
    
    ##############################################################################
    # DeleteVM
    #
    # Deletes a VM and releases of it's resources other than the Network Security 
    # Group. 
    #
    # Returns:   0    success, VM and all it's resource are gone
    #            1    problems.. 
    #
    def DeleteVM(self, args):
        ''' delete the vm and all the pieces '''
        
        if (self.CheckID(args) == False):
            return 1
        
        cmd =  "aws ec2 terminate-instances"
        cmd += " --instance-id %s" % args.vm_id
        cmd += " --region %s" % args.region                 # us-west-2
        
        retcode, output, errval = self.DoCmd(cmd)
        if ( retcode == 0 ):
            retcode = self.WaitForRunStatus(args, "terminated", TIMEOUT_1)
            
            # Is error handled ok? What if problems deleting?  -- instance left around? 
            
        if (retcode == 0):              # successful so far?
            self.Clean(args)            # remove file with the persistent id, ip address, ..
            self.m_args_fname = ""      # clear name, so won't write back args when done
        return retcode                  # 0: succcess, 1: failure

        
##############################################################################
# CSP specific utility functions
#
#    ShowRunning             Shows all the account's running VM's
#    GetRegions              Returns proper list of regions
##############################################################################

    ##############################################################################
    # ShowRunning
    #
    # CSP specific information function to print out the name, type, description
    # and start time of all the running instances in the region
    #
    # Returns:    0    1 or more running instances were found in CSP's args.region
    #             1    no running instances found
    #
    def ShowRunning(self, args):
        ''' Shows list of running instances within region of account '''
        
        lines_printed = 0
        
        cmd =  "aws ec2 describe-instances"
        # cmd += " --region %s" % args.region                 # us-west-2
        retcode, output, errval = self.DoCmd(cmd)
        if ( retcode == 0 ):
            decoded_output = json.loads(output)
            items = len(decoded_output["Reservations"])       # number of security groups
            for idx in range(0, items):
                tagname = "No 'Name' tag provided to identify instance"  # expect the worse
                state   = decoded_output["Reservations"][idx]["Instances"][0]["State"]["Name"]
                if (state == "running"):
                    try:    # may not exist, and may be multiple tags...
                        tags = decoded_output["Reservations"][idx]["Instances"][0]["Tags"]
                        tlen = len(tags)
                        for tidx in range(0, tlen):
                            if (tags[0]["Key"] == "Name"):
                                tagname = tags[0]["Value"]
                                break;
                    except:
                        dummy = 1
                    if (lines_printed == 0):
                        print("# %s:" % self.m_class_name )
                    print(" %-36s %-16s %10s \"%s\"" % 
                          (decoded_output["Reservations"][idx]["Instances"][0]["InstanceId"],
                           decoded_output["Reservations"][idx]["Instances"][0]["InstanceType"],
                           decoded_output["Reservations"][idx]["Instances"][0]["LaunchTime"][0:10],
                           tagname))
                    lines_printed += 1
                    
            if (lines_printed == 0):
                print("# %s: No running instances found" % self.m_class_name )
        
        return retcode      # 0 success, !0 failure
    
    ##############################################################################
    # GetRegions
    #
    # Returns a list of regions where VMs can be created by this CSP. 
    #
    # These are basiclly the names of the CSP's data centers... Each data center
    # may offer different resoures. Don't care about that here. Just need the
    # name.
    #
    # Used in a choice-list in the arg parser when user gives a non-default
    # region name to catch invalid names before any real processing is done
    #
    # Returns:    list of names
    def GetRegions(self):
        ''' Returns a list of region names for the CSP '''
                
        mylist = []
        cmd =  "aws ec2 describe-regions"
        retcode, output, errval = self.DoCmd(cmd)
        if ( retcode == 0 ):
            decoded_output = json.loads(output)
            items = len(decoded_output["Regions"])       # number of regions
            for idx in range(0, items):
                name = decoded_output["Regions"][idx]["RegionName"]
                mylist.append(str(name))
        return mylist 
    

        
