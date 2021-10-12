# auto-port-config
 Script to help configure ports during commissioning.


## Requirements

- python3.9
- rich
- napalm
- ciscoconfparse
- yamlarg

## Usage

```bash
python3.9 ./src/auto_port_config.py --help
usage: auto_port_config.py [-h] [--cfg CFG] [--interface INTERFACE] [--dry-run]

This script is used to provision ports from a default vlan to the correct vlan. 
The input should be a configuration file in the following format.
default-vlan: 1
scan-frequency: 60 #60 seconds
networks:
# ip/cidr: vlan
  192.168.2.1/24: 2
  192.168.3.1/24: 3
sw-defaults: # this section can be left out if you provide environment variables SW_USERNAME and SW_PASSWORD
  user: username
  pass: password
switches:
  - 192.168.1.1
  - 192.168.1.2
  - 192.168.1.3

This should be ran connected to a trunk interface, and specifying the interface name.

Example usage.
auto_port_config.py --interface=ens33 --cfg=./cfg.yaml

optional arguments:
  -h, --help            show this help message and exit
  --cfg CFG             Location of the configuration file.
  --interface INTERFACE
                        Trunk interface for scanning.
  --dry-run             Do not modify the switch configurations.

```

## Changelog

### 0.0.0 Initial Commit