# gcp_funcs.py                                               3/27/2018
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Google Cloud Service Provider specific functions
#
# HELPTEXT: "Google Cloud Service Provider"
#
# See: https://cloud.google.com/sdk/docs/scripting-gcloud
#

import json
import time
import sys
from cspbaseclass import CSPBaseClass
from cspbaseclass import Which
from cspbaseclass import error, trace, trace_do, debug, debug_stop
import os

##############################################################################
# some gcloud aws defaults values that will vary based on users 
# 
# default_key_name:     User will need to create their own security key and 
#                       specify it's name here.
# region:               The gcp region that they wish to run in. Note that
#                       GPU instances might not be avaliable at all sites
# user:                 Login user name for instance. May be hardcoded by ISP 
#                       based on the image_name being selected. 
##############################################################################


default_key_name        = "my-security-key-name"
default_region          = "my-region-name"
default_user            = "my-user-name"
default_project         = "my-project"
default_service_account = "my-service-account"

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


default_image_project           = "nvidia-ngc-public" 
default_image_name              = "nvidia-gpu-cloud-image"
default_instance_type           = "n1-standard-1"
default_instance_type_choices   = ['n1-standard-1', 'n1-standard-8', 'n1-standard-16', 'n1-standard-32', 'n1-standard-64'] 
default_maintenance_policy      = "TERMINATE"
default_scopes                  = ["https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring.write","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append"]
default_boot_disk_size          = 32
default_boot_disk_type          = "pd-standard" 
default_boot_disk_type_choices  = ["pd-standard"]
default_min_cpu_platform        = "Automatic" 
default_min_cpu_platform_choices= ["Automatic", "Intel Groadwell", "Intel Skylake"] 
default_subnet                  = "default"
default_accelerator_type        = "nvidia-tesla-p100"
default_accelerator_type_choices= ["nvidia-tesla-p100"]
default_accelerator_count       = 0
default_accelerator_count_choices=[0,1,2,4]  # up to 4x P100s

TIMEOUT_1 = (60 * 2) # create, start, terminate
TIMEOUT_2 = (60 * 1) # stop, ping
    
