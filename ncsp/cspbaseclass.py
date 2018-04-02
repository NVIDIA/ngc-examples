# cspbaseclass.py                                            3/23/2018
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Cloud Service Provider base class
#

import os
import sys
import time
import subprocess
import json

g_trace_level = 0          # global trace level, see trace_do and debug funcs

##############################################################################
# common helper functions used throughout

def error(*args):
    ''' error output function '''
    
    print "ERROR: " + ' '.join(args)        # may have trouble if integer in args list

def trace_setlevel(trace_level):
    ''' sets trace_level, returns current value '''
    
    global g_trace_level
    g_trace_level = trace_level             # set global trace level - done 
    return g_trace_level
    
def trace_do(trace_level):                  # trace_level normally >0 may be 0 or even negative.
    ''' return true if supplied 'trace_level' <= current value '''
    global g_trace_level                    # g_trace_level should be >= 0 
    # print ("trace_level:%d g_trace_level:%d" %(trace_level, g_trace_level))
    return (trace_level <= g_trace_level)   # true if func trace level <= global trace level

def trace(trace_level, *args):
    ''' a debugging function, prints out line and stack trace if supplied trace_level <= current '''
    
    if (trace_do(trace_level) == True):
        caller_frame = sys._getframe(1)     # caller stack frame
        print "TRACE:%d:%s %s" % (trace_level, caller_frame.f_code.co_name, args)
        
def debug(trace_level, *args):              # like trace, but with no stack trace
    ''' a debugging function: prints out arg if supplied trace_level <= current '''
    
    if (trace_do(trace_level) == True):
        print "%s" % args

def debug_stop(*args):
    ''' a debugging function: prints out arguments and exits '''
    
    caller_frame = sys._getframe(1)           # caller stack frame
    print "DEBUG_STOP:%s %s" % (caller_frame.f_code.co_name, args)
    sys.exit(1)
       
def Which(program):
    ''' same as Linux 'which' command, returns full path to executible or None if not found '''
    
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None
    
