# pylint: disable=I,E,R,F,C
from fabric.api import local, cd, run
from fabric.contrib import files
from datetime import datetime as dt

def pip_dump():
    local("pip freeze > requirements.txt")

def test():
    local("pylint3 *.py -E -j 4 -f colorized")
    local("python test.py")

def deploy(directory="~/GSVPlanBot-git"):
    # check if there are uncommitted changes
    local("git diff-index --quiet HEAD --") 

    test()
    backup_db()

    with cd(directory + "/GSVPlanBot"):
        run("git pull")
        run(directory + "/env/bin/pip install -r GSVPlanBot/requirements.txt")
        run("systemctl --user restart GSVPlanBot")

def backup_db():
    timestamp = dt.now().strftime("%Y-%m-%d %H:%M")
    run("cp users.db \"../backups/users.db+" + timestamp + ".bak\"")

def setup_instance(directory):
    run("mkdir " + directory)
    with cd(directory):
        run("git clone https://github.com/NotAFile/GSVPlanBot")
        run("pyvenv env")
        run("env/bin/pip install -r GSVPlanBot/requirements.txt")
