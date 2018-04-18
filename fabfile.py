from fabric.api import local
from fabric.operations import put
from tempfile import mkdtemp
from fabric.context_managers import shell_env
from fabric.contrib import files
from fabric.api import *
from os import path
import subprocess


with open('host_list.txt') as host_list:
    env.hosts = host_list.readlines()


@task
@runs_once
def fetch_gem_locally(gem):
    temp_dir = mkdtemp()

    with shell_env(GEM_HOME=temp_dir, GEM_PATH=temp_dir):
        with lcd(temp_dir):
            print('fetching %s to %s' % (gem, temp_dir))
            local('gem install --no-ri --no-rdoc --install-dir . %s' % gem)

    return temp_dir

@task
def install_gem(gem):

    # `execute` returns values for each host that it will execute for,
    # so we need to pick out just one of those since it was a local task.
    # There's probably a better way to do this but hey this works.

    local_gem_dir = execute(fetch_gem_locally, gem=gem).values()[0]
    
    remote_dir = run('mktemp -d')

    put('%s/*.gem' % local_gem_dir, remote_dir)

    with cd(remote_dir):
        gem_files = run('ls *.gem')

    for gem in gem_files.split():
        run('gem install --force --ignore-dependencies --local %s/%s' % (remote_dir, gem))

    

def run_command(command):
    run(command)

def run_xcode_install_script():
    pass

def remote_xip_dir(xip_filename):
    
    xip_dir = path.join('XcodeXIPs', xip_filename)
    return run('echo $HOME/%s' % xip_dir)

@task
@runs_once
def propogate_file_to_all_hosts(remote_dir, local_file=None):

    first_host = env.hosts[0]

    if local_file:
        remote_files = put(local_file, remote_dir)
    else:
        remote_files = [remote_dir]

    for host in map(lambda x: x.rstrip(), env.hosts) :
        for remote_file in remote_files:
            with settings(prompts={'Password:': env.password}):
                command = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
                        %s %s@%s:%s' % (remote_file, env.user, host, remote_dir)
                run(command)

@task
def create_dir_if_needed(remote_dir):
    with settings(warn_only=True):
        run('mkdir %s' % remote_dir)

@task
def copy_xcode_if_needed(xcode_location):

    xip_filename = path.basename(xcode_location)
    remote_xip = remote_xip_dir(xip_filename)
    if compare_xcode_versions(xcode_location, remote_xip) == True:
        print('No need to copy, Xcode xips are the same')
        return remote_xip

    print('Xcode versions are different, uploading our local version')

    with settings(warn_only=True):
        run('mkdir %s' % remote_xip)

    put(xcode_location, remote_xip)
    return remote_xip

@task
def compare_xcode_versions(local_xip, remote_xip):

    with settings(warn_only=True):
        local_signature = subprocess.check_output('pkgutil --check-signature %s' % local_xip, \
                                                  shell=True, universal_newlines=True)
        remote_signature = run('pkgutil --check-signature %s' % remote_xip)
    retval = remote_signature.replace('\r', '') == local_signature.rstrip('\n\n')

    return retval

@task
def update_xcode(version_number, local_xcode_xip):

    remote_xip = copy_xcode_if_needed(local_xcode_xip)

    propogate_file_to_all_hosts(remote_xip)

    with settings(prompts={'Password:': env.password}):
        run('yes \'%s\' | xcversion install --no-switch --no-show-release-notes \
                --verbose %s --url=\'file://%s\'' % (env.password, version_number, remote_xip))

@task
def clean_derived():
    run('rm -rf ~/Library/Developer/Xcode/DerivedData/')

@task
def check_xcode():
    run('xcode-select -p')
