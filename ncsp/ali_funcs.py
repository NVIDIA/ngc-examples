# ali_funcs.py                                               3/27/2018
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Alibaba (ali) Cloud Service Provider specific functions
#
# HELPTEXT: "Alibaba Cloud Service Provider"
#

import json
import time
import subprocess
from cspbaseclass import CSPBaseClass
from cspbaseclass import Which
from cspbaseclass import error, trace, trace_do, debug, debug_stop

##############################################################################
# some Alibaba defaults values that will vary based on users 
# 
# default_key_name:     User will need to create their own security key and 
#                       specify it's name here.
# region:               The Alibaba region that they wish to run in. Note that
#                       GPU instances might not be avaliable at all sites
# user:                 Login user name for instance. May be hardcoded by ISP 
#                       based on the image_name being selected. 
##############################################################################

default_key_name        = "my-security-key-name"
default_region          = "my-region-name"
default_user            = "my-user-name"

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

default_image_name_international      = "NVIDIA GPU Cloud Virtual Machine Image 18.03.0"
default_image_name_china              = "NVIDIA GPU Cloud VM Image 18.03.0"

    # Note different names for chinese marketplace verses international marketplace

default_image_name      = default_image_name_international
if (False):   # non GPU choices for script testing..
    default_instance_type   = "ecs.sn1.medium"
    default_choices         = ['ecs.sn1.small', 'ecs.sn1.large', 'ecs.sn1.xlarge',   # compute optimized
                               'ecs.sn2.small', 'ecs.sn2.large', 'ecs.sn2.xlarge'],  # general purpose
else:         # GPU instances - normal usage
    default_instance_type   = "ecs.gn5-c4g1.xlarge"
    default_choices         = ['ecs.gn5-c4g1.xlarge', 'ecs.gn5-c8g1.2xlarge',        # gn6 are nvidia P100
                               'ecs.gn5-c4g1.2xlarge', 'ecs.gn5-c8g1.4xlarge'
                               'ecs.gn5-c28g1.7xlarge', 'ecs.gn5-c8g1.8xlarge',
                               'ecs.gn5-c28g1.14xlarge', 'ecs.gn5-c8g1.14xlarge'],
                               
TIMEOUT_1 = (60 * 4) # create, start, terminate
TIMEOUT_2 = (60 * 4) # stop, ping

