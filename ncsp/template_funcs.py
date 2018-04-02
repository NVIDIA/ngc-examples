# template_funcs.py                                          3/23/2018
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# <CSP> specific class Template functions - starting point for new <CSP> development
# Copy this file to your CSP specific name, and fill in functions
#
# The following line is use with the help text to provide info for this
# class without the expense of actually importing the python class.
# 
# HELPTEXT: "Template sample code for not yet developed <CSP>"
#
# 12 Step Program to create a new CSP interface:
# 
#   0) Be able to create/destroy and look at VM's through the CSP's 
#      web interface, and try writing a few hand-built scripts to do
#      basic minipulations on them. 
#   1) Change this text string "<CSP>" to your CSP name 
#      (avoid using a '-' in name, will be future feature)
#   2) Implement CSPSetupOK() 
#   3) Get the 'ShowRunning' function to work, will learn how to create/parse
#      your CSP's interface by doing this
#   4) Implement the Network Security Group functions to first list, then
#      create and delete the NSG's 
#   5) Starting with the CSP's simplest/cheapest VM instance type,
#      implement the "CreateVM" function, and start getting all the csp
#      specific argument parsing in ArgOptions. Get to the point where
#      you have the VM id, and the IP address. 
#   6) Use the output form CreateVM, make sure it's Nam, ID and IP address
#      are saved in the in the args, and use it  to now DeleteVMs
#   7) Implement GetRunStatus to get current run status. Get idea of what 
#      it does while stopping, starting and terminated states 
#   8) Dig into WaitTillRunning, and get ping and ssh working, and 
#      go back an make sure CreateVM is using it correctly 
#   9) Get StopVM. StartVM and RestartVM working
#   10) Run ./stest <CSP> to verify that basic commands are working
#       from a external script, and interface is stable 
#   11) Start playing with options for different InstanceTypes and 
#       number/type of GPUs 
#   12) Run the 'test' command to get full timing on everything
#       and start experimenting with different CPU and GPU parameters
#

import json
import time
import sys
from cspbaseclass import CSPBaseClass
from cspbaseclass import Which
from cspbaseclass import error, trace, trace_do, debug, debug_stop

##############################################################################
# some <CSP> defaults values that will vary based on users 
# 
# default_key_name:     User will need to create their own security key and 
#                       specify it's name here.
# region:               The <CSP> region that they wish to run in. Note that
#                       GPU instances might not be avaliable at all sites
# user:                 Login user name for instance. May be hardcoded by ISP 
#                       based on the image_name being selected. 
##############################################################################

default_key_name            = "my-security_key-name"     # "my-security_key-name"
default_region              = "my-region-name"           # "my-region-name"
default_user                = "my-user-name"             # "my-user-name"

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


default_image_name      = "Generic <CSP> starter AMI*"
default_instance_type   = "type1.small"   # 1gpu, 4gpu and 8gpu instances
default_choices         = ['type1.small', 'type1.med', 'type1.large'] 

TIMEOUT_1 = (60 * 4) # create, start, terminate
TIMEOUT_2 = (60 * 4) # stop, ping
    
