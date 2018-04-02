#!/usr/bin/python
# csp                                                        3/22/2018
#
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved. 
#
# Top level generic CSP (Cloud Service Provider)     interface 
#
# Demonstrates how to use python to create a consistent interface 
# across multiple different cloud providers. Shows code for creating, starting, 
# deleting and setting up ssh commands and sessions in those VM's  
# 
# csp.py              outermost command interface 
# cpsbaseclass.py     the main class, and CSP independent functions 
# <csp>_funcs.py      contains CSP specific code 
#
# CSP interfaces are dynammicly added if they are found in same directory
# as this application. File name is "<csp>_funcs.py". Currently supported
# csp types are:  
#
#    ali        Aliababa
#    aws        Amazon
#    azure      Microsoft Azure
#
# Basic commans:
#     csp help                      # basic help, lists which csps currently exist
#     csp <csp> createVM            # create security groups and VM with default settings
#     csp <csp> ssh [cmd...]        # ssh's and optionally runs cmd on VM
#     csp <csp> deleteVM            # destroy VM
#     csp <csp> test                # simple timing test of all the major csp commands
#     csp help                      # overall command help
#     csp <csp> --help              # csp specific help
#
# Configuration parameters, VM ids, IP address, .. etc are save in persistent
# file, and updated as needed. See showArgs and cleanArgs commands
#
# csp <csp> --trace [0..3] turns on some minimal command/return tracing
#
import argparse
import time
import sys
import os
from cspbaseclass import error, trace, trace_do, trace_setlevel, debug_stop

###############################################################################
# simple timing class
###############################################################################

class TimeClass:
    ''' simple timing class '''
    
    def __init__(self, outer_loop_value):
        self.m_test_start = self.Now();
        self.m_log_data=[] 
        self.m_log_idx=0
        self.m_instanceTypeName="no name set yet"
        self.m_outer_loop_value=outer_loop_value    # which outer-loop is this create/delete cycle
        
    def SetInstanceTypeName(self, instanceTypeName):
        self.m_instanceTypeName = instanceTypeName   # we loose this before it's printed
    
    def InstanceTypeName(self):
        return(self.m_instanceTypeName)
    
    def Now(self):                      # current time, as a floating point number
        ts = time.time()        
        return(ts)
    
    def Diff(self, te, ts):             # te is end, ts is start -- what's the difference?
        diff = te - ts;
        return diff
    
    def Start(self):                    # return start time
        ts = self.Now()
        return ts
    
    def End(self, taskname, loop, ts):  # called at end, given start time and name
        te = self.Now()
        diff = self.Diff(te, ts)
        name = taskname
        name += '.'
        name += str(loop)
        print "%2s %-20s %8.2f" % ("", name, diff)
        
            # simple list containing "name" and "diff" fields
            
        self.m_log_data.append((name, diff))
        self.m_log_idx += 1
    
    ###############################################################################
    # reporting functions 
    ###############################################################################
   
    def SummaryInit(self, my_class, args):
        ''' Summary initialization - conclusions/sums '''
        self.m_test_end = self.Now();
        self.m_test_diff = self.Diff(self.m_test_end, self.m_test_start)     # overall test time
        
    def SummaryReport(self, my_class, args):
        ''' Summary report to display at end of job'''
        print ""
        print "#---------------------------------------------------------"
        print "# %s %s image:%s" % (my_class.m_class_name, args.instance_type, args.image_name)
        print ("# loop %d of %d start/stop/del:%d %s\n"  % 
                                               (self.m_outer_loop_value+1, args.outer_loop_cnt,  
                                                args.inner_loop_cnt, 
                                                time.strftime("%Y%b%d-%a-%H%M", time.localtime())))
        print "#"
        print ""
        for idx in range(0, self.m_log_data.__len__()):
            val = self.m_log_data[idx]
            print "%2d %-20s %8.2f" % (idx, val[0], val[1])
        print "%2s %-20s %8.2f" % ("", "overall", self.m_test_diff) # done after InitSummary called
        print ""

    def SummaryLog(self, my_class, args):
        ''' Summary log - intent is to easily cut/paste to spreadsheet table '''
        
        with open(my_class.m_log_path + "test", "a") as f:   # test summary file
            f.write( "\n" )
            f.write( "# %s loop %d of %d start/stop/del:%d\n"  %
                                                (my_class.m_class_name, 
                                                 self.m_outer_loop_value+1, args.outer_loop_cnt,  
                                                 args.inner_loop_cnt))
            f.write( "%s\n"    % time.strftime("%Y-%m-%d", time.localtime()))
            f.write( "%s\n"    % args.image_name)                                
            f.write( "%s\n"    % (args.instance_type))
            for idx in range(0, self.m_log_data.__len__()):
                val = self.m_log_data[idx]
                f.write( "%.2f\n" % val[1])
            f.write( "%.2f\n" %self.m_test_diff)  # done only after InitSummary called
        
        
