#!/bin/bash
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


help() {
    echo -e "Usage: $0  [OPTIONS...] [ARGUMENTS...]"
    echo ""
    echo "Arguments:"
    echo -e "\t- CHANNEL_ID Channel to create (required)"
    echo -e "\t- ORDERER_URL Orderer url (required)"
    echo -e "\t- ORGANIZATION_NAME Organization adding the channel (required)"
    echo ""
    echo "Options:"
    echo -e "-h Help!"
    echo ""
    echo "Example:"
    echo -e "\t- $0 mychannel https://myorderer.myorg.com:443 MyOrg"
}

if [[ $1 == "-h" || $1 == "--help" ]]; then
    help
    exit 0
fi

function createChannel() {
    if [ ! $# == 3 ]; then
        help
        exit 1
    fi

    CHANNEL_ID=$1
    ORDERER_URL=$2
    ORGANIZATION_NAME=$3

    printf 'Testing the connection with the orderer:'
    until $(curl --output /dev/null --silent --head $ORDERER_URL); do
        printf '.'
        sleep 2
    done

    configtxgen -profile OrgsChannel --outputCreateChannelTx channel.tx -channelID $CHANNEL_ID
    configtxgen -profile OrgsChannel --outputAnchorPeersUpdate anchor.tx -channelID $CHANNEL_ID -asOrg $ORGANIZATION_NAME
    peer channel create -f channel.tx -c $CHANNEL_ID -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt --outputBlock channel.block
    peer channel update -f anchor.tx -c $CHANNEL_ID -o $ORDERER_URL --tls --clientauth --cafile /var/hyperledger/tls/ord/cert/cacert.pem --keyfile /var/hyperledger/tls/client/pair/tls.key --certfile /var/hyperledger/tls/client/pair/tls.crt
}

createChannel $@
