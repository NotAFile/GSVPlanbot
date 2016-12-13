# pylint: disable=I,E,R,F,C
from fabric.api import local, cd, run
from fabric.contrib import files
from datetime import datetime as dt

def pip_dump():
    local("pip freeze > requirements.txt")

def test():
    local("pylint3 *.py -E -j 4 -f colorized")
    local("python test.py")

def deploy():
    test()
    backup_db()

    with cd("~/GSVPlanBot/GSVPlanBot"):
        run("git pull")
        run("systemctl --user restart GSVPlanBot")

def backup_db():
    timestamp = dt.now().strftime("%Y-%m-%d %H:%M")
    run("cp users.db ../backups/users.db+" + timestamp + ".bak")

def setup_instance(directory):
    run("mkdir " + directory)
    with cd(directory):
        run("git clone https://github.com/NotAFile/GSVPlanBot")
        run("pyvenv 