##############################################################################
# generic timing test, how long does it take to do basic VM features? 
       
def time_test(my_class, outer_loop_value, args):
    ''' generic CSP vm create/stop/start/reset/delete timing test '''
    
    my_time = TimeClass(outer_loop_value)

        # create/get id for Network Security Group
        
    ts = my_time.Start()
    rc = my_class.CreateNSG(args)
    my_time.End("createNSG", 0, ts)
    if (rc != 0):
        return rc
    
    ts = my_time.Start()
    rc = my_class.CreateVM(args)        # args is from parser.parse_args(argv)
    my_time.End("createVM", 0, ts)
    if (rc != 0):
        error ("createVM returned %d, stopping test" % rc)
        return rc
    
        # type of VM created - size, number of CPUs, GPUs... defined by name
        
    my_time.SetInstanceTypeName(args.instance_type)
    
        # start/stop/restart loops, default is 2
        
    loop = 0                     # initialize value if loop isn't run (loop_cnt = 0)
    for loop in range(0, args.inner_loop_cnt):
        ts  = my_time.Start()
        my_class.StopVM(args)
        my_time.End("stopVM", loop, ts)
        
        time.sleep(5)
              
        ts  = my_time.Start()
        my_class.StartVM(args)
        my_time.End("startVM", loop, ts)
 
        time.sleep(5)
       
        ts  = my_time.Start()
        my_class.RestartVM(args)
        my_time.End("restartVM", loop, ts)
    
        time.sleep(5)
        
        # delete vm
    
    ts = my_time.Start()   
    my_class.DeleteVM(args)
    my_time.End("deleteVM", loop, ts)
    
        # delete Security Group
        
    time.sleep(5)           # for alibaba, need a delay before trying to delete NSG
                            # immediatly after deleting the VM -- the deleteNSG fails 
    ts = my_time.Start()   
    my_class.DeleteNSG(args) 
    my_time.End("deleteNSG", loop, ts)
    
        # delete the persistent information - VM/NSG id, name..  
        
    my_class.Clean(args)
    
        # final report
        
    my_time.SummaryInit(my_class, args)         # caculate any conclusions..
    if (args.summary_report != 0):              # extra possiblly redundant
        my_time.SummaryReport(my_class, args)   # but nicely formatted user report
    my_time.SummaryLog(my_class, args)          # cut/pasteable format in log file
    
        # successful return
        
    return 0

# get_csp_list
#
# Returns the list of all the csp's that we support (I.E all the files that
# end with _funcs.py). 
#
# internal function
def get_csp_list():
    ''' returns a list of supported csps -- not including 'template' '''
    
    csp_list=[]
    import glob
    filelist = glob.glob(module_path + "*_funcs.py")    # ['test1/ali_funcs.py', 'test1/azure_funcs.py', ...
    for name in filelist:
        pos0 = name.rfind("/")
        pos1 = name.rfind("_funcs.py")
        csp_name = name[pos0+1:pos1]       # remove the _funcs.py" from it
        if (csp_name != 'template'):
            csp_list.append(csp_name)
    
    return(csp_list)


# show_csps
#
# Returns the list of all the csp's that we support (I.E all the files that
# end with _funcs.py). 
#
# List can be used by further scripting
#
#     for csp_name in $(./ncsp csps); do ./ncsp $csp_name running; done
#
def show_csps():
    ''' returns a list of supported csps -- not including 'template' '''
    
    csp_list = get_csp_list()
    for csp_name in csp_list:
        print("%s " %  csp_name)
    
    return 0


