from rich.traceback import install
import textwrap
from time import sleep
import yaml
import subprocess
import re
from napalm import get_network_driver
#from ntc_templates import parse
from collections import defaultdict
import ipaddress
from napalm.base.helpers import canonical_interface_name
from ciscoconfparse import CiscoConfParse
import yamlarg
import sys
import os
from datetime import datetime


def get_mac_table(sw, un, pw):
    driver = get_network_driver('ios')
    device = driver(sw, un, pw,
                    optional_args={'global_delay_factor': 2, 'transport': 'ssh'})
    device.open()
    mac_address_table = device.get_mac_address_table()
    config = device.get_config(retrieve='startup')['startup']
    int_to_mac = defaultdict(lambda: [])
    mac_to_int = defaultdict(lambda: [])
    int_mac_count = defaultdict(lambda: 0)
    for mac in mac_address_table:
        int_to_mac[canonical_interface_name(mac['interface'])].append(mac['mac'].replace(':','').upper())
        int_mac_count[canonical_interface_name(mac['interface'])] += 1
        mac_to_int[mac['mac'].replace(':','').upper()] = canonical_interface_name(mac['interface'])
    return {'int_to_mac': int_to_mac, 'int_mac_count': int_mac_count, 'mac_to_int': mac_to_int, 'config': config}


def find_interface(mac, sw_data):
    for sw in sw_data.keys():
        if mac in sw_data[sw]['mac_to_int'].keys():
            interface = sw_data[sw]['mac_to_int'][mac]
            if sw_data[sw]['int_mac_count'][interface] == 1:
                for ip_net, vlan in cfg['networks'].items():
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(ip_net):
                        parse = CiscoConfParse(sw_data[sw]['config'].splitlines())
                        #if 'switchport access vlan' not in '\n'.join([c.text for c in parse.find_objects(r'^interface ' + interface + '$')[0].children]):
                        if 'switchport mode trunk' not in '\n'.join([c.text for c in parse.find_objects(r'^interface ' + interface + '$')[0].children]):
                            return {'sw': sw, 'interface': interface, 'vlan': vlan}
    return None


if __name__ == '__main__':
    # Install rich traceback for better diagnostics.
    install(show_locals=True)
    from rich import print

    # Parse Arguments
    description = textwrap.dedent("""
    This script is used to provision ports from a default vlan to the correct vlan. 
    The input should be a configuration file in the following format.
    
    default-vlan: 1
    scan-frequency: 60 #60 seconds
    networks: # this section can be left out if you provide environment variables SW_USERNAME and SW_PASSWORD
    # ip/cidr: vlan
      192.168.2.1/24: 2
      192.168.3.1/24: 3
    sw-defaults:
      user: username
      pass: password
    switches:
      - 192.168.1.1
      - 192.168.1.2
      - 192.168.1.3
    
    This should be ran connected to a trunk interface, and specifying the interface name.
    
    Example usage.
    auto_port_config.py --interface=ens33 --cfg=./cfg.yaml
    
    """)
    try:
        pkgdir = sys.modules['auto_port_config'].__path__[0]
    except KeyError:
        import pathlib
        pkgdir = pathlib.Path(__file__).parent.absolute()
    args = yamlarg.parse(os.path.join(pkgdir, 'arguments.yaml'), description=description)

    # Load configuration. Set username/password if environment variables are set.
    cfg = yaml.load(open(args['cfg'], 'r'), Loader=yaml.FullLoader)
    if 'sw-defaults' not in cfg.keys():
        cfg['sw-defaults'] = dict()
    if os.getenv('SW_USERNAME') is not None:
        cfg['sw-defaults']['user'] = os.getenv('SW_USERNAME')
    if os.getenv('SW_PASSWORD') is not None:
        cfg['sw-defaults']['pass'] = os.getenv('SW_PASSWORD')
    os.getenv('SW_PASSWORD')

    print(datetime.now(), 'Starting...')
    while True:
        # Scan networks
        ips = dict()
        vlans = list(cfg['networks'].values())
        vlans.append(cfg['default-vlan'])
        for net in cfg['networks'].keys():
            for vlan in vlans:
                if cfg['networks'][net] != vlan:
                    print(datetime.now(), 'Scanning ' + net + ' on vlan ' + str(vlan) + '.')
                    scn = subprocess.run(
                        ['sudo', 'arp-scan', '--interface=' + args['interface'], '--vlan=' + str(vlan), net],
                        capture_output=True)
                    results = scn.stdout.decode('utf-8')
                    scn_ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)\t(([0-9a-f]{2}:){5}[0-9a-f]{2})(\t.*)', results)
                    for ip in scn_ips:
                        ips[ip[0]] = ip[1].upper().replace(':', '')
        # Check to make sure there are some IP's on incorrect vlans, then scan switches.
        if len(ips) > 0:
            print(datetime.now(), "Found IP Addresses: ")
            print(ips)
            # Update switch mac tables. This is done after scanning so the mac addresses show up on the switches.
            print(datetime.now(), "Fetching up to date information from the switches.")
            sw_data = dict()
            for sw in cfg['switches']:
                sw_data[sw] = get_mac_table(sw, cfg['sw-defaults']['user'], cfg['sw-defaults']['pass'])

            interfaces_to_modify = list()
            for ip, mac in ips.items():
                for ip_net, ip_vlan in cfg['networks'].items():
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(ip_net):
                        vlan = ip_vlan
                        break
                add_int = find_interface(mac, sw_data)
                if add_int is not None:
                    interfaces_to_modify.append(add_int)
            print(interfaces_to_modify)
            # Update the port configuration
            for data in interfaces_to_modify:
                print(datetime.now(), 'Updating ' + data['sw'] + ' ' + data['interface'] + ' to vlan ' + str(data['vlan']))
                sw = data['sw']
                interface = data['interface']
                vlan = data['vlan']
                driver = get_network_driver('ios')
                device = driver(sw, cfg['sw-defaults']['user'], cfg['sw-defaults']['pass'],
                                optional_args={'global_delay_factor': 2, 'transport': 'ssh'})
                device.open()
                config = 'interface ' + interface + '\n' + \
                         'switchport access vlan ' + str(vlan) + '\n' + \
                         'spanning-tree portfast \nspanning-tree bpduguard enable'
                if not args['dry_run']:
                    device.load_merge_candidate(config=config)
                    print(device.compare_config())
                    device.commit_config()
                print('Done')
        print('Waiting ' + str(cfg['scan-frequency']) + ' seconds to start over.')
        sleep(cfg['scan-frequency'])