##############################################################################
# CSPClass
#
# Cloud Service Provided primitive access functions
##############################################################################    
class CSPClass(CSPBaseClass):
    ''' Cloud Service Provider Class for alibaba'''
    
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
        ''' quick check to verify alibaba command line interface is installed '''
        
        fullpath = Which("aliyuncli")       # does cli application exist?       
        if (fullpath == None):
            return 1                        # error, cli app not found
        else:
            # TODO: verify network connection to CSP
            # TODO: check login setup correctly
            return 0
    

    ##############################################################################
    # ArgOptions
    #
    # alibaba specific argument parser. This extends or overrides default argument
    # parsing that is set up in ncsp.py/add_common_options() function
    #
    # All arguments set up here and in the common code are saved/restored from
    # the csp specific args file. See my_class.ArgSave/RestoreFromFile(parser) 
    # in the base class for implementation. 
    # 
    def ArgOptions(self, parser):  
        ''' Alibaba specific option parser '''
       
            # set up Alibaba specific fields of the parser   
        region_list = self.GetRegionsCached()
        parser.add_argument('--RegionId', dest='region',
                            default=default_region, required=False,
                            choices=region_list,  # query, keeps changing
                            help='region in which to create the VM')
        parser.add_argument('--instance_type', dest='instance_type',   # 'size' on azure, use 'instance-type' as common name
                            default=default_instance_type, required=False,                
                            choices=default_choices,                  # should query list if can (region dependent?)
                            help='VM instance (type) to create')
        parser.add_argument('--auto-ngc-login', dest='auto_ngc_login', action='store_true',
                            default=False, required=False,
                            help='Enable NGC auto login using the Azure Key Vault')
        parser.add_argument('--keyvault', dest='keyvault',
                            default=None, required=False,
                            help='Azure Key Vault name that contains the NGC API Key')
        parser.add_argument('--apikey', dest='apikey',
                            default=None, required=False,
                            help='NGC API Key to store in the vault')
        parser.add_argument('--bandwidth_out', dest='bandwidth_out',
                            default=10, required=False, type=int,
                            help='Internet Max Bandwidth Out (1 to 200 Bbps)')        
        parser.add_argument('--charge_type', dest='charge_type',
                            default='PostPaid', required=False,
                            choices=['PostPaid', 'PrePaid'],  
                            help='Instance Charge Type')
	parser.add_argument('--image_owner_alias', dest='image_owner_alias',
                            default='marketplace', required=False,
                            choices=['system', 'self', 'others', 'marketplace'],
                            help='Image owner')     
        parser.set_defaults(image_name=default_image_name);
        parser.set_defaults(key_name=default_key_name)
        parser.set_defaults(user=default_user)
        
            # ping-ability makes starting/stopping more traceable, but this 
            # features is disabled by default, and explicidly needs to be 
            # enabled in the Networks Security Group -- see ICMP option
             
        parser.set_defaults(pingable=1)   # alibaba instances we created support pings 
       
    ###########################################################################
    # ArgSanity
    #
    # alibaba class specific argument checks, Called after the argument parser has run
    # on the user options as a hook to verify that arguments are correct
    #
    # 'parser' is the structure returned from argparse.ArgumentParser()
    #
    # Returns    0    success
    #            1    something is wrong, stop
    # 
    def ArgSanity(self, parser, args):
        ''' Alibaba Arg sanity checking '''
        
        rc = 0
        if args.bandwidth_out < 1 or args.bandwidth_out > 200:
            error("bandwidth must be between 1 an 200")
            rc = 1
            
        return(rc)          # 0 good, 1 stop  

    ###########################################################################
    # overrides common method in base class     
    
    def DoCmdNoError(self, cmd):
        ''' ali specifc Blocking command -- returns command output, doesn't report error'''
        
        debug(1, cmd)
        self.Log(cmd)
        
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, errval = child.communicate()                # returns data from stdout, stderr
        debug(3, output)                                    # full output for trace    
       
        # print "cmd:              %s " % cmd
        # print "child.returncode: %d " % child.returncode
        # print "errval:           %s " % errval
        # print "output:\n%s " % output

            # ali error output is in json format -- kind of... 
            # {
            #     "Message": "The specified InstanceId does not exist.", 
            #     "Code": "InvalidInstanceId.NotFound"
            # }
            # Detail of Server Exception:
            #
            # HTTP Status: 404 Error:InvalidInstanceId.NotFound The specified InstanceId does not exist. RequestID: C66FB5EA-FA09-41B2-AD69-9A68BCCE0B4A

        if child.returncode != 0 and errval == "":                
            pos = output.find('}')
            if (pos == -1):
                return(child.returncode, "", errval) 
            
            jsonbuf = output[:pos+1]    # only the stuff before the first '}'
            decoded_output = json.loads(jsonbuf)
            errval = decoded_output['Message']
            
        return (child.returncode, output, errval)           # pass back retcode, stdout, stderr
    
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
        
        cmd  = "aliyuncli ecs DescribeInstanceAttribute"
        cmd += " --InstanceId %s" % args.vm_id   
        retcode, output, errval = self.DoCmd(cmd)
                
        run_state = "Terminated"    # assume: doesn't exist any longer
        if (retcode == 0):          # did actually grab a real live status ?
            decoded_output = json.loads(output)
        
            id = decoded_output['InstanceId']
            if (id.__len__() > 0 and id == args.vm_id):
                run_state = decoded_output['Status']
        
            # return the value, should be something like "running" or "pending" or ""
            
        self.Inform(run_state)
        return(run_state);


    ##############################################################################
    # From image file name, Find the ID of the AMI instance that will be loaded
    #
    # Get the image ID of the "NVIDIA GPU Cloud Virtual Machine Image" that we created.
    # Note that currently (10/2017) the ID of this image changes whenever we update 
    # the image. This query here does a name-to-id lookup. The name should remain constant.         
    def GetImageId(self, args):

            # if already have the ID, can skip this step. Note "None" as string from args file
            
        if (args.image_id != "" and args.image_id != None and args.image_id != "None"):
            return 0
        
            # query name, to return id
            
        cmd  = "aliyuncli ecs DescribeImages" 
        cmd += " --RegionId %s" % args.region
        cmd += " --ImageName \"%s\"" % args.image_name
        cmd += " --ImageOwnerAlias %s" % args.image_owner_alias

        retcode, output, errval = self.DoCmd(cmd)
       
        if (retcode != 0):
            error(errval)
            return 1
            
            # decode the JSON output
            
        decoded_output = json.loads(output)
        trace(2, json.dumps(decoded_output, indent=4, sort_keys=True))
        
        args.image_id = decoded_output['Images']['Image'][0]['ImageId']
        return 0
    
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
        
        if (args.vm_ip == ""):      # this ip value should have been set in Create
            error("No IP for VM: \"%s\"" % args.vm_name)
            return(1)
        
        # TODO: see if new IP (which we query for RIGHT NOW is different than
        #       the vm_ip that was gathered before. Alibaba is NOT suppose to
        #       change the IP address once it's created for the life of
        #       the VM.. but that's an ass-u-m(e)-tion because it was seen
        #       to move more than once.
        #
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
        
        cmd  = 'aliyuncli ecs DescribeSecurityGroups'
        cmd += " --RegionId %s" % args.region                       # us-west-1
        cmd += " --PageSize 50"                                     # default is 10, max is 50
        cmd += " --output json"
        cmd += " --filter SecurityGroups.SecurityGroup[].SecurityGroupName"

        retcode, output, errval = self.DoCmd(cmd)                   # call the Alibaba command
        if (retcode != 0):                                          # check for return code
            error ("Problems describing security groups")
            return 1
        print output            # see function below for example of output
        return(0)
 
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
        ''' Does the security group name currently exist ? get it if it does '''
        
        trace(2, "\"%s\"" % (args.nsg_name))
        
        if (args.nsg_name == "" or args.nsg_name == None or args.nsg_name == "None"):
            error("NetworkSecurityGroup name is \"%s\"" % args.nsg_name)
            return 1
        
            # can it be found by name? -- get list of all names first
        
        cmd  = 'aliyuncli ecs DescribeSecurityGroups'
        cmd += " --RegionId %s" % args.region                       # us-west-1
        cmd += " --PageSize 50"                                     # default is 10, max is 50
        cmd += " --output json"
        cmd += " --filter SecurityGroups.SecurityGroup[].SecurityGroupName"

        retcode, output, errval = self.DoCmd(cmd)                   # call the Alibaba command
        if (retcode != 0):                                          # check for return code
            error ("Problems describing security groups")
            return 1
            
            # returns a Json object like:
            #     [
            #        "NexposeSG", 
            #        "NewtonSG", 
            #        "sg-rj93y8iuj33uosositpw"
            #     ]
            #
            # Use json converter to make it into a list
            #     [u'NexposeSG', u'NewtonSG', u'sg-rj93y8iuj33uosositpw']
            
        decoded_output = json.loads(output)                     # convert json format to python structure
        
                # does the list contain our requested security group name?
       
        if (args.nsg_name in decoded_output):
                        
                # yes it does, now go back and find the index into the list of names
                # then go back and pull the json record for that idx and filter it
                # for the SecurityGroupId id. 
                
            idx = 0   
            for item in decoded_output:
                if (unicode(args.nsg_name) == item):
                    # print "List contains SG name \"%s\" at index %d" % (args.nsg_name, idx)
                    
                    cmd  = 'aliyuncli ecs DescribeSecurityGroups'
                    cmd += " --RegionId %s" % args.region                       # us-west-1
                    cmd += " --PageSize 50"                                     # default is 10, max is 50
                    cmd += " --output json"
                    cmd += " --filter SecurityGroups.SecurityGroup[" 
                    cmd += str(idx)                                             # index to string
                    cmd += "].SecurityGroupId"
                        
                    retcode, output, errval = self.DoCmd(cmd)                   # call the Alibaba command
                    if (retcode != 0):                                          # check for return code
                        error ("Problems describing security groups")
                        return False       
                    
                    trace(3, output)
                        
                        # existing Security group ID is saved in the args structure
                        #
                        # just to make it more of a pain because it's not hard enough
                        # it's necessary to remove the surrounding qoute charaters from
                        # the group id here
                                     
                    args.nsg_id = (output.replace('"', '')).strip()             # remove surrounding qoutes
                                                                                # use strip() to remove newline                
                    trace(2, "args.nsg_id: \"%s\"" % args.nsg_id)           
                    return 0
                idx = idx + 1
                
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

            # create security group
                  
        cmd  = 'aliyuncli ecs CreateSecurityGroup'
        cmd += " --RegionId %s" % args.region                       # us-west-1
        cmd += " --SecurityGroupName \"%s\"" % args.nsg_name        # "NvidiaSG"
 
        retcode, output, errval = self.DoCmd(cmd)                   # call the Alibaba command
        if (retcode != 0):                                          # check for return code
            error ("Problems creating security group")
            return 1
      
            # decode the JSON output
            
        decoded_output = json.loads(output)                         # convert json format to python structure
        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
        
        security_group_id = decoded_output['SecurityGroupId']
        
            # new Security group ID is saved in the args structure
                     
        args.nsg_id = security_group_id
        
            # A new security group will not have any rules in it.  
            # The following commands will open inbound ports 22 (for SSH), 
            # 443 (for HTTPS), and 5000 (for DIGITS6):

        cmd  = 'aliyuncli ecs AuthorizeSecurityGroup' 
        cmd += ' --RegionId %s' % args.region                       # us-west-1
        cmd += ' --SecurityGroupId %s' % security_group_id          # "sg-rj999tz2kpxehy7obsjn" 
        cmd += ' --IpProtocol tcp --PortRange 22/22 --SourceCidrIp 0.0.0.0/0'
        cmd += ' --Policy accept --Description SSH'
        self.DoCmd(cmd)
        
        cmd  = 'aliyuncli ecs AuthorizeSecurityGroup' 
        cmd += ' --RegionId %s' % args.region                       # us-west-1
        cmd += ' --SecurityGroupId %s' % security_group_id          # "sg-rj999tz2kpxehy7obsjn" 
        cmd += ' --IpProtocol tcp --PortRange 443/443 --SourceCidrIp 0.0.0.0/0'
        cmd += ' --Policy accept --Description HTTPS'
        self.DoCmd(cmd)
        
        cmd  = 'aliyuncli ecs AuthorizeSecurityGroup' 
        cmd += ' --RegionId %s' % args.region                       # us-west-1
        cmd += ' --SecurityGroupId %s' % security_group_id          # "sg-rj999tz2kpxehy7obsjn" 
        cmd += ' --IpProtocol tcp --PortRange 5000/5000 --SourceCidrIp 0.0.0.0/0'
        cmd += ' --Policy accept --Description DIGITS6'
        self.DoCmd(cmd)        

        cmd  = 'aliyuncli ecs AuthorizeSecurityGroup' 
        cmd += ' --RegionId %s' % args.region                       # us-west-1
        cmd += ' --SecurityGroupId %s' % security_group_id          # "sg-rj999tz2kpxehy7obsjn" 
        cmd += ' --IpProtocol icmp --PortRange -1/-1'               # Is value Ok? (-1/8 for Alibaba?)
        cmd += ' --SourceCidrIp 0.0.0.0/0'
        cmd += ' --Policy accept --Description \"Support for ping\"'
        self.DoCmd(cmd)        

             # The following command will open all outbound ports:

        cmd  = 'aliyuncli ecs AuthorizeSecurityGroupEgress'
        cmd += ' --RegionId %s' % args.region                       # us-west-1
        cmd += ' --SecurityGroupId %s' % security_group_id          # "sg-rj999tz2kpxehy7obsjn" 
        cmd += ' --IpProtocol all --PortRange -1/-1 --DestCidrIp 0.0.0.0/0'
        cmd += ' --Policy accept --Description \"All open!\"'
        retcode, output, errval = self.DoCmd(cmd)                   # call the Alibaba command
            
        if (retcode != 0):                                          # check for return code
            error ("Problems setting up security group rules")
            return 1
       
        return 0                                                    # happy return
    
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
        
        for retrycnt in range(0, 5):                        # deleting right after deleteVM errors 
            self.Inform("DeleteNSG")
            
            cmd  = 'aliyuncli ecs DeleteSecurityGroup'
            cmd += ' --RegionId %s' % args.region           # us-west-1
            cmd += ' --SecurityGroupId %s' % args.nsg_id    # "sg-rj999tz2kpxehy7obsjn" 
            cmd += " 2> /dev/null"                          # don't show errors 
            
            retcode, output, errval = self.DoCmdNoError(cmd)   # call the Alibaba command, ignore error
            if (retcode == 0):                              # check for error code
                args.nsg_id = ""                            # clear out the id
                break
            trace(3-retrycnt, "Problems deleting security group \"%s\" retry:%d" % (args.nsg_name, retrycnt))
            time.sleep(retrycnt)            
        return retcode
    
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
    # Man page: https://www.alibabacloud.com/help/doc-detail/25499.htm?spm=a3c0i.o51771en.b99.190.3eb7831cDsO1p3
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
            # should move this step outside this VM create so that better reflects 
            # real VM timing?
            
        retcode = self.CreateNSG(args)                              # sets args.nsg_id
        if (retcode != 0):
            return(retcode)
        trace(2, "nsg_id: \"%s\" %s" % (args.nsg_name, args.nsg_id))

            # look up image-name, return region specific image id 
            # TODO: saw this 'aliyuncli ecs describe-images' fail with network error
            #       check if connection to Alibaba is working before calling this
            
        self.Inform("GetImageId")
        if (self.GetImageId(args) != 0):
            return 1
        trace(2, "image_id: \"%s\" %s" % (args.image_name, args.image_id))
        
            # with security group and image id, we can now create the instance
                 
        self.Inform("CreateInstance")   
        cmd  = 'aliyuncli ecs CreateInstance'
        cmd += " --RegionId %s" % args.region                       # us-west-1
        cmd += " --ImageId %s"  % args.image_id                     # m-rj9gjqbdwtwlhtgqjeov" 
        cmd += " --SecurityGroupId %s" % args.nsg_id                # sg-rj999tz2kpxehy7obsjn"
        cmd += " --InstanceType %s" % args.instance_type            # ecs.gn5-c4g1.xlarge
        cmd += " --InstanceName %s" % args.vm_name                  # Name to create VM: "newton-gn5-1gpu" 
        cmd += " --InternetMaxBandwidthOut %d" % args.bandwidth_out # 10
        cmd += " --InstanceChargeType %s" % args.charge_type        # PostPaid 
        cmd += " --KeyPairName %s" % args.key_name                  # baseos-alibaba-siliconvalley
        
        retcode, output, errval = self.DoCmd(cmd)                   # call the Alibaba command
        if (retcode != 0):                                          # check for return code
            error ("Problems creating VM \"%s\"" % args.vm_name)
            return 1
      
            # decode the JSON output
            
        decoded_output = json.loads(output)                         # convert json format to python structure
        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
        args.vm_id = decoded_output['InstanceId']
                       
            # with Alibaba, Instances created via CLI are not automatically given a public IP address.  
            # To assign a public IP address to the instance you just created
            # note -- this may not work immediatly after creating VM. try a few times
            
        args.vm_ip = ""
        for retrycnt in range(0, 4):
            self.Inform("AllocatePublicIpAddress")   
            cmd  = 'aliyuncli ecs AllocatePublicIpAddress'
            cmd += " --RegionId %s" % args.region           # us-west-1
            cmd += " --InstanceId %s" % args.vm_id          # i-rj9a0iw25hryafj0fm4v
            cmd += " 2> /dev/null"                          # don't show errors (the timeout)
            
            retcode, output, errval = self.DoCmdNoError(cmd)  # call the Alibaba command, no errors
            if (retcode == 0):                              # check for error code
                decoded_output = json.loads(output)         # convert json format to python structure
                trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
                args.vm_ip = decoded_output['IpAddress']
                break                                       # got IP we think -- done now
            
            trace(3-retrycnt, "Problems allocating IP address for %s, retry:%d" % (args.vm_id, retrycnt))
            time.sleep(retrycnt)            
          
        if (args.vm_ip == ""):
            error ("Unable to allocating IP address for \"%s\"" % args.vm_name)
            return 1 
        
        # print "args.vm_ip: %s" % args.vm_ip
                                 
            # save vm ID and other fields setup here so don't use them if error later
            # do this again later when we are fully started
            
        self.ArgSaveToFile(args)
 
            # unlike Alibaba or azure, alibaba does not automaticly start an instance
            # when it is created. Start it here to be consistent

        retcode = self.StartVM(args)
                
        return 0
    
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
        if (status == "Running"):
            return 0                                    # already running, simply return
        elif (status == "Stopping" ): 
            buf = "%s is in %s state, can't start running now" % (args.vm_name, status)
            error(buf)
        elif (status == "Stopped" or status == "null"):
            rc = 0                                      # ok to start VM
        else:
            buf = "id %s is in \"%s\" state, not sure can start running" % (args.vm_id, status)
            error(buf)
            
        if (rc != 0):
            return rc                                   # unexpected status
        
        self.Inform("StartVM")   
       
            # start the VM 
            
        cmd = "aliyuncli ecs StartInstance"
        cmd += " --InstanceId %s" % args.vm_id  
        retcode, output, errval = self.DoCmd(cmd)
        
        if (retcode == 0):
            retcode = self.WaitTillRunning(args, "Running", TIMEOUT_1) 
        
        return retcode                                  # 0: succcess, 1: failure
    
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
            
        retcode = self.CheckRunStatus(args, "Running")
        if (retcode != 0):
            error ("Not running")
            return retcode

        self.Inform("StopVM")   
        
        cmd = "aliyuncli ecs StopInstance"
        cmd += " --InstanceId %s" % args.vm_id
        
        retcode, output, errval = self.DoCmd(cmd)
        if (retcode == 0):
            status = self.GetRunStatus(args)
            
                # The instance becomes "Stopping" after a successful API request, 
                # and the instance becomes "Stopped" after it is stopped successfully.
                
            if (status != "Stopping"):
                buf = "Asked VM to stop, but status = \"%s\"" % (status)
                error(buf)
                retcode = 1
            else:
                retcode = self.WaitForRunStatus(args, "Stopped", TIMEOUT_2)
        
        return retcode                  # 0 success, 1 failure
    
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
    def RestartVM(self, args):             # also known as 'RebootInstance' on Alibaba
        ''' Restarts the VM '''
        
        if (self.CheckID(args) == False):
            return 1
        
        retcode = self.CheckRunStatus(args, "Running") 
        if (retcode != 0):
            error ("Not running")
            return retcode
 
        self.Inform("RestartVM")   
       
        cmd = "aliyuncli ecs RebootInstance"
        cmd += " --InstanceId %s" % args.vm_id
        
        retcode, output, errval = self.DoCmd(cmd)
        
                # currently running, with Alibaba, status never becomes "un-running" 
                # durring a restart -- so we check when it FAILS to ping to know if
                # restart actually occured. Then we simply wait till it's back up
                # again - pingable and ssh-able to know it's running
              
        if (retcode == 0):
            if (args.pingable == 1):
                retcode = self.WaitForPing(args, False, TIMEOUT_2)
            else:
                time.sleep(5)           # let VM go down enough so SSH stops (we hope)
                retcode = 0             # fake success, since ping isn't supported
                
            if (retcode != 0):
                error("never went un-pingable. Did VM restart?")
            else:
                retcode = self.WaitTillRunning(args, "Running", TIMEOUT_1) 
        return retcode                   # 0: succcess, 1: failure
    
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
        
            # with alibaba, can only release in instance that is in the Stopped state
            
        self.StopVM(args)
        
            # command to Delete the Instance.
            
        cmd = "aliyuncli ecs DeleteInstance"
        cmd += " --InstanceId %s" % args.vm_id
        
        retcode, output, errval = self.DoCmd(cmd)
            
            # Is error handled ok? What if problems deleting?  -- instance left around? 
            
        if (retcode == 0):
            self.Clean(args)            # remove file with the persistent id, ip address, ..
            self.m_args_fname = ""      # clear name, so won't write back args when done
        return retcode
    
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
        ''' Shows list of running instances of account, independent of the current zone '''
        
        lines_printed = 0
         
        cmd =  "aliyuncli ecs DescribeInstances"
        # cmd += " --RegionId %s" % args.region                     # us-west-1
        cmd += " --PageSize 50"                                     # default is 10, max is 50
        retcode, output, errval = self.DoCmd(cmd)
        if (retcode == 0):
            decoded_output = json.loads(output)
            
            # output looks like (with zero instaces)
            #   {
            #       "TotalCount": 0, 
            #       "PageNumber": 1, 
            #       "RequestId": "67D9A0C9-9393-49E9-B097-68DC739B2A85", 
            #       "PageSize": 10, 
            #       "Instances": {
            #           "Instance": []
            #       }
            #    }

            count = decoded_output["TotalCount"]
            if (count == 0):
                print("# %s: No running instances found" % self.m_class_name )
                return 1
            for idx in range(0, count):
                instance = decoded_output["Instances"]["Instance"][idx]
                if (instance["Status"] == "Running"):
                    if (lines_printed == 0):
                        print("# %s:" % self.m_class_name )
                    print(" %-36s %-16s %10s \"%s\"" % 
                        (instance["InstanceId"],   
                                                    # TODO - add in the region here !
                        instance["InstanceType"],
                        instance["CreationTime"][0:10],
                        instance["InstanceName"]))
                    lines_printed += 1
            
        return 0        # 0 have a list of running instances, 1 fail or empty list
    
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
        cmd =  "aliyuncli ecs DescribeRegions"
        
        retcode, output, errval = self.DoCmd(cmd)
        if ( retcode == 0 ):
            decoded_output = json.loads(output)
            items = len(decoded_output["Regions"]["Region"])           # number of regions 
            for idx in range(0, items):
                name = decoded_output["Regions"]["Region"][idx]["RegionId"]
                mylist.append(str(name))
        return mylist 

     
