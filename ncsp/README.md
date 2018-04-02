# NCSP: NVIDIA Simple CSP interface
*NVIDIA/ngc_examples/ncsp/README.md*

Tries to provide a common low level scriptable CLI interface to create, start, stop, restart and delete VMs on various different CSPs. With multiple CSPs and different (one could say unique) command syntaxes, parameters and id confiurations for each of them, trying to write common low level cross platform applications on top of each of them is problematic. 

There are four interdependent goals that are being addressed here:

1. Easy access to the CSP to create and run VMS
1. Understanding what the CSP is capable of and how to control it 
1. Explore differences between the commands,  features and performance of the different CSPs
1. Provide a simple command line and scriptable interface to create and control VMs independent of the CSP. 

Terraform could potentially be used for some of this, but while it provides interfaces to lots of different CSPs, it’s difficult to see exactly what the commands are doing at the bottom end. And that violates #2 above.  But there’s nothing here that means you can’t write a Terraform interface within NCSP if you want, ( Which would be a excellent way to learn about Terraform! ) 

This project attempts to achieve the above goals by doing the following

1. Code is simple well documented python, easy to look at and tweak
1. Provides a identical CLI interface regardless of the CSP. Users can easily start a VM on a CSP without knowing any of the internal features of the CSP
1. CSP specific code and error checking is pretty well isolated to specific CSP dependent modules. All the command parsing, error handling, persistence and reports are independent of that code. 
1. CSP dependent parameters, like the image name, region or login name are defaulted in a CSP dependent manor and for the most part are not needed to be tweaked by the user. Yet all these parameters can be tweaked on the command line
1. These tweakable configuration parameters are persistently stored in a file, and remain set until they are changed or cleared in mass.
1. The CSP returned object values, such as VM ids and IP address are also stored in that same persistent file, and can be viewed and tweaked in the same way as other parameters. You don’t need to remember them, and the command make use if them when needed
1. Easy to add a interface to a new CSP

## Quick overview of **ncsp**'s capabilities 

If you want to bring up a VM on Amazon AWS, the command is
```
ncsp aws createVM
```
Then to get it’s uptime
```
ncsp aws ssh uptime
```
You want to create VM using a 8GPU instance - I.E type=p3.16xlarge
```
ncsp aws --instance_type p3.16xlarge createVM
```
And to delete the VM, its
```
ncsp aws deleteVM
```
That’s it… 

If AWS isn't your thing today, and do you want to start using Google Cloud? Same commands as above, but notice that for the most part, only the CSP's name has changed
```bash
ncsp gcp --accelerator_count=8 createVM
ncsp gcp ssh uptime
ncsp gcp deleteVM
```
There might be a few CSP specific changes that you have to account for -- like the number of GPUs as '--accelerator_count=8' in the Google example above.

Note that the general and many CSP specific command line options can be displayed via
```
ncsp <CSP> --help
```

Well Google Cloud has been fun, but you might run into case where you need to run the same test multiple times on differnt CSPs. In this case, we parameterize the CSP name, as **CSP**, which is passed into a small scrupt run **mytest** in a loop 1000 times. 
```
 #!/bin/bash
 # mytest script -- create/delete and run a test on a VM 1000 times
 #
 set -e   # have bash exit script on any non-zero error code
 for i in `seq 1 1000`;  do
    nscp $CSP createVM
    nscp $CSP ssh mytest
    nscp $CSP deleteVM
 done
 if [ $? -ne 0 ]; then
     ncsp $CSP ssh   # poke around if a error leaves VM up, will fail if dies
     return 1        # return 1 to stop outer loop
 else
     return 0        # test ran successful, return 0 
 fi
```
 
To run this on aws, google and alibaba, this is all you need to do:
```
set -e            # have bash exit script on first non-zero return
for CSP in "aws" "gcp" "ali" ; do
    mytest $CSP   # call script with each CSP name
done
```
In fact, the command **./ncsp csps** lists all the CSP's that it knows about, so the above script could be even more generic by
```
set -e            # have bash exit script on first non-zero return
for CSP in $(./ncsp csps); do 
    mytest $CSP   # call script with CSP name
done
```

To finish our quick look at **ncsp**, as this is an instructional application, you will want to see the commands are being sent out to the CSP's and their responses. The **--trace** option is used for this. The value is 0:**off**, 1:**commands**, 2:**commands and response**
```
Peters-MacBook-Pro:ncsp pbradstr$ ./ncsp aws --trace 1 createVM             
aws ec2 describe-security-groups  --region us-west-2
aws ec2 describe-images --region us-west-2 --filters Name=name,Values="ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server*"             
aws ec2 run-instances --image-id ami-01eb3061 --instance-type t2.micro --region us-west-2 --key-name baseos-awskey-oregon --security-group-ids sg-0cca0173              
aws ec2 create-tags --resource i-0e18d6bdac9e994e1 --tags Key=Name,Value=pbradstr-Thu-2018Feb01-185738
. . .
```
## Important features:
### CSP command line appliations (CLI) must be setup first:
You need to set up the command line interface with your proper account authorizations before any of scripts here will work. They are designed to operate by calling those CLI commands directly. 

Please see your CSP's documentation on how to set that up and verify it's working.

But keep in mind, one of the goals of the scripts here is to provide full working examples of the most important commands necessary to create and control VMs on the various CSP's and provide comparisons between those implementations. 
### CSP Default values:
There are a few values at the top of each csp specific module that you should set. They are all named **default_...* and specify values particular to your setup like your ssh key, and the region you are operating out of.
 
