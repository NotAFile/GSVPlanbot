# pylint: disable=I,E,R,F,C
from fabric.api import local

def dump_requirements():
    local("pip freeze > requirements.txt")

def test():
    local("pylint3 *.py -E -j 4 -f colorized")
    local("python test.py")

def deploy():
    local("")