# prints command line usage
def usage(module_path):
    ''' program usage help text '''
    
    print('''\
    Nvidia Cloud Service Provider common simple scriptable interface
    
    usage:
        ncsp cmd [options]
        ncsp <csp> csp_cmd [options]
    
    cmd:                    top level csp-independent commands
        help                overall application help
        csps                lists supported csps 
    ''')
    
        # show the <csp>_func.py files that have in directory
        
    import glob
    filelist = glob.glob(module_path + "*_funcs.py")    # ['test1/ali_funcs.py', 'test1/azure_funcs.py', ...
    print("    csp:                    name of the supported Cloud Service Provider (csp)")
    
        # special case for 'all'. 
        
    print("        %-23s %s" % ("ALL", "Runs command on all CSP's one after each other"))
    
        # now the rest of the files. 
        
    for filename in filelist:
        pos0 = filename.rfind("/")
        pos1 = filename.rfind("_funcs.py")
        csp_name = filename[pos0+1:pos1]
        
            # pull quoted string after HELPTEXT= from the file
            # 
        helptext=""
        
        try:
            with open(filename, "r") as f:
                for i, line in enumerate(f):
                    if (i > 10): 
                        break;
                    idx = line.find("HELPTEXT:");
                    if (idx >= 0):
                        start = line.find("\"", idx+9);
                        end   = line.find("\"", start+1)
                        if (start > idx and end > start):
                            helptext=line[start+1:end-1]
                            break
        except:
            helptext=""     # could not open file, don't report error

        print("        %-23s %s" % (csp_name, helptext))

        # rest of the menu
        
    print('''     
    csp_cmd:  
        CSP specific commands:
            createVM[opts]       create instance, use -h to see csp specific options
            stopVM               stop current instance
            startVM              start current instance
            restartVM            restart current instance
            deleteVM             delete (stop first) and destroy instance
            test                 create/stop/start/restart/delete timing test
            ping                 simple ping VM if possible - check connection
            ssh [cmd]            ssh into current VM instance, run command if given
            status               status of current instance
            show                 verbose info about instance           
        Network Security Group commands:
            createNSG [opts]     creates network security group
            deleteNSG            deletes network security group
            showNSGs             shows all network security groups           
        CSP Query commands:
            regions              displays list of region names supported by csp
            running              display list of running instances in a region
        General commands  
            validCSP             returns 0 if csp name is supported, 1 elsewise
            ip                   prints the ip value of the VM
            args                 display persistent args file
            clean                clean cached files, restore args to defaults
        help
            --help               csp specific argument help
    ''')
    sys.exit(1)

def add_common_options(my_class, parser):
    ''' common arguments used in outer control and CSP sepecific features '''
    
    parser.add_argument('--version', action='version', version="%(prog)s 0.0")
    parser.add_argument('--trace', dest='trace', type=int, choices=xrange(0,4),
                        default=0, required=False,
                        help='trace level flag: 0:none, 1:cmd, 2:+info, 3:+output')
    parser.add_argument('--inner_loop_cnt', dest='inner_loop_cnt', type=int, choices=xrange(0, 6),
                        default=2, required=False,
                        help='inner stop/start/reset test loops run')
    parser.add_argument('--outer_loop_cnt', dest='outer_loop_cnt', type=int, choices=xrange(0, 6),
                        default=1, required=False,
                        help='outer over-all create/delete loops run')
    parser.add_argument('--summary_report', dest='summary_report', type=int, choices=xrange(0, 2),
                        default=1, required=False,
                        help='show summary report at end of test')
    
        # some computed defaults used for VM
            
    my_user     = os.environ["USER"];
    my_vm_name  = my_user + time.strftime("-%a-%Y%b%d-%H%M%S", time.localtime())
    my_vm_name  = my_vm_name.lower()    # gcp (gcloud) wants all lower case names
    my_nsg_name = my_user + "NSG"       # for NetworkSecurity Group
    
        # common VM arguments -- do it here so don't have to set up these args
        # for every CSP. Gives them default values of "" so know if they are created or not
        # CSP code can override any of these with parser.set_defaults(key);

    parser.add_argument('--user', dest='user',              # overridden in CSP specific code
                        default=None, required=False,
                        help='username for the VM')
    parser.add_argument('--vm_name', dest='vm_name',        # Name of VM
                        default=my_vm_name, required=False,
                        help='external name of the VM')
    parser.add_argument('--vm_id', dest='vm_id',            # set in CSP specific code
                        default=None, required=False,
                        help='id value of the VM')
    parser.add_argument('--nsg_name', dest='nsg_name',      # common: Name of Network Security Group
                        default=my_nsg_name, required=False,
                        help='Network Security Group Name')
    parser.add_argument('--nsg_id', dest='nsg_id',          # set in CSP specific code
                        default="", required=False,
                        help='Network Security Group ID')   
    parser.add_argument('--key_name', dest='key_name',      # overridden in CSP specific code
                        default=None, required=False,   
                        help='ssh key name')
    parser.add_argument('--key_path', dest='key_path',      # common: where ssh key files reside
                        default="~/.ssh/", required=False,   
                        help='directory where ssh key files reside')
    parser.add_argument('--key_file', dest='key_file',      # computed in CSP specific code
                        default=None, required=False,
                        help='full path to ssh key file')
    parser.add_argument('--image_name', dest='image_name',  # overridden in CSP specific code
                        default=None, required=False,
                        help='name of the VM image to run')
    parser.add_argument('--image_id', dest='image_id',      # set in CSP specific code
                        default=None, required=False,
                        help='ID of the VM image to run')

    parser.add_argument('--pingable', dest='pingable',      # ping feature is optional to most VM network config
                        type=int, choices=xrange(0,2), 
                        default=0, required=False,          # default is not pingable    
                        help='set to 1 if can ping IP address')   
        
    parser.add_argument('--ip', dest='vm_ip',               # set in CSP specific dode
                        default="", required=False,
                        help='VM IP address')   
        
