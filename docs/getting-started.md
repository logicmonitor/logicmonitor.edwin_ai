# Getting Started

This is a guide to bootstrap contributors.
There's a wealth of Ansible documentation, and these steps help cut to the chase.

## Install Ansible

On Mac:
```shell
brew install ansible
```

This should install the following binaries:
1. ansible-galaxy
1. ansible-playbook
1. ansible-test
1. ansible-vault

## Create Edwin API Token

If you don't already have an API token, you may need to create one.
Assuming you have sufficient permissions, you can create your own inside the EdwinUI portal:
1. Navigate to "Settings > API Credentials".
1. Click "Create" (in upper-right corner).
1. Provide an appropriate description and select the following scopes (at the least):
    * query_records
1. Persist the secret somewhere so you don't lose it.
(Or continue to the section on [Ansible vault][ansible-vault].)

## Create Ansible Vault

[Ansible vault][ansible-vault] is a mechanism to securely encrypt and leverage sekrits.
It is **strongly encouraged** that devs follow this practice to avoid accidentally commiting a secret to the repo.

```shell
# create vault
ansible-vault create vault.yml

# edit vault
ansible-vault edit vault.yml
```

The vault structure should look like:
```yaml
---
edwin_access_id: ...
edwin_access_key: ...
```

## Local Testing

While testing may vary depending on your needs, the following provides a basic test loop.
These commands are to be executed in the project root directory (i.e., [./](../)):
```
# create the collection; add '-f' to force on successive builds
ansible-galaxy collection build

# install the collection locally; add '-f' to force
ansible-galaxy collection install path/to/tarball -p collections/
```

Once the collection is accessible, you can execute a playbook against it:
```shell
ansible-playbook sample_playbook --ask-vault-pass
```

## Publication

After merging code to the repo, the collection should be republished.
This does not happen automatically.

To publish, you'll need an Ansible API token from [Ansible galaxy][ansible-galaxy]:
1. Click "Login" (in upper-right corner).
1. Follow the instructions to link Galaxy to your GitHub account.
1. Once logged in, navigate to "Collections > API token".
1. Click "Load token".
   * Persist this token so you don't lose it.
   Stashing the token in your [vault](#create-ansible-vault) is encouraged.

Assuming you have an artifact that is built from `main` (with the new changes):
```shell
ansible-galaxy collection publish path/to/tarball --token <galaxy api token>
```

[ansible-galaxy]: https://galaxy.ansible.com/
[ansible-vault]: https://docs.ansible.com/projects/ansible/latest/vault_guide/index.html