##############################################################################
# CSPClass
#
# Cloud Service Provided primitive access functions
##############################################################################    
class CSPClass(CSPBaseClass):
    ''' Cloud Service Provider Class for <CSP> '''
    
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
        ''' quick check to verify our <CSP> command line interface is installed '''

        return 0        # TODO: initial debug -- remove this line.
    
        fullpath = Which("<CSP>cli")  # change to your actual CSP's user command
        if (fullpath == None):
            return 1                # error, not found
        else:
            # TODO: verify network connection to CSP
            # TODO: check login setup correctly
            return 0
     
    ##############################################################################
    # ArgOptions
    #
    # <CSP> specific argument parser. This extends or overrides default argument
    # parsing that is set up in ncsp.py/add_common_options() function
    #
    # All arguments set up here and in the common code are saved/restored from
    # the csp specific args file. See my_class.ArgSave/RestoreFromFile(parser) 
    # in the base class for implementation. 
    #   
    def ArgOptions(self, parser):  
        ''' <CSP> specific option parser '''
        
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
                            help='<CSP> VPC id')
         
            # these override the common/default values from add_common_options
            # with this csp's specific values
            
        parser.set_defaults(image_name=default_image_name);
        parser.set_defaults(key_name=default_key_name)
        parser.set_defaults(user=default_user);
        
            # ping-ability makes starting/stopping more traceable, but this 
            # features is disabled by default, and explicidly needs to be 
            # enabled in the Networks Security Group -- see ICMP option
             
        parser.set_defaults(pingable=1)   # set to 1 if <CSP> instances we created support pings

          
    ###########################################################################
    # ArgSanity
    #
    # CSP class specific argument checks, Called after the argument parser has run
    # on the user options as a hook to verify that arguments are correct
    #
    # 'parser' is the structure returned from argparse.ArgumentParser()
    #
    # Returns    0    success
    #            1    something is wrong, stop
    # 
    def ArgSanity(self, parser, args):
        ''' <CSP> Parser Argument sanity checking '''
        
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
        
        run_state = "unknown"    
         
        self.Inform(run_state)
        return(run_state);

    ###########################################################################
    # GetImageId
    #
    # This might be CSP specific - some CSPs require an ID value for the 
    # template that they use to create a VM from (aws, alibaba), while others
    # (azure) take the full name.
    #
    # For the cases where a name-to-id lookup is required, this is the function
    # that does it. 
    #
    # Name comes from "args.image_name" as a string, and can be given a optional
    # argument by the user
    #
    # This ID value is returned in "args.image_id", and will be something 
    # like "# ami-8ee326f6"
    #
    # Returns:    0    success
    #             1    Name is unknown, no ID foud
    #      
    def GetImageId(self, args):

            # call the function to see of "args.image_name" exists at CSP
            
        # CSP_Specific_ImageNameToIdLookup(args.image_name, args.region)
        rc = 0
        
        if (rc == 0): 
            args.image_id = "ami-unknown-id"  

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
        
        debug(1, "ip: %s keyname: \"%s\"" % (args.vm_ip, args.key_name))
     
            # Very CSP specific - may be picked up in CreateVM
            
        args.vm_ip = "1-2-3-4-imaginary.fake.com"   # main responsibilty of this function
        
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
        
            # dummy list of groups to have something to display
            
        output = []    
        output.append({ "GroupId":"sg_dummy_1", "GroupName":"NSG_Dummy1", "Description":"Desc of Dummy1" })
        output.append({ "GroupId":"sg_dummy_2", "GroupName":"NSG_Dummy2", "Description":"Desc of Dummy2" })
        output.append({ "GroupId":"sg_dummy_3", "GroupName":"NSG_Dummy3", "Description":"Desc of Dummy3" })

            # Have a list of security groups. display them

        items = len(output)         
        for idx in range(0, items):
            print "%2d %-12s \"%s\" \"%s\"" % (idx,
                                               output[idx]["GroupId"], 
                                               output[idx]["GroupName"],
                                               output[idx]["Description"])
        
        if (items == 0):
            return 1                # no NSG's found
        else:
            return 0                # 1 or more NSG's found
              
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
        
        args.nsg_id=None   # if set, we know it exists. 
            
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

        # CSP_Specific_CreateNSG(args.nsg_name, ...)
        rc = 0
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
        if (rc != 0):                                  # check for return code
            error ("Problems creating VM \"%s\"" % args.vm_name)
            return rc 
                
            # get the NSG id of the new security group
            
        args.nsg_id = "sg_FakeNSGID"       
        debug(1, "args.nsg_id <--- %s" % args.nsg_id)
        
            # tag the NSG id if needed (CSP specific)
            
        # CSP_Specific_TagGroup(args.nsg_id, args.nsg_name)

            # Security rules -- make a list of ingress and outgress rules - easy to change
            # slow, but this code is rarely used. understandability is more important
            # note unlike aws/alibaba ingress/outgress both in same rule set - as "Direction" field
            # Rule priority, between 100 (highest priority) and 4096 (lowest priority). Must be unique for each rule in the collection
            # TBD: rule for pinging? -- for aws/alibaba - this is a 'icmp' rule. Not allowed here
            #
            # The actual fields required in this table will be CSP specific
            
        rule = {}
        rule[0] = {"Direction":"Inbound",  "Name":"AllowSSH",  "IpProtocol":"tcp", "ToPort":22,    "FromPort":22,  "Priority":1000, "Description":"For SSH"     }
        rule[1] = {"Direction":"Inbound",  "Name":"HTTPS-in",  "IpProtocol":"tcp", "ToPort":443,   "FromPort":443, "Priority":1010, "Description":"For SSL"     }
        rule[2] = {"Direction":"Outbound", "Name":"HTTPS-out", "IpProtocol":"tcp", "ToPort":443,   "FromPort":443, "Priority":110,  "Description":"For SSL"     }
        rule[3] = {"Direction":"Inbound",  "Name":"DIGITS6",   "IpProtocol":"tcp", "ToPort":5000,  "FromPort":5000,"Priority":1020, "Description":"For NVIDIA DIGITS6" }
        # rule[1] = {"Name":"Ping",    "IpProtocol":"icmp","ToPort":-1,    "FromPort":8,   "Priority":2000, "Description":"To allow to be pinged" }
        
        outer_retcode = 0
        for idx in range(0, len(rule)):
            self.Inform("CreateNSG rule %s.%s" %(args.nsg_name, rule[idx]["Name"]) ) 
            time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
        self.Inform("              ")     
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
           
        # CSP_Specific_DeleteNSG(args.nsg_id)
        rc = 0
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!

        args.nsg_id = None                                  # remove id from args
        
        return(rc)
    
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
            
        # CSP_Specific_Check_Key(args.key_path, args.key_name)
        rc = 0
        if (rc != 0):
            return rc                           # ssh keys not setup correctly

            # security group, create if neeeded, does nothing if already exists
            # consider moving this step outside this VM create to better 
            # reflect the real VM timing?

        self.Inform("CreateNSG")
        if (self.CreateNSG(args) != 0):         # sets args.nsg_id
            return 1
        trace(2, "nsg_id: \"%s\" %s" % (args.nsg_name, args.nsg_id))

            # look up image-name, return region specific image id
 
        self.Inform("GetImageId")
        if (self.GetImageId(args) != 0):
            return 1
        trace(2, "image_id: \"%s\" %s" % (args.image_name, args.image_id))

            # Create the VM
         
        self.Inform("CreateVM")   
        # CSP_specific_CreateVM(args.vm_name, ...)
        rc = 0
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
        if (rc != 0):
            return rc           # unable to create the VM

            # Get the returend information, pull out the vmID and (if possible) 
            # the public IP address of the VM 
                
        args.vm_id = "vm_dummyID"
        args.vm_ip = ""                             # don't have IP until we see VM running
                       
            # CSP Specific - Name your instance if not done from above CreateVM
            
        self.Inform("create-tags")
        # CSP_specific_tagVM(args.vm_id, args.vm_name)
        rc = 0      # success
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!

            # This code will be CSP specific, since some CSP's will not return
            # from their 'createVM' function untill the VM is fully running.
            # Otherwise wait till the instance is up and running, pingable and 
            # ssh-able the "running" string used here will be CSP specific
            #
            # Note that this function major responsiblity is to set args.vm_ip 
            
        if (rc == 0):
            time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
            rc = self.WaitTillRunning(args, "unknown", TIMEOUT_1) 
                        
            # save vm ID and other fields setup here so don't use them if error later
            # actually don't care if it's fully running, (that would be nice) but
            # need to save the VM id here since we need to delete it in any case
        
        self.ArgSaveToFile(args)
         
            # returns 0 only if VM is fully up and running, we have it's public IP
            # and can ssh into it
            
        debug(2, "createVM returning %d" % rc)   
        return rc                                  # 0: succcess, 1: failure
    
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
        
            # check for a valid VM id, returns if it's not set, indicating that
            # either a VM hasn't been created, or it was deleted.
            
        if (self.CheckID(args) == False):               # checks for a valid VM id
            return 1                                    # 
        
            # Get run status and check current state
            # The strings being checked here may be CSP specific. 
            
        status = self.GetRunStatus(args)
        if (status == "running"):
            return 0                                    # already running, simply return
        elif (status == "stopping"):
            buf = "%s is in %s state, can't start running now" % (args.vm_id, status)
            error(buf)
        elif (status == "stopped" or status == "null"):
            rc = 0                                      # ok to proceed
        elif (status == "unknown"):                        
            rc = 0                                      # TEMPLATE DEVELOPMENT CODE - remove this check! 
        else:
            buf = "id %s is in \"%s\" state, not sure can start running" % (args.vm_id, status)
            error(buf)
            
        if (rc != 0):
            return rc                                   # unexpected status
        
            # start the VM 
     
        self.Inform("StartVM") 
        # CSP_Specific_StartVM(args.vm_id, args.region, ...)
        rc = 0
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
        
            # CSP specific - verify that the VM is fully up and running, and that
            # we have it's IP address and can ssh into it.
            # 
            # Some CSP's may return from their StartVM in this state, so this call
            # is optional 
            
        if (rc == 0):
            rc = self.WaitTillRunning(args, "unknown", TIMEOUT_1)  # running
     
            # returns 0 only if VM is fully up and running, we have it's public IP
            # and can ssh into it
               
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
        
            # check for a valid VM id, returns if it's not set, indicating that
            # either a VM hasn't been created, or it was deleted.
            
        if (self.CheckID(args) == False):
            return 1
        
         
            # Checks status. Note that "running" string may be CSP specific
            
        retcode = self.CheckRunStatus(args, "unknown")  # running
        if (retcode != 0):
            error ("Not running")
            return retcode
        
            # Stop the VM
            
        self.Inform("StopVM")  
        # CSP_Specific_StopVM(args.vm_id, args.region)
        rc = 0
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
        
            # The CSP may return from the above command once the request
            # for stopping has been received. However we don't want to 
            # return from this function until we are actually positive that
            # the VM has compleatly stopped. This check will be CSP specific 
            
        if (rc == 0):
            status = self.GetRunStatus(args)
            
                # CSP specific.. 
                # The instance becomes "stopping" after a successful API request, 
                # and the instance becomes "stopped" after it is stopped successfully.
                
            if (status != "unknown"):   # "stopping" - transiant state
                error("Asked VM to stop, but status = \"%s\"" % (status))
                rc = 1
            else:
                rc = self.WaitForRunStatus(args, "unknown", TIMEOUT_2) # stopped
        
            # return 0 only when the VM is fully stopped
            
        return rc                       # 0: succcess, 1: failure
    
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
        
            # check for a valid VM id, returns if it's not set, indicating that
            # either a VM hasn't been created, or it was deleted.
            
        if (self.CheckID(args) == False):
            return 1
        
            # can only restart a VM if it's currently running. 
            # This "running" string may be CSP specific
            
        retcode = self.CheckRunStatus(args, "unknown")   # running
        if (retcode != 0):
            error ("Not running")
            return retcode
        
            # Restart the VM
            
        self.Inform("RestartVM")
        # CSP_SepecificRestartVM(args.vm_id, args.region)
        rc = 0;
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!

            # this code is CSP specific.
            #
            # For instance, on aws after "reset", the status never changes to 
            # any "un-running" value during the reset procss -- so we must poll  
            # via ping to know if restart actually occured. It's pingable, it's
            # not pingable, it becomes pingabe once again. 
            #
            # Then we simply wait till it's back up again - pingable and 
            # ssh-able to know it's running
            #
            # Ability to ping the VM is also CSP specific, and this 'pingable'
            # flag is normally setup in the Network Security Group as a specific rule. 
                
        if (retcode == 0):
            if (args.pingable == 1):
                rc = self.WaitForPing(args, False, TIMEOUT_2)
            else:
                time.sleep(5)       # let VM go down enough so SSH stops (we hope)
                rc = 0              # fake success, since ping isn't supported
                
            if (rc != 0):
                error("never went un-pingable. Did VM restart?")
            else:
                rc = self.WaitTillRunning(args, "unknown", TIMEOUT_1)  # running
                
            # returns 0 only if VM is fully up and running, we have it's public IP
            # and can ssh into it  
                      
        return rc                  # 0: succcess, 1: failure
    
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
        
            # check for a valid VM id, returns if it's not set, indicating that
            # either a VM hasn't been created, or it was deleted.
            
        if (self.CheckID(args) == False):
            return 1
        
        self.Inform("DeleteVM")
        # CSP_SpecificDeleteVM(args.vm_id, args.region)
        rc = 0
        time.sleep(1)           # TEMPLATE DEVELOPMENT CODE - remove this sleep!
        
            # CSP specific..
            #
            # Some CSP's may initiate deletling the VM and then immediatly
            # return while all the work is still occuring in the DataCenter
            #
            # Since we don't want to return until the VM an all the pieces
            # are fully deallocated, wait here. As usual, the status string we
            # are looking for here may be CSP specific, not 'unknown'
            
        if ( rc == 0 ):
            rc = self.WaitForRunStatus(args, "unknown", TIMEOUT_1) # terminated
            
            # CSP specific
            # 
            # Some CSP's like azure and alibaba may have additional resouces like
            # IP address or disks that need to be specificly deleted. Basiclly if we
            # allocated them in Create, we probably need to deallocate them here
            
        # CSP_Sepecific_Dealloc(stuff...) 
            
            # Is error handled ok? What if problems deleting?  -- instance left around? 
            #
            # This cleans out everything in the internal args file, so that user must
            # fully specify any options on the next create. This is the easiest/safest 
            # way to make sure any CSP specific ID parmaters, like the VM id also
            # get cleared... Really Big hammer, but squishes everything fairly
            #
        if (rc == 0):                   # successful so far?
            self.Clean(args)            # remove file with the persistent id, ip address, ..
            self.m_args_fname = ""      # clear name, so won't write back args when done
            
        return rc                       # 0: succcess, 1: failure
    
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
        
        # CSP_SpecificShowRunning(args.region)
        rc = 0
        
        if (rc == 0):
            output = []    
            output.append({ "InstanceId":"i-1234123412341234", "InstanceType":"invented.micro",  "LaunchTime":"2018-02-29", "Description":"Fake image 1234" })
            output.append({ "InstanceId":"i-5678567856785678", "InstanceType":"invented.biggee", "LaunchTime":"2018-02-30", "Description":"Fake image 5678" })

            items = len(output)
            lines_printed = 0
            for idx in range(0, items):
                    print(" %-36s %-16s %10s \"%s\"" % 
                          (output[idx]["InstanceId"],
                           output[idx]["InstanceType"],
                           output[idx]["LaunchTime"],
                           output[idx]["Description"]))
                    lines_printed += 1
                    
            if (lines_printed == 0):
                print("No running instances found in %s" % args.region)
                return 1
        
        return 0
    
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
                
        mylist = ["north", "south", "east", "west"]

        return mylist 
 