```
 ############################################################################## 
 # some Amazon aws defaults values that will vary based on users 
 # 
 # default_key_name:     User will need to create their own security key and 
 #                       specify it's name here.
 # region:               The <CSP> region that they wish to run in. Note that
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


default_image_name      = "Generic <CSP> starter AMI*"
default_instance_type   = "type1.small"   # 1gpu, 4gpu and 8gpu instances
default_choices         = ['type1.small', 'type1.med', 'type1.large'] 
```

There may be a few more of these, depending upon which CSP is being used. But all the necessary defaults that you must set up are located at the top of the file, and begin with **my_**

While you can enter these on the command line, and they are persistent until the VM is deleted, you will find it easiest to set these up properly. 

### Persistance: 
Persistance of the arguments and logs is done in the **$HOME/ncsg** directory. You will see a directory for each CSP of the form
```
└── aws
    ├── data
    │   ├── args
    │   └── regions
    └── logs
        ├── cmds
        └── test
```
The **data/args** file contains all the command line option falues and response that are currently active. **Deleting the VM** or the **<csp> clean** command deletes that file, restoring all options back to programmed defaults.

The command options are persistent once you type them in. If you turn on tracing
```
ncsp aws --trace 1 createVM       # turn on tracing while creating a VM
```
That tracing will remain in effect, till you turn it off, clear the args, or delete the VM
```
ncsp aws deleteVM                 # trace will be turned off at end of the command
ncsp aws createVM                 # no tracing will be enabled for next creating
```
Note that due simply to this simple per-CSP directory structure, only one active instance is allowed for a single CSP at one time. But you can have unique instances running in each supported CSP. There are several ways around this, one of which is listed below, so don't fret about this preceived limitation too much. 
### More serious scripting
As shown above, you embed these commands in other scripts.   For a little bigger example, here is something that creates a VM, starts and stops it 10 times, then deletes it.  It works with any of the CSPs that you have accounts with.

All the ncsp commands exit with 0 if successful, or 1 of not. Take note that the ```-set e``` command at the top of the script will break out of the script when it first sees a non-zero return code, and exit the script with that value. Thus this bash script does error checking even though it's not explicit.

```#!/bin/bash
  
set -e                        # exit on any non-zero exit code

CSP="ali"                     # what CSP test is going to be run on
./ncsp $CSP validCSP          # returns 0 only if we know this CSP name
./ncsp $CSP createVM          # create a new VM

CNT=0                         # counter
while [ $CNT -lt 10 ]; do
  echo "Loop $CNT ------------------"
  ./ncsp $CSP ssh uptime      # do something interesting
  ./ncsp $CSP stopVM          # stop the VM
  echo ""
  sleep 10
  ./ncsp $CSP startVM         # start VM
  echo ""
  sleep 10
  CNT=$[$CNT+1]
done
./ncsp $CSP deleteVM          # delete the VM
exit 0
```
If your getting more serious into automating these features, you might as well do it in Python. Take a look at the time_test() function in ncsp.py which is a big brother of the bash script above.
 
### Support for additional CSPs
The CSP dependent code is loosely placed in the <csp>funcs.py file for each csp. These are read in when the **ncsp** application is started, based on the 2nd argument. Thus to support any CSP, all that's necessary is having a file by the proper name in the directory. 

The file **template_funcs.csp** contains the 20 or so CSP dependent function with all the proper arguments, and kind emulates the interface without actually doing anything. It's well commented and a good starting point. You can actually run it, all internal and return values are emulated as correct as possible. 
```
    ./ncsp template createVM
    ./ncsp template running
```

So, to develop support a new CSP, or to test features of an exising one without effecting the current code, start with **template_funcs.csp** or copy one of the working files to a new name and then minipulate as needed. 

Note that as the CSP name changes, so does the persistant data path mentioned above, so you also get a compleatly isolated data and logs directory
```
Peters-MacBook-Pro:ncsp pbradstr$ ln -s aws_funcs.py myaws_funcs.py
Peters-MacBook-Pro:ncsp pbradstr$ ./ncsp myaws show
ERROR: No 'myaws' VM ID value
Peters-MacBook-Pro:ncsp pbradstr$ ./ncsp myaws createVM  # creates a new VM of 'myaws' type
```
In addition to development, the above trick is one way to support multiple different VM instance with the same CSP. All you really need to do is to link it here file
```
Peters-MacBook-Pro:ncsp pbradstr$ ln -s aws_funcs.py myaws_funcs.py
```
## CSP specific commands
### ALL csp
This psudeo-csp will run the commands on all the CSP's that are supported, one after each other. Intended for 'running' and 'status' commands mostly 

### Google GCP
There are no specific instance-types Vm's with GPUS for Google gcp - To create VM's with GPUs, use the **--accelerator_type** and **--accelerator_count** options. Rea
```
./ncsp gcp --accelerator_type nvidia-tesla-p100 --accelerator_count 2 createVM
```
 

## The main usage help text
```
 ./ncsp help
    Nvidia Cloud Service Provider common simple scriptable interface
    
    usage:
        ncsp cmd [options]
        ncsp <csp> csp_cmd [options]
    
    cmd:                    top level csp-independent commands
        help                overall application help
        csps                lists supported csps 
    
    csp:                    name of the supported Cloud Service Provider (csp)
        ALL                     Runs command on all CSP's one after each other
        aws                     Amazon Cloud Service Provide
        gcp                     Google Cloud Service Provide
        ali                     Alibaba Cloud Service Provide
        template                Template sample code for not yet developed <CSP
     
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
 ```