##############################################################################
# CSPClass
#
# Cloud Service Provided primitive access functions
##############################################################################    
class CSPClass(CSPBaseClass):
    ''' Cloud Service Provider Class for gcp '''
    
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
        ''' quick check to verify Google gcloud command line interface is installed '''

        fullpath = Which("gcloud")      # does cli application exist?
        if (fullpath == None):
            return 1                    # error, not found
        else:
            # TODO: verify network connection to CSP
            # TODO: check login setup correctly
            return 0
        
    ##############################################################################
    # ArgOptions
    #
    # gcp specific argument parser. This extends or overrides default argument
    # parsing that is set up in ncsp.py/add_common_options() function
    #
    # All arguments set up here and in the common code are saved/restored from
    # the csp specific args file. See my_class.ArgSave/RestoreFromFile(parser) 
    # in the base class for implementation. 
    #
    def ArgOptions(self, parser):  
        ''' gcp specific option parser '''
        region_list = self.GetRegionsCached()        
        parser.add_argument('--region', dest='region',
                            default=default_region, required=False,
                            choices=region_list,                            # regions change, this is queried output
                            help='region in which to create the VM')
        parser.add_argument('--project', dest='project',
                            default=default_project, required=False,
                            help='is the project in which to create the VM')
        parser.add_argument('--image_project', dest='image_project',
                            default=default_image_project, required=False,
                            help='is the image project to which the image belongs')
        parser.add_argument('--service_account', dest='service_account', 
                            default=default_service_account, required=False,
                            help='service account')
        parser.add_argument('--maintenance_policy', dest='maintenance_policy', 
                            default=default_maintenance_policy, required=False, 
                            help='maintenance_policy')
        parser.add_argument('--subnet', dest='subnet', 
                            default=default_subnet, required=False,
                            help='subnet')        
        parser.add_argument('--scopes', dest='scopes', 
                            default=default_scopes, required=False,
                            help='scopes')
        parser.add_argument('--boot_disk_size', dest='boot_disk_size', 
                            default=default_boot_disk_size, required=False, type=int, 
                            help='disk boot size')
        parser.add_argument('--boot_disk_type', dest='boot_disk_type', 
                            default=default_boot_disk_type, required=False,
                            choices=default_boot_disk_type_choices,
                            help='disk boot type')
        parser.add_argument('--min_cpu_platform', dest='min_cpu_platform', 
                            default=default_min_cpu_platform, required=False,
                            choices=default_min_cpu_platform_choices,
                            help='min_cpu_platform')
        parser.add_argument('--accelerator_type', dest='accelerator_type', 
                            default=default_accelerator_type, required=False,
                            choices=default_accelerator_type_choices,
                            help='GPU accelerator type')
        parser.add_argument('--accelerator_count', dest='accelerator_count', 
                            default=default_accelerator_count, required=False, type=int, 
                            choices=default_accelerator_count_choices,
                            help='Number of GPU accelerators to attach to instance')
        parser.add_argument('--instance_type', dest='instance_type',    # 'size' on azure, use 'instance-type' as common name
                            default=default_instance_type, required=False,
                            choices=default_instance_type_choices,
                            help='VM instance (type) to create')
 
        parser.add_argument('--vpcid', dest='vpcid', 
                            default=None, required=False,
                            help='gcp VPC id')
         
            # these override the common/default values from add_common_options
            # with this csp's specific values
            
        parser.set_defaults(image_name=default_image_name);
        parser.set_defaults(key_name=default_key_name)
        parser.set_defaults(user=default_user);
        
            # ping-ability makes starting/stopping more traceable, but this 
            # features is disabled by default, and explicidly needs to be 
            # enabled in the Networks Security Group -- see ICMP option
             
        parser.set_defaults(pingable=1)   # gcloud instances we created support pings (alibaba not)

          
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
        ''' gcp Parser Argument sanity checking '''
        
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
        
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " instances describe"
        cmd += " --zone \"%s\""             % args.region              # "us-west1-b" 
        cmd += " --quiet"                                              # 'quiet' prevents prompting "do you want to delete y/n?"
        cmd += " \"%s\" "                   % args.vm_name             # note gclould takes VM Name, not a uuid as with aws/azure..     
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                                  # check for return code
            error ("Problems describe VM \"%s\"" % args.vm_name)
            return rc 
        decoded_output = json.loads(output)                            # convert json format to python structure        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
        
        run_state = decoded_output['status'] 
         
            # returns something like "RUNNING" or "STOPPED"
            
        self.Inform(run_state)
        return(run_state);

       
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
        ''' called after 'running' status to get IP. Does nothing for Google '''  
        
            # With google, it looks like the IP address gets changed when restarting
            # from 'stop'. -- SO we must clear it in our stop command !
            # 
            # If we don't have IP run "describe" and get it. 
            # If we have it, simply return it
            
        if (args.vm_ip != ""):      # this ip value should have been set in Create
            # print "GetIPSetupCorrectly: already have ip:%s" % args.vm_ip
            return 0                # so we don't need to get it
        
            # don't have IP value, hopefully VM is in running state and will
            # have a IP that we can get 
        
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " instances describe"
        cmd += " --zone \"%s\""             % args.region              # "us-west1-b" 
        cmd += " --quiet"                                              # 'quiet' prevents prompting "do you want to delete y/n?"
        cmd += " \"%s\" "                   % args.vm_name             # note takes VM Name, not a uuid as with aws/azure..     
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                                  # check for return code
            error ("Problems describe VM \"%s\"" % args.vm_name)
            return rc 
        decoded_output = json.loads(output)                            # convert json format to python structure        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
   
            # ip value that was all that was really needed
            
        args.vm_ip = decoded_output['networkInterfaces'][0]['accessConfigs'][0]['natIP']
     
            # sanity -- is VM id returned same as what we got from Create?
            # got the value for free, might as well check it
            
        vm_id = decoded_output['id']     
        if (vm_id != args.vm_id):
            error ("Sanity - Returned vm_id:%s != vm_id value from create: %s" % (vm_id, args.vm_id))
            return 1      
         
            # check status -- we should be RUNNING
            
        status = decoded_output['status'] 
        if (status != "RUNNING"):
            error ("Shouldn't we be RUNNING? -- current status is \"$status\"")
        
        return(0)
    
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
        
        error ("gcp (google cloud) does not use network security groups")
        return 1                # no NSG's found
                # 1 or more NSG's found
              
    ##############################################################################
    # ExistingSecurityGroup
    #
    # Given a name of a security group in args.nsg_name, this function sees
    # if it currently exists on the CSP
    #
    # Google cloud does not use security groups
    #
    # Returns:   0 do nothing 
    #
    def ExistingSecurityGroup(self, args):
        ''' Does the security group name currently exist ? get it if it does'''

        trace(2, "\"%s\"" % (args.nsg_name))
        error ("gcp (google cloud) does not use network security groups")
        return 0
        
    ##############################################################################
    # CreateSecurityGroup
    #
    # Creates a full network security group by the name of args.nsg_name, saves the 
    # value in args.nsg_id
    #
    # Google cloud does not use security groups
    #
    # Returns:   0 do nothing 
    #
    def CreateSecurityGroup(self, args):
        ''' creates security group. saves it in args.nsg_id '''
        
        trace(2, "\"%s\" %s" % (args.nsg_name, args.nsg_id))
        error ("gcp (google cloud) does not use network security groups")
        return 1

    ##############################################################################
    # DeleteSecurityGroup
    # 
    # Deletes the security group specified at args.nsg_id, and clears that value
    #
    # Google cloud does not use security groups
    #
    # Returns:   0 do nothing 
    #
    def DeleteSecurityGroup(self, args):
        ''' deletes the security group '''
    
        trace(2, "\"%s\" %s" % (args.nsg_name, args.nsg_id))
        error ("gcp (google cloud) does not use network security groups")
        return 1
    
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

            # make sure our persistant IP address is clear
            
        args.vm_ip = ""     
        
            # public ssh key file, builds path from options, checks existance
            # this sets args.key_file to "keyfile.pub"  (better known as "id_rsa.pub")
                    
        retcode = self.CheckSSHKeyFilePath(args, ".pub")
        if (retcode != 0):
            return(retcode)
        keyfile_pub = args.key_file
        # print "keyfile_pub:%s" % keyfile_pub
        
            # however other than in the createVM, the private Key file
            # is required for all the local ssh'ing that we will be doing
            
        retcode = self.CheckSSHKeyFilePath(args, "")
        if (retcode != 0):
            return(retcode)
        
            # ssh key file, builds path from options, checks existance
            # metadata consists of user name, and the "ssh key" file
            #
            # Note that where we pass azure the name of our public ssh key,
            # with Google the entire public key string is passsed in the metadata
            #
            # Example:
            #     metadata = "ssh-keys=newtonl:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDbzMfRh2nXbcwqqVjGvMgOqD3FyJHk4hGdXofLfBAsfQtZQbUg208yWqPEdFgPVyw8zwhd2WAEnaRSK6TmNOok5qgCydpjxbqoCNIfdhfOSFl+T6veiibzQ2UyWolxNPaQ4IPE4FdQsNDM37lsQNCFyZfBaqfbTSmDi5W8Odoqf7E2tfXcLD4gsFpexM4bgK43aaOCp/ekCiJi+Y13MJTw5VmLIdLgJZ/40oMRpK6nZcipbkHkVQEV9mLpTKDLG/xvb7gRzFiXbp4qgF9dWQKqIkfL4UNpcKTjYXqmdt2okoeDGVhQ0AnVM1pHKIyVulV5c17jz7wyj+0UaizAFvSh newtonl@nvidia.com" 
            #
            # Note: The first few characters of the id_rsa.pub file is "ssh-rsa AAAAB3..." 
            #       don't need to explicitly pass in "ssh-rsa" here. Don't over complicate it
            #
        with open(keyfile_pub, "r") as f:
            ssh_rsa_data = f.read();
         
        metadata="ssh-keys=%s:%s" % (args.user, ssh_rsa_data)
        
            # with Google, don't need to create a network security group.
            # mostly inherit defaults from the main scription 

            # neat thing with Google, is that we can specify GPU's at VM init time
            # with other CSPs, number/type of GPU's is a function of the "instance_type"
        
        accelerator_count = 0   # used for delay before ping below
        if (    args.accelerator_type != None and args.accelerator_type != "" 
            and args.accelerator_type != "None" and args.accelerator_count > 0):   
            accelerator = "%s,count=%d" %(args.accelerator_type, args.accelerator_count)
            accelerator_count = args.accelerator_count
               
                # if adding GPUs, add additional info to the VM name
                #
                # Google GPU 'accelerator' types are of form: nvidia-tesla-p100 - too long for VM name which is
                # limited to 61 chars - so strip of last what's after last '-' as name
                #
                # Remember with google, names must all be lowercase numbers/letters
            
            if (args.vm_name.find("gpu") == -1):       # haven't added "gpu" yet
                type = args.accelerator_type[args.accelerator_type.rfind("-")+1:]  
                args.vm_name += "-%dx%sgpu" %(args.accelerator_count, type)
        else:
            accelerator = None      # don't assign gpus   

            # Create the VM
            # NOTE: with gcp, it's not necessary to assign it Network Security Groups
            #       when creating the VM's -- Called "network firewall rules", they are
            #       added later after the VM is created. 
         
        self.Inform("CreateVM")   
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " --project \"%s\" "               % args.project             # "my-project"
        cmd += "instances create \"%s\""          % args.vm_name             # "pbradstr-Fri-2018Mar02-181931"
        cmd += " --zone \"%s\""                   % args.region              # "us-west1-b" 
        cmd += " --quiet"                                                    # reduces noize output
        cmd += " --machine-type \"%s\""           % args.instance_type       # "n1-standard-1" 
        cmd += " --subnet \"%s\""                 % args.subnet              # default
        cmd += " --metadata \"%s\""               % metadata 
        cmd += " --maintenance-policy \"%s\""     % args.maintenance_policy  # "TERMINATE"
        cmd += " --service-account \"%s\""        % args.service_account     # "342959614509-compute@developer.gserviceaccount.com" 