##############################################################################
# CSP specific baseclass override functions
#
# These are only here to make template class appear to work before it's 
# attahed to the CSP. REMOVE THEM FOR FLIGHT and let real baseclass functions
# work    
#
#    Ping                    Pings the fake ip address
#    Ssh                     SSH's into VM,
#    WaitForPing             Pings ip address, waits for ping to stop or start
#    WaitTillCanSSH          
#
# REMOVE ALL THESE BASECLASS OVERRIDE FUNCTIONS WHEN TALKING TO A REAL CSP
##############################################################################
   
    def Ping(self, args):
        ''' fake ping into vm '''
       
        time.sleep(1)
 
        print("66 bytes from %s: icmp_seq=0 ttl=999 time=0.0 ms" % args.vm_ip)
        print("66 bytes from %s: icmp_seq=1 ttl=999 time=0.0 ms" % args.vm_ip)
        print("66 bytes from %s: icmp_seq=2 ttl=999 time=0.0 ms" % args.vm_ip)
        
        return 0
        
    def Ssh(self, args, doprint, argv):
        ''' fake SSH into instance, maybe running a command then returning '''

        rc        = 0
        stdoutstr = "fake output"
        stderrstr = ""
        
        time.sleep(1)
                # requested to print it?  (do this for add-hoc cmds from user)
                
        if doprint:
            print stdoutstr
                
            # return the values, so parser code can play with it
            
        return rc, stdoutstr, stderrstr   
 
    def WaitForPing(self, args, state, timeout):
        ''' fake Attempts to Ping, or not to Ping VM, waits till get a response '''
        time.sleep(1)
        return (0)
    
    def WaitTillCanSSH(self, args, sshcmd, timeout): 
        ''' fake Spins till gets a ssh response from the VM '''
        time.sleep(1)
        return(0)