# process_cmd
#
# command line processor     - a big case statement
# see https://www.pydanny.com/why-doesnt-python-have-switch-case.html
#
# my_class is the CSPBaseClass, while argv are the additonal command line
# arguments that were passed in. This function is the top level command
# line parser for all the CSPs - this code is generic across all of them
#
# The 'createVM', 'stopVM' and the like functions are csp sepecific to change
# the state of a VM, and gather the proper IP address and set up the security
# rules.
#
# Commands like 'ssh', 'ping' use the IP address that was saved and allow
# access to that VM
#
# 
# 
def process_cmd(my_class, argv):

        # first thing, verify that the connection to the CSP is up and 
        # running correctly (cli app downloaded, user logged in, etc...)
         
    rc = my_class.CSPSetupOK()      # csp name dependent function
    if (rc != 0):
        error("CSP \"%s\" access is not configured correctly, set it up first" % my_class.ClassName())
        return rc                   # unhappy
    
        # create the main command line argument parser class
    
    parser = argparse.ArgumentParser(prog='csp', 
                                     description='CSP simple python interface for %s' % my_class.ClassName())
    
        # common options arguments
    
    add_common_options(my_class, parser)
                          
        # add in positional arguments
        
    parser.add_argument('command',  help="command to execute, run 'help' for details")
    parser.add_argument('arguments', help="optional csp specific args run '-h' for details",
                         nargs=argparse.REMAINDER)
 
        # class specific arguments 
        
    my_class.ArgOptions(parser)     # csp dependent function
       
        # update the defaults with values saved in file if that file exists
        
    my_class.ArgRestoreFromFile(parser)
    
        # actual argument parser, and any CSP class specific checks
        # 'args' here contains all the argument and option values in this order
        #
        #   1) hardcoded defaults in arg-command, or programaticly determined
        #   2) overridden by any value specifed in the saved args from last run (if saved)
        #   3) overridden by any values specified on command line ]
        #
        # Then the command is run
        #
        # Then, At very end of this function, if commands were successful all the 
        # option values and computed/inquired values like CSP ID values are written 
        # back to a file -- to be picked up in #2 above. 
        
    args = parser.parse_args(argv)
    
        # set global value used for trace level, as 'args' isn't passed around everywhere
    
    trace_setlevel(args.trace)         
    
        # CSP class specific arg checks, 
        # bail here if something isn't set correctly
        
    rc = my_class.ArgSanity(parser, args)
    if (rc != 0): 
        error("In ArgSanity rc:%d" % rc)
        return(rc)
        
        # this is the command that is to be run, pull from the args
        
    cmd = args.command
    
        # commands to handle the persistent arg list -- 
        
    if cmd == "clean":
        my_class.Clean(args)        # cleans out args an other cached files
        return 0
    elif cmd == "args":
        my_class.ArgShowFile()
        return 0
    elif cmd == "help":
        usage(my_class.m_module_path)
        return 1

        
            # print args if higher trace level 
        
    if (trace_do(2)):
        print vars(args)
        print "============"
        print "cmd=%s" % cmd
    
    rc = 0                              # return value if forget to set below
    
        # parse the commands

    if cmd == "validCSP":
        rc = 0                            # invalid CSP name errors out above
    elif cmd == "createNSG":
        rc = my_class.CreateNSG(args)
    elif cmd == "deleteNSG":
        rc = my_class.DeleteNSG(args)    
    elif cmd == "showNSGs":
        rc = my_class.ShowNSGs(args)
    elif cmd == "createVM":
        rc = my_class.CreateVM(args)      # args is from parser.parse_args(argv)
    elif cmd == "startVM":
        rc = my_class.StartVM(args)
    elif cmd == "stopVM":
        rc = my_class.StopVM(args)
    elif cmd == "restartVM":
        rc = my_class.RestartVM(args)
    elif cmd == "deleteVM":
        rc = my_class.DeleteVM(args)
    elif cmd == "ssh":
        rc, stdoutstr, stderrstr = my_class.Ssh(args, True, argv[1:])  # args is historical and incl
    elif cmd == "ping":
        rc = my_class.Ping(args)
    elif cmd == "status":
        rc = my_class.Status(args)
    elif cmd == "show":
        rc = my_class.Show(args)
    elif cmd == "boottime":
        rc, kernel, user, total = my_class.KernelBootTime(args)
        if (rc == 0):
            print ("kernel:%s user:%s total:%s" % (kernel, user, total))
    elif cmd == "running":
        rc = my_class.ShowRunning(args)
    elif cmd == "regions":
        rc = my_class.ShowRegions(args)
    elif cmd == "ip":
        rc = my_class.ShowIP(args)
    elif cmd == "test":     # default is 1 outer create/delete loop
        if (args.outer_loop_cnt <= 0):
            error("outer_loop_cnt=0, no tests run")
        else:
            for loop in range(0, args.outer_loop_cnt):
                rc = time_test(my_class, loop, args)
                if (rc != 0):
                    break
                time.sleep(30)   # time between loops
            if (rc != 0):
                error("Test returned %d" % rc)  
    else:
        error("Undefined command", cmd)
        usage(my_class.m_module_path)
        rc = 1
        
        # save all the persistent args values to file after the above commands have
        # run and modified them -- like the VM or SecurityGroup IDs
        
    if (cmd != "DeleteVM"):
        my_class.ArgSaveToFile(args)
    
    if rc == None:      # handle "None" return case -- should be an error? 
        error("No return code for cmd \"%s\"" % cmd)
        rc = 2

    return rc    # exit code

