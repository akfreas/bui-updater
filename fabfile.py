from fabric.api import local
from fabric.operations import put, get
from tempfile import mkdtemp
from fabric.context_managers import shell_env
from fabric.contrib import files
from fabric.api import *
from os import path
from StringIO import StringIO
import subprocess


if len(env.hosts) == 0:
    with open('host_list.txt') as host_list:
        env.hosts = host_list.readlines()


def remote_package_dir(xip_filename=None):
    
    xip_dir = 'XcodeInstallation'

    if xip_filename:
        xip_dir = path.join(xip_dir, xip_filename)

    return run('echo /var/tmp/%s' % xip_dir)


@task
def add_match_github_key_and_config(key_file_path):
    file_buf = StringIO()

    users = sudo('users')
    default_user = 'iosbui'
    if 'ios-crew' in users:
        default_user = 'ios-crew'


    config_path = '/Users/%s/.ssh/config' % default_user
    match_key_path = '/Users/%s/.ssh/github-match.key' % default_user
    put(key_file_path, match_key_path, use_sudo=True, mode=0600)

    if files.exists(config_path):
        get(config_path, file_buf, use_sudo=True)
    else:
        file_buf.write('')

    content=file_buf.getvalue()

    with open('./match_ssh_config.txt') as match_config_fp:
        match_config = '\r\r' + match_config_fp.read()

    content = content.replace(match_config, '')
    content += match_config

    file_buf = StringIO()
    file_buf.write(content)

    put(remote_path=config_path, local_path=file_buf, use_sudo=True)

    for path in [config_path, match_key_path]:
        sudo('chown %s %s' % (default_user, path))

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

    

@task
def run_command(command):
    with settings(warn_only=True):
        run(command)


@task
@runs_once
def propogate_file_to_all_hosts(remote_file=None, local_file=None):

    first_host = env.hosts[0]
    if local_file:
        remote_files = put(local_file, remote_file)
    else:
        remote_files = [remote_file]

    for host in map(lambda x: x.rstrip(), env.hosts[1:]) :

        for remote_file in remote_files:
            with settings(warn_only=True, prompts={'Password:': env.password}):
                run('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no %s@%s \'mkdir %s\'' % 
                        (env.user, host, path.dirname(remote_file)))
                command = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
                        %s %s@%s:%s' % (remote_file, env.user, host, remote_file)
                run(command)

    return remote_files

@task
def create_dir_if_needed(remote_dir):
    with settings(warn_only=True):
        # recursively create directories if they do not exist
        run('mkdir -pv %s' % remote_dir)

@task
@runs_once
def copy_xcode_if_needed(xcode_location):

    xip_filename = path.basename(xcode_location)
    remote_xip = remote_package_dir(xip_filename)

    if compare_xcode_versions(xcode_location, remote_xip) == True:
        print('No need to copy, Xcode xips are the same')
        return remote_xip

    print('Xcode versions are different, uploading our local version')
    
    create_dir_if_needed(path.dirname(remote_xip))

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

    #with settings(warn_only=True):
    #    build_agent('stop')

    remote_xip = copy_xcode_if_needed(local_xcode_xip)

    #create the same directory on all hosts
    create_dir_if_needed(path.dirname(remote_xip))

    #this command only runs once
    propogate_file_to_all_hosts(remote_xip)

    with settings(warn_only=True, prompts={'Password: ': env.password}):
        run('xcversion install --no-switch --no-show-release-notes \
                --verbose %s --url=\'file://%s\'' % (version_number, remote_xip))


    build_agent('start')

@task
def delete_xcode_xips():
   
    xips = remote_package_dir()
    run('rm -r %s/*.xip' % xips)

@task
def build_agent(command):
    
    agent_command = '/usr/local/buildAgent/bin/agent.sh %s' % command

    with settings(warn_only=True):
        run(agent_command)
    users = sudo('users')

    with settings(warn_only=True):
        if 'ios-crew' in users:
            sudo(agent_command, user='ios-crew')
        else:
            run(agent_command)

@task
def install_dmg(local_dmg):


    remote_dmg = propogate_file_to_all_hosts(local_file=local_dmg)
    for dmg in remote_dmg:
        mountpoint = '/Volumes/RemotelyMountedDMG'

        if files.exists(mountpoint):
            sudo('hdiutil unmount %s' % mountpoint)

        sudo('hdiutil attach -mountpoint %s %s' % (mountpoint, dmg))
        found_pkgs = run('find %s -name "*.pkg"' % mountpoint)
        for pkg in found_pkgs.split('\n'):
            sudo('installer -verbose -pkg \'%s\' -target /' % pkg)
        sudo('hdiutil unmount %s' % mountpoint)

@task
def clean_derived():
    with settings(warn_only=True):
        run('rm -rf ~/Library/Developer/Xcode/DerivedData/')

@task
def select_xcode(version, reboot=False):

    with settings(warn_only=True):
        build_agent('stop')

    with settings(prompts={'Password:': env.password}):
        run('xcversion select %s' % version)
        if reboot:
            sudo('reboot')

    build_agent('start')


@task
def check_xcode():
    run('xcode-select -p')
    run('xcversion selected')
