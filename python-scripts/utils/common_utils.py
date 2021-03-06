# Copyright 2018 Owkin, inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import socket

import time
from subprocess import call, check_output


def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


# Wait for a process to begin to listen on a particular host and port
# Usage: waitPort <what> <timeoutInSecs> <errorLogFile> <host> <port>
def waitPort(what, secs, logFile, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))

    if result != 0:
        print('Waiting for %s ...' % what, flush=True)
        starttime = int(time.time())

        while True:
            call(['sleep', '1'])
            result = sock.connect_ex((host, port))
            if result == 0:
                break

            if int(time.time()) - starttime > secs:
                print('Failed waiting for %(what)s; see %(logFile)s' % {'what': what, 'logFile': logFile}, flush=True)

            print('.', end='', flush=True)


# Wait for one or more files to exist
def dowait(what, secs, logFile, files):
    logit = True
    starttime = int(time.time())

    for file in files:
        while not os.path.exists(file):
            if logit:
                print('Waiting for %s ...\n' % what, flush=True)
                logit = False

            time.sleep(1)

            if int(time.time()) - starttime > secs:
                print('Failed waiting for %(what)s; see %(logFile)s\n' % {'what': what, 'logFile': logFile}, flush=True)
                return False

            print('.', end='', flush=True)

    print('')

    return True


# Remove chaincode docker images
def remove_chaincode_docker_images():
    chaincodeImages = check_output('docker images | grep "^dev-peer" | awk \'{print $3}\'', shell=True)

    if chaincodeImages:
        print('Removing chaincode docker images ...', flush=True)
        call('docker rmi -f ' + chaincodeImages.decode('utf-8').replace('\n', ' '), shell=True)


# Remove chaincode docker containers
def remove_chaincode_docker_containers(version=None):
    if version is None:
        chaincodeContainers = check_output('docker ps -a | grep "dev-peer" | awk \'{print $1}\'', shell=True)
    else:
        chaincodeContainers = check_output('docker ps -a | grep "dev-peer" | grep "%s"| awk \'{print $1}\'' % version, shell=True)

    if chaincodeContainers:
        print('Removing chaincode docker containers ...', flush=True)
        call('docker rm -f ' + chaincodeContainers.decode('utf-8').replace('\n', ' '), shell=True)
