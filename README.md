# auto-port-config
 Script to help configure ports during commissioning.


## Requirements

- python3.9
- rich
- napalm
- ciscoconfparse
- yamlarg

## Usage

```text
python3.9 ./src/auto_port_config.py --help
usage: auto_port_config.py [-h] [--cfg CFG] [--interface INTERFACE] [--dry-run] [--cfg-only]

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
  --cfg-only            Only scan the 'configuration'/'default' vlan. (Much faster.)

```

## Building

```bash
sudo rm -r dist
python3.9 -m poetry build
```

## Changelog

### 0.1.0 Updates for efficiency and bug fixes
- Apply the config changes for all interfaces on a switch at the same time. (significant speed-up when many interfaces come online at one time.)
- Add filtering to arp-scan results, to remove entries that are returned on an incorrect vlan.
- Add an option to only scan the configuration/default vlan. Without this/by default it scans for devices on incorrect vlans.

### 0.0.0 Initial Commit