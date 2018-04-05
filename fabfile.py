from fabric.api import local
from fabric.api import *
from fabric.operations import put
from tempfile import mkdtemp
from fabric.context_managers import shell_env

with open('host_list.txt') as host_list:
    env.hosts = host_list.readlines()


def install_xcpretty():
    run('gem install xcpretty')

def install_gem(gem):
    temp_dir = mkdtemp()

    with shell_env(GEM_HOME=temp_dir, GEM_PATH=temp_dir):
        with lcd(temp_dir):
            print('fetching %s to %s' % (gem, temp_dir))
            local('gem install --no-ri --no-rdoc --install-dir . %s' % gem)

    remote_dir = run('mktemp -d')

    put('%s/*.gem' % temp_dir, remote_dir)

    with cd(remote_dir):
        gem_files = run('ls *.gem')

    for gem in gem_files.split():
        run('gem install --ignore-dependencies --local %s/%s' % (remote_dir, gem))
    
def run_command(command):
    run(command)

def clean_derived():
    run('rm -rf ~/Library/Developer/Xcode/DerivedData/')

def check_xcode():
    run('xcode-select -p')