###############################################################################
# do_csp_cmd
#
# Major magic of the code..
#
# dynamically based on the csp name, load a module "<csp>_funcs.py" 
# and create its main class instance. This csp specific file will
# be in the same directory as the main module. 
#
# To add a new CSP, simply create a csp-specific file of the given
# "csp".py name with interfaces that are same as the other examples
# and drop it into the directory with the other csp-specific files 
#
# NOTE: find_module() does not handle dotted package names, 
#       so keep the file structure simple
#
# See: https://pymotw.com/2/imp/    (1/2018)
#
def do_csp_cmd(csp, argv): 
    ''' import csp dependent class based on name, and run command on it '''
    
    import imp
    module_name      = "%s_funcs" % csp
    try:
        f, filename, description = imp.find_module(module_name)
        package = imp.load_module(module_name, f, filename, description)
        my_class = package.CSPClass(csp, module_path)
    except ImportError, err:
        print "Error: CSP \"%s\" not supprted: %s" %(csp, err)
        sys.exit(1)             # unhappy return
    
        # process the command line arguments on class (does all the work)
        
    rc = process_cmd(my_class, sys.argv[2:])
    return rc

###############################################################################
# main body of nsp application. Code starts here. 
# 
# Loads the csp specific csp module and does the work
#
    
    # argv[0] is the full path to the prog name -- from it we can get 
    # the path where our modules will be, used for search later

try:
    pos = sys.argv[0].rfind("/")
    module_path = sys.argv[0][0:pos+1]
except:
    module_path = sys.argv[0]  

if (sys.argv.__len__() == 1):               # no arguments, print usage
    usage(module_path)      
    
    # if we have one arg, it's probably the csp name, but there are
    # few special options like 'help' or 'csps' that are also allowed
    
arg1=sys.argv[1]                            # our csp name, like "aws",
                                    

if (arg1 == "help" or arg1[0:1] == '-'):    # be nice if user is confused
    usage(module_path)                      # usage exits, does not return  
elif (arg1 == "csps"):                      # list all known CSP classes
    rc = show_csps()
    sys.exit(rc)

    # from here on out, we are doing a CSP depenent function -- so
    # need at least one more argument beyond the CSP name
    
csp = arg1                                  # name of the csp are we talking about
if (sys.argv.__len__() <= 2):
    usage(module_path)                      # not enough args, exit with usage

    # from here on, the argument list starts with the 2nd value 
    
argv=sys.argv[2:]

    # if csp is 'all', then run the given command on all of csp's that are 
    # active (don't complain about those CSP's that fail the CSPSetupOK test)
    # Also don't run 'template' class -- we want the good stuff here


if (csp == "ALL"):
    csp_list = get_csp_list()
    for csp in csp_list:
        rc = do_csp_cmd(csp, argv)
else:
    # single csp is given -- run it. 
    # parse the rest of the command line and run it on the given CSP
    
    rc = do_csp_cmd(csp, argv)
sys.exit(rc)


