#	Build Agent Updater

This tool allows remote execution of install and upgrade actions for iOS build agents. 

## Setup

**Requirements**

You'll need Python 2.7.x to run and [pip](https://pip.pypa.io/en/stable/installing/) to install your dependencies.

It's recommended that you use [Virtualenv](https://virtualenv.pypa.io/en/stable/) to manage Python dependencies.

Clone this repository and then run
`pip install -r requirements.txt`

## Using Fabric

Fabric is a tool that allows remote execution of commands by defining tasks. These tasks are contained in a file called `fabfile.py` and are invoked using the command `fab <command name>`. If you would like to run tasks on many hosts, you can either pass a comma-separated list of hosts using the `-H` flag.

You can also specify a username and password using the `-u` and `-p` flags.

Example usage:

`fab -u ios_builder -p password1 -H buildbox01.tx.com install_gem:gem=fastlane`

This would run the task `install_gem` using the parameter `gem=fastlane` on the specified host with the specified credentials.

If you would rather not enter each host into the command prompt, you may alternatively make a file called `host_list.txt` with a target host on each line.

## Remote Tasks

This is a list of some of the commands you will find useful for updating build agents. Take a look in the `fabfile`  for all the tasks you can execute.

### install_gem
Downloads a gem and all its dependencies to a local temporary directory, copies the local gems to each host, and installs. No need for reconfiguring firewalls this way!

Parameters:
`gem` - name of gem on Rubygems you want to install.

`fab install_gem:gem=gem_name`


**run_command**

Simply run a command on each listed host.

Parameters:
`command` - command you want to run.

`fab run_command:command="ls /Applications/"`

**update_xcode**

Updates Xcode on each host. Before you run this command, you will need to download a copy of the `xip` file containing Xcode.


Parameters:
`version_number` -  the new version you want to install.
`local_xcode_xip` - path to the local `xip` file containing Xcode.

`fab update_xcode:version_number=9.3,local_xcode_xip=/Users/afreas/Downloads/Xcode_9.3.xip`

**install_dmg**

Installs `dmg` file to hosts using locally downloaded `dmg`.

Parameters:
`local_dmg` - path to `dmg` file that contains `pkg`s you want to install.

`fab install_dmg:local_dmg=~/Downloads/Command_Line_Tools_macOS_10.13_for_Xcode_9.3.dmg`

**select_xcode**

Uses `xcversion` (which uses `xcode-select`) to select an Xcode version.

Parameters:
`version` - the installed Xcode version to switch to.
`reboot` - optional boolean, if `true` will reboot the machine it executes on. Defaults to `false`.

`fab select_xcode:version=9.3,reboot=true`

**clean_derived**

Deletes derived data in `~/Library/Developer/Xcode/DerivedData/` directory.

`fab clean_derived`

**build_agent**

Runs a TeamCity build agent command. Can be used to start, stop or get info.

Parameters:
`command` - one of `start`, `stop`, or `info`.

`fab build_agent:command=start`
