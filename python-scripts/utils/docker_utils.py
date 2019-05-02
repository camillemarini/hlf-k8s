import os
import yaml

HLF_VERSION = '1.4.1'


def generate_docker_compose_org(org, conf_orderer, substra_path, network):

    orderer = conf_orderer['orderers'][0]

    FABRIC_CA_HOME = '/etc/hyperledger/fabric-ca-server'
    FABRIC_CFG_PATH = f'{substra_path}/data'
    FABRIC_CA_CLIENT_HOME = '/etc/hyperledger/fabric'

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': f'setup-{org["name"]}',
                                                  'image': 'substra/substra-ca-tools',
                                                  'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup.py 2>&1 | tee {substra_path}/data/log/setup-{org["name"]}.log"',
                                                  'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}',
                                                                  f'FABRIC_CFG_PATH={FABRIC_CFG_PATH}',
                                                                  f'FABRIC_CA_CLIENT_HOME={FABRIC_CA_CLIENT_HOME}'],
                                                  'volumes': ['./python-scripts:/scripts',
                                                              f'{substra_path}/data/log:{substra_path}/data/log',
                                                              f'{substra_path}/conf/config/conf-{org["name"]}.json:/{substra_path}/conf.json',

                                                              # TODO, remove
                                                              f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',

                                                              f'{substra_path}/conf/{org["name"]}/fabric-ca-client-config.yaml:{FABRIC_CA_CLIENT_HOME}/fabric-ca-client-config.yaml'],
                                                  'networks': [network],
                                                  'depends_on': [],
                                                  },

                                        'run': {'container_name': f'run-{org["name"]}',
                                                'image': 'substra/substra-ca-tools',
                                                'command': f'/bin/bash -c "set -o pipefail;sleep 3;python3 /scripts/run.py 2>&1 | tee {substra_path}/data/log/run-{org["name"]}.log"',
                                                'environment': ['GOPATH=/opt/gopath',
                                                                f'FABRIC_CFG_PATH={FABRIC_CFG_PATH}',
                                                                f'ORG={org["name"]}'],
                                                'volumes': [
                                                            # docker in docker
                                                            '/var/run/docker.sock:/var/run/docker.sock',

                                                            # scripts
                                                            './python-scripts:/scripts',

                                                            # logs
                                                            f'{substra_path}/data/log/:{substra_path}/data/log/',

                                                            # chaincode
                                                            '../substra-chaincode/chaincode:/opt/gopath/src/github.com/hyperledger/chaincode',

                                                            # channel
                                                            f'{substra_path}/data/channel/:{substra_path}/data/channel/',

                                                            # TODO remove
                                                            f'{substra_path}/data/orgs/:{substra_path}/data/orgs/',


                                                            # msp
                                                            f'{org["users"]["admin"]["home"]}/msp:{org["users"]["admin"]["home"]}/msp',
                                                            f'{org["users"]["user"]["home"]}/msp:{org["users"]["user"]["home"]}/msp',
                                                            f'{conf_orderer["users"]["admin"]["home"]}/msp:{conf_orderer["users"]["admin"]["home"]}/msp',

                                                            # conf files
                                                            f'{substra_path}/conf/:{substra_path}/conf/',
                                                            f'{substra_path}/conf/config/:{substra_path}/conf/config',
                                                            f'{substra_path}/data/configtx-{org["name"]}.yaml:{FABRIC_CFG_PATH}/configtx.yaml',

                                                            # orderer core yaml for peer binary
                                                            f'{substra_path}/conf/{conf_orderer["name"]}/{orderer["name"]}/:{substra_path}/conf/{conf_orderer["name"]}/{orderer["name"]}/',
                                                            # ca file
                                                            f"{org['ca']['certfile']}:{org['ca']['certfile']}",

                                                            # tls
                                                            f"{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}:{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}",
                                                ],
                                                'networks': [network],
                                                'depends_on': [],
                                                }
                                        },
                      'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{org["name"]}.yaml')}

    # RCA
    rca = {'container_name': org['ca']['host'],
           'image': f'hyperledger/fabric-ca:{HLF_VERSION}',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'ports': [f'{org["ca"]["port"]["external"]}:{org["ca"]["port"]["internal"]}'],
           'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
           'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}'],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',
                       f'{substra_path}/backup/orgs/{org["name"]}/rca:{FABRIC_CA_HOME}',
                       f'{substra_path}/conf/{org["name"]}/fabric-ca-server-config.yaml:{FABRIC_CA_HOME}/fabric-ca-server-config.yaml'
                       ],
           'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
    docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

    # Peer
    for index, peer in enumerate(org['peers']):
        svc = {'container_name': peer['host'],
               'image': f'hyperledger/fabric-peer:{HLF_VERSION}',
               'restart': 'unless-stopped',
               'command': '/bin/bash -c "peer node start 2>&1"',
               'environment': [# https://medium.com/@Alibaba_Cloud/hyperledger-fabric-deployment-on-alibaba-cloud-environment-sigsegv-problem-analysis-and-solutions-9a708313f1a4
                               'GODEBUG=netdns=go+1'],
               'working_dir': '/etc/hyperledger/fabric',
               'ports': [f'{peer["port"]["external"]}:{peer["port"]["internal"]}'],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': [
                   # docker in docker chaincode
                   '/var/run/docker.sock:/host/var/run/docker.sock',

                   # channel
                   f'{substra_path}/data/channel/:{substra_path}/data/channel/',

                   # backup files
                   f'{substra_path}/backup/orgs/{org["name"]}/{peer["name"]}/:/var/hyperledger/production/',

                   # tls peer server files
                   f"{peer['tls']['dir']['external']}/{peer['tls']['server']['dir']}:{peer['tls']['dir']['internal']}",
                   # tls peer client files
                   f"{peer['tls']['dir']['external']}/{peer['tls']['client']['dir']}:{peer['tls']['dir']['external']}/{peer['tls']['client']['dir']}",
                   # tls orderer client files
                   f"{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}:{orderer['tls']['dir']['external']}/{orderer['tls']['client']['dir']}",

                   # TODO, remove
                   f'{substra_path}/data/orgs/{org["name"]}/:{substra_path}/data/orgs/{org["name"]}/',

                   # msp
                   f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/msp/:{org["core_dir"]["internal"]}/msp',

                   # conf files
                   f'{substra_path}/conf/{org["name"]}/{peer["name"]}/core.yaml:{org["core_dir"]["internal"]}/core.yaml',

                   # ca file
                   f"{org['ca']['certfile']}:{org['ca']['certfile']}",
                ],
               'networks': [network],
               'depends_on': ['setup']}

        # run
        docker_compose['substra_tools']['run']['depends_on'].append(peer['host'])

        # run override
        docker_compose['substra_tools']['run']['volumes'].append(f"{peer['tls']['dir']['external']}/{peer['tls']['client']['dir']}:{peer['tls']['dir']['external']}/{peer['tls']['client']['dir']}", )
        docker_compose['substra_tools']['run']['volumes'].append(f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/msp/:{org["core_dir"]["internal"]}/{peer["name"]}/msp', )

        # setup override
        docker_compose['substra_tools']['setup']['volumes'].append(f'{substra_path}/data/orgs/{org["name"]}/{peer["name"]}/msp/:{org["core_dir"]["internal"]}/{peer["name"]}/msp',)

        docker_compose['substra_services']['svc'].append((peer['host'], svc))

        # Create all services along to conf

        COMPOSITION = {'services': {}, 'version': '2', 'networks': {network: {'external': True}}}

        for name, dconfig in docker_compose['substra_services']['rca']:
            COMPOSITION['services'][name] = dconfig

        for name, dconfig in docker_compose['substra_services']['svc']:
            COMPOSITION['services'][name] = dconfig

        for name, dconfig in docker_compose['substra_tools'].items():
            COMPOSITION['services'][name] = dconfig

        with open(docker_compose['path'], 'w+') as f:
            f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose


def generate_docker_compose_orderer(org, substra_path, network):

    genesis_bloc_file = org['misc']['genesis_bloc_file']

    FABRIC_CA_HOME = '/etc/hyperledger/fabric-ca-server'
    FABRIC_CFG_PATH = f'{substra_path}/data'
    FABRIC_CA_CLIENT_HOME = '/etc/hyperledger/fabric'

    # Docker compose config
    docker_compose = {'substra_services': {'rca': [],
                                           'svc': []},
                      'substra_tools': {'setup': {'container_name': f'setup-{org["name"]}',
                                                  'image': 'substra/substra-ca-tools',
                                                  'command': f'/bin/bash -c "set -o pipefail;python3 /scripts/setup.py 2>&1 | tee {substra_path}/data/log/setup-{org["name"]}.log"',
                                                  'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}',
                                                                  f'FABRIC_CFG_PATH={FABRIC_CFG_PATH}',
                                                                  f'FABRIC_CA_CLIENT_HOME={FABRIC_CA_CLIENT_HOME}'],
                                                  'volumes': ['./python-scripts:/scripts',
                                                              f'{substra_path}/data/log:{substra_path}/data/log',
                                                              f'{substra_path}/data/genesis:{substra_path}/data/genesis',
                                                              f'{substra_path}/conf/config/conf-{org["name"]}.json:{substra_path}/conf.json',
                                                              f'{substra_path}/data/configtx-{org["name"]}.yaml:{FABRIC_CFG_PATH}/configtx.yaml',

                                                              # TODO, remove
                                                              f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',

                                                              f'{substra_path}/conf/{org["name"]}/fabric-ca-client-config.yaml:{FABRIC_CA_CLIENT_HOME}/fabric-ca-client-config.yaml',
                                                              ],
                                                  'networks': [network],
                                                  'depends_on': []}},
                      'path': os.path.join(substra_path, 'dockerfiles', f'docker-compose-{org["name"]}.yaml')}

    # RCA
    rca = {'container_name': org['ca']['host'],
           'image': f'hyperledger/fabric-ca:{HLF_VERSION}',
           'restart': 'unless-stopped',
           'working_dir': '/etc/hyperledger/',
           'ports': [f"{org['ca']['port']['external']}:{org['ca']['port']['internal']}"],
           'command': '/bin/bash -c "fabric-ca-server start 2>&1"',
           'environment': [f'FABRIC_CA_HOME={FABRIC_CA_HOME}'],
           'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
           'volumes': [f'{substra_path}/data/orgs/{org["name"]}:{substra_path}/data/orgs/{org["name"]}',
                       f"{substra_path}/backup/orgs/{org['name']}/rca:{FABRIC_CA_HOME}",
                       f"{substra_path}/conf/{org['name']}/fabric-ca-server-config.yaml:{FABRIC_CA_HOME}/fabric-ca-server-config.yaml"],
           'networks': [network]}

    docker_compose['substra_tools']['setup']['depends_on'].append(org['ca']['host'])
    docker_compose['substra_services']['rca'].append((org['ca']['host'], rca))

    # ORDERER
    for index, orderer in enumerate(org['orderers']):
        svc = {'container_name': orderer['host'],
               'image': f'hyperledger/fabric-orderer:{HLF_VERSION}',
               'restart': 'unless-stopped',
               'working_dir': '/etc/hyperledger/fabric',
               'command': '/bin/bash -c "orderer 2>&1"',
               'ports': [f"{orderer['port']['external']}:{orderer['port']['internal']}"],
               'logging': {'driver': 'json-file', 'options': {'max-size': '20m', 'max-file': '5'}},
               'volumes': [
                   # genesis file
                   f'{genesis_bloc_file}:{genesis_bloc_file}',

                   # backup files
                   f"{substra_path}/backup/orgs/{org['name']}/{orderer['name']}:/var/hyperledger/production/orderer",

                   # msp
                   f'{substra_path}/data/orgs/{org["name"]}/{orderer["name"]}/msp/:{org["core_dir"]["internal"]}/msp',

                   # tls server files
                   f"{orderer['tls']['dir']['external']}/{orderer['tls']['server']['dir']}:{orderer['tls']['dir'][ 'internal']}",

                   # conf files
                   f"{substra_path}/data/configtx-{org['name']}.yaml:{org['core_dir']['internal']}/configtx.yaml",
                   f"{substra_path}/conf/{org['name']}/{orderer['name']}/core.yaml:{org['core_dir']['internal']}/core.yaml",
                   f"{substra_path}/conf/{org['name']}/{orderer['name']}/orderer.yaml:{org['core_dir']['internal']}/orderer.yaml",

                   # ca file
                   f"{org['ca']['certfile']}:{org['ca']['certfile']}",
               ],
               'networks': [network],
               'depends_on': ['setup']}

        docker_compose['substra_tools']['setup']['volumes'].append(f'{substra_path}/data/orgs/{org["name"]}/{orderer["name"]}/msp/:{org["core_dir"]["internal"]}/{orderer["name"]}/msp', )
        docker_compose['substra_services']['svc'].append((orderer['host'], svc))

    # Create all services along to conf

    COMPOSITION = {'services': {}, 'version': '2', 'networks': {network: {'external': True}}}

    for name, dconfig in docker_compose['substra_services']['rca']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_services']['svc']:
        COMPOSITION['services'][name] = dconfig

    for name, dconfig in docker_compose['substra_tools'].items():
        COMPOSITION['services'][name] = dconfig

    with open(docker_compose['path'], 'w+') as f:
        f.write(yaml.dump(COMPOSITION, default_flow_style=False, indent=4, line_break=None))

    return docker_compose