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

## Testing Event-Driven Ansible (EDA)

The collection ships EDA source plugins (`webhook`, `alerts`, `kafka`) and example rulebooks under
[`extensions/eda/rulebooks`](../extensions/eda/rulebooks). There are two ways to run them.

### Option 1: Local testing with the `ansible-rulebook` CLI

Use the top-level rulebooks (they use the `run_playbook` action, which is CLI-only).

```shell
# install tooling and the collection from this checkout
# (ansible-core provides ansible-galaxy; aiohttp/aiokafka back the webhook/kafka sources)
pip install ansible-rulebook ansible-runner ansible-core requests aiohttp aiokafka
ansible-galaxy collection install . --force

# ansible-rulebook needs an inventory FILE (not the `localhost,` shorthand)
printf 'localhost ansible_connection=local\n' > inventory.ini

# polling source (pulls from the Edwin AI API; no inbound webhook needed)
# EDWIN_PORTAL is the portal subdomain only (e.g. "mycompany"), not a URL
export EDWIN_PORTAL=mycompany EDWIN_ACCESS_ID=... EDWIN_ACCESS_KEY=...
ansible-rulebook --rulebook extensions/eda/rulebooks/alert_polling.yml -i inventory.ini \
  --env-vars EDWIN_PORTAL,EDWIN_ACCESS_ID,EDWIN_ACCESS_KEY --print-events
```

The polling source reports severity as the integer `cf.eventSeverity` (higher is more severe); tune
with the `min_severity` and `lookback` source arguments.

To test the `webhook` source locally, run a rulebook whose source is
`logicmonitor.edwin_ai.webhook`, then POST to the listener:

```shell
# in one terminal, start a rulebook with a webhook source on port 5000
ansible-rulebook --rulebook extensions/eda/rulebooks/alert_remediation.yml -i inventory.ini --print-events

# in another terminal, send a (flat) test payload
curl -X POST http://127.0.0.1:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"id":"123","severity":"critical","host":"web-server-01","metric":"cpu","message":"High CPU"}'
```

When HMAC is enabled (set `token:` on the source), sign the raw body and send it as either
`X-Hub-Signature-256: sha256=<hex>` or `X-Edwin-Signature: <hex>`:

```shell
printf '%s' '<exact-body>' | openssl dgst -sha256 -hmac '<token>'
```

### Option 2: Testing on the AAP controller

The AAP EDA controller does **not** support `run_playbook`; use the rulebooks under
[`extensions/eda/rulebooks/aap`](../extensions/eda/rulebooks/aap) (they use `run_job_template`).

> **Decision Environment requirement:** EDA source plugins must be present in the **Decision
> Environment** image — a Project sync only delivers rulebooks, not the collection's plugin code. The
> stock `de-minimal` DE does not include this collection, so activations using these sources fail with
> `SourcePluginNotFoundException` until you run them in a DE that has `logicmonitor.edwin_ai` installed
> (build one with `ansible-builder` from the published collection and register it under **Automation
> Decisions → Decision Environments**).

1. Create an EDA **Project** pointing at this repository.
2. In the **Automation Controller** (the **Automation Execution** section in AAP 2.5+) →
   **Templates**, create the Job Templates referenced by the rulebook. For a smoke
   test you can point them at the example [`playbooks/debug_event.yml`](../playbooks/debug_event.yml),
   which just prints the variables the rulebook passed. (Select an actual playbook here, **not** a
   rulebook from `extensions/eda/rulebooks/`.) Enable **Prompt on launch** for Variables so the
   `extra_vars` are accepted (set `include_events: false` only if you do not want the full matching
   event injected alongside them).
3. Create a **Rulebook Activation** selecting a rulebook from `aap/`.
   * For the `webhook` rulebook, attach an **Event Stream** (HMAC credential) and map the source, or
     expose the activation port directly.
   * For the `alerts`/`kafka` rulebooks, provide the required variables/credentials.
4. Send a test event (e.g. `curl` to the event stream URL, or via your event sender) and confirm the
   Job Template launches under **Jobs**.

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
