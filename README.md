# general2proxmox

This is a small script for migrating Ansible Proxmox modules from
[community.general][github-general] to [community.proxmox][github-proxmox].

The intent is to informally document the git migration process and to provide an
easy way to reproduce the filtered source repository if needed.  It is kept
separate to avoid polluting those source trees.

## Usage

See `./src/main.py --help`.

<!-- lilnks -->

[github-general]: (https://github.com/ansible-collections/community.general.git)
[github-proxmox]: (https://github.com/ansible-collections/community.proxmox.git)