#       cmd += " --scopes %s"                     % args.scopes              # https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring.write","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" \
        if ( accelerator != None ):                                          # optional if we want GPUs 
            cmd += " --accelerator type=%s"       % accelerator              # nvidia-tesla-p100,count=1"
        cmd += " --min-cpu-platform \"%s\""       % args.min_cpu_platform    # "Automatic" 
        cmd += " --image \"%s\""                  % args.image_name          # "nvidia-gpu-cloud-image-20180227" 
        cmd += " --image-project \"%s\""          % args.image_project       # "nvidia-ngc-public" 
        cmd += " --boot-disk-size %d"             % args.boot_disk_size      # 32, in GB
        cmd += " --boot-disk-type \"%s\""         % args.boot_disk_type      # "pd-standard" 
        cmd += " --boot-disk-device-name \"%s\""  % args.vm_name             #  assume same as VM name     
        
            # To break big command into individual options per line for debugging
            # echo $V | sed -e $'s/ --/\\\n --/g' 
    
            # execute the command
            
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                  # check for return code
            error ("Problems creating VM \"%s\"" % args.vm_name)
            return rc 

            # Get the returend information, pull out the vmID and (if possible) 
            # the public IP address of the VM 
            #
            # NOTE: with gcp, IP address is assigned in output from 'create' commmand
            #       don't need to poll for it  (we waited for command to complete instead)
            
        decoded_output = json.loads(output)          # convert json format to python structure        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
                
            # FYI: reason why [0] is user here is that json output format could
            #      possibly supply more than one instance of data. Since our request
            #      is specific to one instance, the [0] grouping is kind of redundant
            
        args.vm_id = decoded_output[0]['id']           # may not actually need the ID, all vm_name based
        args.vm_ip = decoded_output[0]['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        
            # save vm ID and other fields setup here so don't use them if error later
            # actually don't care if it's fully running, (that would be nice) but
            # need to save the VM id here since we need to delete it in any case
        
        self.ArgSaveToFile(args)
        
            # Google has a habbit of reusing the IP addresses, way more than any other
            # csp that I've tested. But since this is an old IP with a new VM, if that
            # IP exists in the known_hosts file, it's going to cause problems when
            # we try to ssh into it (as will happen right away with "WaitTillRunning"
            # Blow away value in known-hosts now. Note that it's also removed when
            # the VM is deleted... but done here on create if forgot or removed some
            # other way.   (TODO: This step needed on other CSPs ? )
            
        self.DeleteIPFromSSHKnownHostsFile(args)
        
            # quick sanity check -- verify the name returned from the create command
            # is the same as we were given

        returned_name = decoded_output[0]["name"]
        # print("name:%s" % returned_name)
        if (decoded_output[0]["name"] != args.vm_name): 
            error ("sanity check: vm name returned \"%s\" != vm_name \"%s\" given to create command" % (returned_name, args.vm_name))
            json.dumps(decoded_output, indent=4, sort_keys=True)
            return 1
         
            # Seeing an error here on gcloud only where 
            # 
            #      1) VM is up in gcloud web page, and can ssh into it there from the web page
            #      2) the first ping in WaitTillRunning succeeds
            #      3) the ssh in WaitTillRunning fails with a timeout
            #      4) any further ping or ssh fails
            #      5) see #1
            #
            # A delay before the first ping seems to workaround the problem 
            # 5 seconds is not enough, got 30% error rates. 10 seconds seems
            # to work at least with"n1-standard-1" instances and no gpus
            #
            # Adding and additional 10 seconds per GPU. Emperical value
            #
            
        delay = 10 + (accelerator_count * 10)
        debug (0, "WORKAROUND: external network connect - sleep for %d seconds before ping" % (delay))
        time.sleep(delay)       # wait a few seconds before ANY command to vm
            
            # Another sanity check -- gcp will return from create only once the
            # vm is up and running. This code here (which comes from aws implementation)
            # wait's till we can ping and ssh into the VM. It should take little
            # time here with gcp, but on the other hand it's a good confidence booster
            # to know that we have checked and hav verified that can ping and ssh into
            # the vm. 
        
        if (rc == 0):
            rc = self.WaitTillRunning(args, "RUNNING", TIMEOUT_1)
          
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
        if (status == "RUNNING"):
            return 0                                    # already running, simply return
        elif (status == "stopping"):
            buf = "%s is in %s state, can't start running now" % (args.vm_id, status)
            error(buf)
        elif (status == "TERMINATED" or status == "null"):
            rc = 0                                      # ok to proceed
        else:
            buf = "id %s is in \"%s\" state, not sure can start running" % (args.vm_id, status)
            error(buf)
            
        if (rc != 0):
            return rc                                   # unexpected status
        
            # start the VM 
     
        self.Inform("StartVM") 
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " instances start"
        cmd += " --zone \"%s\""             % args.region              # "us-west1-b" 
        cmd += " --quiet"                                              # 'quiet' prevents prompting "do you want to delete y/n?"
        cmd += " \"%s\" "                   % args.vm_name             # note takes VM Name, not a uuid as with aws/azure..     
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                  # check for return code
            error ("Problems deleting VM \"%s\"" % args.vm_name)
            return rc 
        
        decoded_output = json.loads(output)          # convert json format to python structure        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
        
            # CSP specific - verify that the VM is fully up and running, and that
            # we have it's IP address and can ssh into it.
            # 
            # Some CSP's may return from their StartVM in this state, so this call
            # is optional 
            
        if (rc == 0):
            rc = self.WaitTillRunning(args, "RUNNING", TIMEOUT_1)  # running
     
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
            
        retcode = self.CheckRunStatus(args, "RUNNING")  # running
        if (retcode != 0):
            error ("Not running")
            return retcode
        
            # Stop the VM
            
        self.Inform("StopVM")  
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " instances stop"
        cmd += " --zone \"%s\""             % args.region              # "us-west1-b" 
        cmd += " --quiet"                                              # 'quiet' prevents prompting "do you want to delete y/n?"
        cmd += " \"%s\" "                   % args.vm_name             # note takes VM Name, not a uuid as with aws/azure..     
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                  # check for return code
            error ("Problems deleting VM \"%s\"" % args.vm_name)
            return rc 
        
        decoded_output = json.loads(output)          # convert json format to python structure        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))
       
            # The CSP may return from the above command once the request
            # for stopping has been received. However we don't want to 
            # return from this function until we are actually positive that
            # the VM has compleatly stopped. This check will be CSP specific 
            
        if (rc == 0):
                        # make sure our persistant IP address is clear - 
                        # google changes IP address after stop. So make sure
                        # the next time we need it, we go and ask for it
            
            args.vm_ip = "" 
            
                        # get status
                        
            status = self.GetRunStatus(args)
            
                # CSP specific.. 
                # The instance becomes "stopping" after a successful API request, 
                # and the instance becomes "stopped" after it is stopped successfully.
                
            if (status != "TERMINATED"):   # "stopping" - transiant state
                error("Asked VM to stop, but status = \"%s\"" % (status))
                rc = 1
            else:
                rc = self.WaitForRunStatus(args, "TERMINATED", TIMEOUT_2) # stopped
        
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
            
        retcode = self.CheckRunStatus(args, "RUNNING")   # running
        if (retcode != 0):
            error ("Not running")
            return retcode
        
            # Restart the VM
            
        self.Inform("RestartVM")
        
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " instances start"
        cmd += " --zone \"%s\""             % args.region              # "us-west1-b" 
        cmd += " --quiet"                                              # 'quiet' prevents prompting "do you want to delete y/n?"
        cmd += " \"%s\" "                   % args.vm_name             # note takes VM Name, not a uuid as with aws/azure..     
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                  # check for return code
            error ("Problems deleting VM \"%s\"" % args.vm_name)
            return rc 
        
        decoded_output = json.loads(output)          # convert json format to python structure        
        trace(3, json.dumps(decoded_output, indent=4, sort_keys=True))

            # this code is CSP specific.
            #
            # on aws after "reset", the status never becomes "un-running" 
            # anytime durring the reset procss -- so we check when it FAILS 
            # to ping to know if estart actually occured. Then we simply wait 
            # till it's back up again - pingable and ssh-able to know it's 
            # running
            #
            # Ability to ping the VM is also CSP specific, and is normally 
            # setup in the Network Security Group as a specific rule. 
                
        if (retcode == 0):
            if (args.pingable == 1):
                rc = self.WaitForPing(args, False, TIMEOUT_2)
                print "Saw Pingable rc=%d" % rc
            else:
                time.sleep(5)       # let VM go down enough so SSH stops (we hope)
                rc = 0              # fake success, since ping isn't supported
                
            if (rc != 0):
                error("never went un-pingable. Did VM restart?")
            else:
                rc = self.WaitTillRunning(args, "RUNNING", TIMEOUT_1)  # running
                
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
        cmd =  "gcloud --format=\"json\" beta compute"
        cmd += " instances delete"
        cmd += " --zone \"%s\""             % args.region              # "us-west1-b" 
        cmd += " --quiet"                                              # 'quiet' prevents prompting "do you want to delete y/n?"
        cmd += " \"%s\" "                   % args.vm_name             # note takes VM Name, not a uuid as with aws/azure..     
        rc, output, errval = self.DoCmd(cmd)       
        if (rc != 0):                                  # check for return code
            error ("Problems deleting VM \"%s\"" % args.vm_name)
            return rc 
        
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
        
        mylist = []
        cmd =  "gcloud --format=\"json\" beta compute instances list"
        rc, output, errval = self.DoCmd(cmd)
        if ( rc == 0 ):
            decoded_output = json.loads(output)
            items = len(decoded_output)                                           # number of instances
            lines_printed = 0
            for idx in range(0, items):
                status = decoded_output[idx]["status"]                            # UP or ??
                if (status == "RUNNING"):
                    name              = decoded_output[idx]["name"]               # "gpu-stress-test"
                    id                = decoded_output[idx]["id"]                 # "6069200451247196266"
                    machineType       = decoded_output[idx]["machineType"]        # "https://www.googleapis.com/compute/beta/projects/my-project/zones/us-central1-a/machineTypes/n1-standard-32-p100x4"
                    cpuPlatform       = decoded_output[idx]["cpuPlatform"]        # "Unknown CPU Platform"
                    creationTimestamp = decoded_output[idx]["creationTimestamp"]  # "2017-08-18T16:21:42.196-07:00"
                    zone              = decoded_output[idx]["zone"]               # "https://www.googleapis.com/compute/beta/projects/my-project/zones/us-east1-d"

                        # pull interesting data out of longer fields that were gathered above
                    
                    launch_time = creationTimestamp[0:10]
                    
                        # VM machine type running on
                        
                    i = machineType.rfind('/')
                    if (i != -1):
                        type = machineType[i+1:]                        # from last '/'
                    else:
                        type = machineType                              # unexpected format, take it all
                        
                        # datacenter region the VM is running in
                        
                    i = zone.rfind('/')
                    if (i != -1):
                        tzone = zone[i+1:]                              # from last '/'
                    else:
                        tzone = zone                                    # unexpected format, take it all
                        
                    if (lines_printed == 0):
                        print("# %s:" % self.m_class_name )
                    print(" %-20s %-16s %-32s %10s \"%s\"" %(id, tzone, type, launch_time, name))
                    lines_printed += 1

            if (lines_printed == 0):
                print("%s: No running instances found" % self.m_class_name )
        
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
                
        mylist = []
        cmd =  "gcloud --format=\"json\" beta compute regions list"
        rc, output, errval = self.DoCmd(cmd)
        if ( rc == 0 ):
            decoded_output = json.loads(output)
            items = len(decoded_output)       # number of regions
            for idx in range(0, items):
                name   = decoded_output[idx]["name"]     # asia-east1
                status = decoded_output[idx]["status"]   # UP or ??
                if (status == "UP"):
                    mylist.append(str(name))             # only include running farms
        return mylist                                    # list is empty if no regions
 