##############################################################################
# CSPBaseClass
#
# Cloud Service Provided common class helper functions
##############################################################################    
class CSPBaseClass:
    ''' Common functions for all Class '''
    
        # Some generic class helper functions
        
    def __init__(self, name, module_path):
        ''' Class Initialization '''
          
        self.m_class_name       = name
        
            # file locations, all under persistent $HOME directory on machine
 
        homedir = os.path.expanduser("~")
        partial = "%s/ncsp/" % homedir

        if os.path.isdir(partial) == False:
            os.mkdir(partial)
            
        partial += self.m_class_name
        if os.path.isdir(partial) == False:
            os.mkdir(partial)

        self.m_save_path        = partial + "/data/"
        self.m_log_path         = partial + "/logs/"
        
        if os.path.isdir(self.m_save_path) == False:
            os.mkdir(self.m_save_path)
                 
        if os.path.isdir(self.m_log_path) == False:
            os.mkdir(self.m_log_path)

            # full path names to various files we create and use
            
        self.m_cmd_fname        = self.m_log_path  + "cmds"
        self.m_args_fname       = self.m_save_path + "args"
        self.m_regions_fname    = self.m_save_path + "regions"
        self.m_module_path      = module_path       # path where the modules are 
        self.m_inform_pos       = 0                 # used for spinner
        
            # append to the logfile header
    
        thetime = time.strftime("%c", time.localtime())
        self.Log("\n#\n# %s\n#\n" % thetime)
        
    def CheckSSHKeyFilePath(self, args, extension):
        ''' Builds ssh key file from options, verifies existance '''
        
            # key_name and key_key is user defined,  is 
            # Unlike a unix shell, Python does not do any automatic path expansions like '~'
            # Something like "~/.ssh/my-security-key.pem"
            
        key_file = "%s%s%s" % (args.key_path, args.key_name, extension)  
        
            # Produces  "/home/<username>/.ssh/my-security-key.pem"
            
        key_file = os.path.expanduser(key_file)                

        if os.path.exists(key_file):
            args.key_file = key_file
            return 0            # success
        else:
            error("Could not find public keyfile \"%s\" -- Aborting" % key_file)
            return 1            # check proper error response??
        
    def Log(self, string):
        ''' simple time stamping log function '''
        
        with open(self.m_cmd_fname, "a") as f:
            f.write(time.strftime("%Y%m%d.%I%M%S: ", time.localtime()))
            f.write(string)
            f.write("\n")
        f.close()

    def ArgSaveToFile(self, args):
        ''' save all the parser default arguments to a file '''
        
        if (self.m_args_fname == "" ):
            return 0                # no file name, used in deleteVM to say don't write back
        
        vargs = vars(args)          # get whatever "namespace(..)" off args
        trace(2, vargs)

        with open(self.m_args_fname, "w") as f:
            json.dump(vargs, f)     # save dictionary as a json file
        return 0

    def ArgRestoreFromFile(self, parser):
        ''' restores default args in parser if file containing them exists '''
        
        if (self.m_args_fname == "" ):
            return 
         
        # pull in saved key,values from file, append to provided vargs
        if os.path.exists(self.m_args_fname):
            mydict = []   
            with open(self.m_args_fname, "r") as f:
                mydict = json.load(f);
                debug(2, json.dumps(mydict, indent=4, sort_keys=True))
                
                for item in mydict.items():
                    kv = {item[0] : item[1]}        # convert key,value to single item dictionary
                    parser.set_defaults(**kv)       # update default value for key 
            return 0
        return 1
 
    
    def ArgShowFile(self):
        ''' displays peristent args file '''
        
        print ("# %s" % self.m_args_fname)
        if os.path.exists(self.m_args_fname):
            with open(self.m_args_fname, "r") as f:
                mydict = json.load(f);
                print json.dumps(mydict, indent=4, sort_keys=True)
        else:
            print ("# does not exist")
        
        return 0
    
    def Clean(self, args):
        ''' erases cached args and other persistent file '''
        
            # prevent problem if host reuses the IP address in a later VM
            
        self.DeleteIPFromSSHKnownHostsFile(args)

            # remove the persistent args
            
        if (self.m_args_fname != "" ):
            if (os.path.exists(self.m_args_fname)):
                os.remove(self.m_args_fname);  
                
            # remove cached list of CSP's regions
            
        if (self.m_regions_fname != "" ):
            if (os.path.exists(self.m_regions_fname)):
                os.remove(self.m_regions_fname); 
        
        return 0
                         
    def Inform(self, info):
        ''' spinner busy clock thing for long wait items '''
        
        if (True):     # depends on trace level?
            myclock = [ "|", "/", "-", "\\" ] 
            
            if (self.m_inform_pos > 3):
                self.m_inform_pos = 0       # restart back at beginning of 'clock' array
                
                # azure has a space char before the clock char for the prompt to sit on
                # emulate that look here
                
            sys.stdout.write(" %s %s ..                        \r" % (myclock[self.m_inform_pos], info))
            if (trace_do(1)):
                sys.stdout.write("\n")      # if tracing, go to new line
            sys.stdout.flush()
            self.m_inform_pos += 1
        else:
            print info    
            
    def ClassName(self):
        ''' return name of the class (azure, aws, ali...)'''
        
        return self.m_class_name
    
    def CheckID(self, args):
        ''' checks that the VM id exists -- if doesn't, don't know if we have a running vm '''
        
            # Note that string "None" (as a string) sneaks into arg file after
            # delete. Need to check for it in addition to None (the object)
            
        if args.vm_id is None or args.vm_id == "" or args.vm_id == "None":
            error("No %-5s vm currently defined" % self.m_class_name);
            return False
        else:
            return True
       
    def DoCmdNoError(self, cmd):
        ''' Blocking command -- returns command output, doesn't report error'''

        debug(1, cmd)
        
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, errval = child.communicate()                # returns data from stdout, stderr
        
        debug(3, output)
        
        return (child.returncode, output, errval)           # pass back retcode, stdout, stderr
  
    def DoCmd(self, cmd):
        ''' Blocking command -- returns command output'''
 
        retcode, output, errval = self.DoCmdNoError(cmd)    # Do the work
        
        if retcode != 0:                                    # report any error
            if (trace_do(1) == False):                      # if we have tracing on >=1, already printed cmd
                print("cmd:  %s" % cmd)
            print("errval: \"%s\" child.returncode %d" % (errval, retcode))  # debug

        return (retcode, output, errval)                    # pass back retcode, stdout, stderr
    
        # DeleteIPFromSSHKnownHostsFile
    #
    # the CSP's may (will) eventually reuse the same IP address for new VMs. 
    # However the new VM's will have a different ECDSA key, and you will 
    # receive nasty messages from ssh when you try to talk to this new
    # VM if key saved in ~/.ssh/known_hosts for this IP has not been
    # removed.. 
    #
    # This function should be called when the VM is deleted to avoid this
    # type of unnecessary problem from confusing the user
    #
    def DeleteIPFromSSHKnownHostsFile(self, args):
        ''' reused ip's for new vm's cause first-time ssh issues, remove from known-hosts file '''
        
        if (args.vm_ip != None and args.vm_ip != "None" and args.vm_ip != ""):
            
                # use 'ssh-keygen -R <ipaddr>'  to remove offending value
                # value are hashed? on linux, not direct IP address
                
            cmd="ssh-keygen -R %s 2> /dev/null" % args.vm_ip            
            self.DoCmd(cmd)     # not critical if it fails... 
        return 0


    # Ssh
    #
    # SSH should not Cloud Service Provider dependent, so it's common function 
    # passes back tripple: 'returncode, stdoutstr, stderrstr' in all cases
    # if 'print' is set, locally prints (used when add-hoc user ssh cmds given)
    # argc is from the commands, which includes either historical or new vm_ip addr
    # args is directly from the typed in commmand string, and is what we want VM to do 
    #
    # Returns: retcode, stdoutstr, stderrstr
    #
    def Ssh(self, args, doprint, argv):
        ''' SSH into instance, maybe running a command then returning '''
        
            # check for a valid VM id, returns if it's not set, indicating that
            # either a VM hasn't been created, or it was deleted.
            
        if (self.CheckID(args) == False):               # checks for a valid VM id
            return 1 
   
        stdoutstr = ""
        stderrstr = ""
        retcode   = 1     # assume error, until this gets set to 0
    
        if (args.vm_ip == ""):
            return retcode, stdoutstr, stderrstr
        
        cmd = "ssh" 
        # cmd += " -oStrictHostKeyChecking=no"  # did when started earler, should not be needed here
            
            # ssh keyfile -- which may not be needed in all cases. Only put it here (with -i) 
            # if it's supplied. 
            
        if (args.key_file != None and args.key_file != ""):
            cmd += " -i %s " % args.key_file       
            
            # user name and IP 
            
        cmd += " %s@%s"  % (args.user, args.vm_ip) # 'user' name can't have a /n in string! 
            
            # add additional user supplied args to command string
                    
        llen = argv.__len__()
        if llen == 0:
            subprocess.call(cmd, shell=True)
        else:
            # print "llen=%d" % llen
            
            cmd += " "       # make sure there's space after last token on cmd string
            
                # convert from array back to a string
                
                # NOTE: the main usage of this code if from argv[] string array 
                #       from the command line. Funky usage when using ssh commands 
                #       internally (and funky means that we have to give this function
                #       an initialized argv[] string array). But doing this allows
                #       only one function to be created... 
                
            for i in range(0, llen):
                cmd += argv.__getitem__(i)
                cmd += " "
           
                # common errcode, stdout, stderr return from running the command
               
            retcode, stdoutstr, stderrstr = self.DoCmd(cmd)
            
                # requested to print it?  (do this for add-hoc cmds from user)
                
            if doprint:
                print stdoutstr
                
            # return the values, so parser code can play with it
            
        return retcode, stdoutstr, stderrstr
    
    def Ping(self, args):
        if (args.pingable == 0):
            error("'%s' interface does not currently support ping" % self.m_class_name)
            return 1  
              
            # check for a valid VM id, returns if it's not set, indicating that
            # either a VM hasn't been created, or it was deleted.
            
        if (self.CheckID(args) == False):               # checks for a valid VM id
            return 1 
        
        if (args.vm_ip == "" or args.vm_ip == None or args.vm_ip == "None"):
            error("No IP is assigned to %s" % args.vm_name)

            # ping a few times, all output goes into 'output' or 'errval'
            
        cmd = "ping -t 3 -c 3 %s" % args.vm_ip
        # print cmd
        retcode, output, errval = self.DoCmd(cmd)
             
            # report what was found 
        if (retcode == 0):
            print "ping to %s was successful" % args.vm_ip
        else:
            error("ping to %s failed" % args.vm_ip)
            print output
            print errval
        return retcode
        
    def CheckRunStatus(self, args, value):
        ''' Sees if the current run-status is value '''
        
        status = self.GetRunStatus(args)
        # print("CheckRunStatus-status:%s looking for-value:%s" % (status, value))
        if (status.lower() == value.lower()):   # case insensitive
            return 0     # 0 for status=='value' success, 1 for something else
        else:
            return 1     # not what we want
    
    def WaitForRunStatus(self, args, value, timeout):
        ''' waits for status state to be value '''
        
        now   = time.time() # floating point number
        end   = now + timeout
        rc    = self.CheckRunStatus(args, value)
        
        while (rc != 0 and now < end): 
            time.sleep(0.5)                             # Wait time
            rc  = self.CheckRunStatus(args, value)      # want to be value, returns 0 if is
            now = time.time()                           # floating point number for time

        if (rc != 0):
            error ("Timeout " + value)
            
        return rc       # True for got status=='value' within timeout, False if not
    

    def WaitForPing(self, args, state, timeout):
        ''' Attempts to Ping, or not to Ping VM, waits till get a response '''
        ''' Note: VM's may not support ping see args.pingable flag '''    
        
        now   = time.time()         # floating point number
        end   = now + timeout
        ip    = args.vm_ip
        cmd   = "ping -c 1 -W 1 "
        cmd  += ip
        
        retcode, output, errval = self.DoCmdNoError(cmd)
        
        if (retcode == 0):
            pingable = True   # wait till can ping
            info     = "wait for not ping-able"
        else:
            pingable = False
            info     = "wait for ping-able"
       
            # can check here if pingable (state == True) or not-pingable (state == False)
            
        while (pingable != state and now < end): 
            self.Inform(info)
            time.sleep(0.5)                     # Wait time
            
            retcode, output, errval = self.DoCmdNoError(cmd)
            if (retcode == 0):
                pingable = True   # wait till can ping
            else:
                pingable = False            
            now = time.time() # floating point number
        
        if (pingable == state):     # response from ping-cmd is expected state
            # print "PING SUCCESSFUL: \"%s\"" % cmd
            return(0)               # 0 returned for success -- is pingable
        else:
            if (now > end):
                error ("Ping: Timeout %s" %(cmd))
            else:
                error ("Ping: Failed \"%s\"\n" %(cmd, errval))
            return(1)               # 1 returned for failure, not pingable
    
    def WaitTillCanSSH(self, args, sshcmd, timeout): 
        ''' Spins till gets a ssh response from the VM '''
        
        # Ssh-ability is not really poll-able -- doesn't return till either timeout
        #        or success, meaning that there is no Inform notifier updates
        #        occuring if booting, and waiting for OS to come up..
        # The best solution is to have ping response to VM working, so 
        # this step really isn't an issue
        
        now   = time.time()         # floating point number
        end   = now + timeout
        
        cmd   = "ssh -oStrictHostKeyChecking=no "   # allow to be added to /.ssh/known_hosts
        cmd  += "-o ConnectTimeout=2 "              # quicker timeout, see clock move
        
            # ssh keyfile -- which may not be needed in all cases. 
            # Only put it here (with -i) if it's supplied. 
            
        if (args.key_file != None and args.key_file != ""):
            cmd += " -i %s " % args.key_file
        cmd  += "%s@%s " % (args.user, args.vm_ip)  # space after ip, before following cmd
        cmd  += sshcmd                              # the ssh command we want to run
        cmd  += " 2> /dev/null"                     # don't want to see stderr msgs
            
        retcode, output, errval = self.DoCmdNoError(cmd)
       
        cnt = 0
        while (retcode != 0 and now < end): 
            cnt = cnt + 1
            self.Inform("wait for ssh-able %d" % cnt)
            time.sleep(1)                     # Wait time
            retcode, output, errval = self.DoCmdNoError(cmd)
            now = time.time() # floating point number
        
        if (retcode == 0):      # response from ping-cmd is 0 if able to ping
            # print "SSH  SUCCESSFUL: \"%s\"" % cmd
            return(0)           # 0 returned for success
        else: 
            if (now > end):
                error ("SSH Timeout: \"%s\"" %(cmd))
            else:
                error ("SSH Failed: : \"%s\"\n%s" %(cmd, errval))
            return(1)           # 1 returned for timeout, can't ssh
    
    def WaitTillRunning(self, args, value, timeout):
        ''' called after launch, waits till can get IP from running instance '''
        ''' value is "Running" for alibaba, or "running" for aws -- case dependent '''
        
            # initially right after 'start', status will be 'pending'
            # wait till we get to a status value of 'running'
               
        rc = self.WaitForRunStatus(args, value, timeout)  # Has different cases/values for CSP! 
        if (rc != 0):
            error("Did not get run status writing timeout")
            return rc                               # fail, not runable, return 1
        
            # after the CSP says we are "running", the next thing we will need 
            # is the IP adresss of the VM. This may be setup in create, or we may
            # need be able to query for it from the CSP as is needed in aws. In any
            # case, don't leave this step till have the IP address to the VM. 
            # NOTE: the VM is not up enough to respond to the IP, it's still booting
            
        rc = self.GetIPSetupCorrectly(args)     # CSP specific way to get IP address 
        if (rc != 0):                           # may have been done in Create for some CSPs
            return rc
        
            # make sure we can ping -- this takes a few seconds after the kernel boots 
            # for the network to come up to return pings. 
            # pinging might not be enabled in network config for CSP
        
        if (args.pingable != 0):
            rc = self.WaitForPing(args, True, timeout)
            if (rc != 0):
                return rc                      # returns 1 - not pingable
        
            # See if we can ssh this beast. Note that this might be the first time
            # we do so with the given IP, so the known_host files may not have it.
            # this function handles that so user isn't prompted.
            #
            # spins, waiting for SSH to work

        rc = self.WaitTillCanSSH(args, "uname -a", timeout)
        if (rc != 0):
            return rc                          # returns 1 - could not ssh
        
        return 0                               # 0: success, running - 1:fail, not running
    
    def KernelBootTime(self, args):
        ''' ask VM for kernel boot time '''
        kernel = 0
        user   = 0
        total  = 0
        
        rc = self.WaitTillCanSSH(args, "uname -a", 10)
        if (rc != 0):
            error("Could not ssh")
            return rc
        
            # Use "systemd-analyze" to grab the kernel boot time from the VM
            # Greping through syslog is error-prone, especially if it's booted
            # multiple times, or bootup ordering changes. 
            #
            # NOTE: embedded qoutes are fun here -- requires something like this
            #    (example):   "\"grep \\\"[1]: Startup finished\\\" /var/log/syslog | tail -n 1\""
 
        cmd = []        # might there be a a better way to do this?  (self.Ssh takes array of strings)
        cmd.append("\"systemd-analyze\"")
        retcode, stdoutstr, stderrstr = self.Ssh(args, False, cmd)
        
            # stdoutstr should be:
            #   Startup finished in 3.582s (kernel) + 5.972s (userspace) = 9.555s
            
        if (retcode == 0):      # successfull ssh
            tmpary = stdoutstr.split()   # ['Startup', 'finished', 'in', '3.582s', '(kernel)', '+', '5.972s', '(userspace)', '=', '9.555s']
            if tmpary[4] != "(kernel)" or  tmpary[7] != "(userspace)":
                error("not expected output from systemd-analyze:" + stdoutstr)
                retcode = 1
            else:
                kernel = tmpary[3]
                user   = tmpary[6]
                total  = tmpary[9]
                # print kernel + user + total
        else:
            print stderrstr     # unhappy
            
        return retcode, kernel, user, total        # 4 values
         
    def Show(self, args):
        ''' Shows detailed information about the vm -- name, size, status... '''
        
        print ("%-10s \"%s\" %s %s" % ("vm", args.vm_name,  args.vm_id, args.vm_ip))
        print ("%-10s \"%s\" %s" % ("nsg", args.nsg_name, args.nsg_id))
        return 0

    def Status(self, args):
        ''' Shows run/halt status of VM '''
        
        if (self.CheckID(args) == False):
            return 1
        
        status = self.GetRunStatus(args)            # prints status output via Inform() 
        print("\n")
        return 0
    
    def GetRegionsCached(self):
        ''' returns the regions list for csp, cached to file first time '''
        
                    # if we have done this before, the regions are cached in a file
        try:
            with open(self.m_regions_fname, "r") as f:
                mylist = json.load(f);
        except:
            mylist = self.GetRegions()              # csp dependent query function
            with open(self.m_regions_fname, "w") as f:
                json.dump(mylist, f)

        return mylist                               # return list
        
    def ShowRegions(self, args):
        ''' shows the regions supported by csp ''' 
        
        mylist = self.GetRegionsCached()
        for region in mylist:
            print ("  %s" % region)
        return 0
    
    def ShowIP(self, args):
        ''' shows the public IP address for the VM '''
        if (self.CheckID(args) == False):
            return 1
        print args.vm_ip 
        return 0
          
    ##############################################################################
    # Top level Network Security Group (NSG) command functions - CSP independent
    #
    # The NSG is created per-user, not per VM instance, under the assumption that
    # it doesn't need to change for the different types of VM's that the user
    # creates. See how the args.nsg_name field is defined in add_common_options()
    # to understand how the this could be changed.
    #
    # NOTE: it's up to the csp specific deleteVM implementations to decide to
    #       delete the Network Security Group or not. 
    ##############################################################################
    
    def ShowNSGs(self, args):
        return(self.ShowSecurityGroups(args))
        
    def CreateNSG(self, args):
        ''' returns security group, creates/queries if it does not currently exist '''    
            
        self.Inform("CreateNSG")
                 
            # Do we have ID from user or from persistent?
            
        if (args.nsg_id != "" and args.nsg_id != None and args.nsg_id != "None"):
            trace(2, "Security group \"%s\" exists: %s" % (args.nsg_name, args.nsg_id))
            return 0
        
        if (args.nsg_name == ""):
            error("Network Security Group name is \"\" - aborting")
            sys.exit(1)
            
            # Does it exist by name? Don't need to create it if so
           
        self.Inform("ExistingNSG")                            
        if (self.ExistingSecurityGroup(args) == 0):
            trace(2, "Security group \"%s\" found: %s" % (args.nsg_name, args.nsg_id))
            return 0
        
            # Create a new security group
            # The ID is written to args.nsg_id
                 
        self.Inform("CreateNSG")                            
        rc = self.CreateSecurityGroup(args)
        if (rc != 0):
            return rc
        trace(2, "Created Security Group \"%s\": %s" % (args.nsg_name, args.nsg_id))
        return 0
        
    def DeleteNSG(self, args):
        ''' deletes security group if it currently exists '''
        
        rc = 0
        
            # Do we have ID from user or from persistent?
        self.Inform("DeleteNSG")   
        if (args.nsg_id != "" and args.nsg_id != None and args.nsg_id != "None"):
            rc = self.DeleteSecurityGroup(args)
        elif (args.nsg_name != "" and args.nsg_name != None and args.nsg_name != "None"):
            if (self.ExistingSecurityGroup(args) == 0):     # Does it exist by that name?
                rc = self.DeleteSecurityGroup(args)         # above call set args.nsg_id
        
        return rc
