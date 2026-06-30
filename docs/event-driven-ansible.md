# Event-Driven Ansible (EDA)

This collection ships Event-Driven Ansible source plugins so Edwin AI can trigger Ansible automation in response to alerts.
This is complementary to the `query_api` module, which is a "pull" model.

## Source plugins

| Source | Pattern | Use case |
| --- | --- | --- |
| `logicmonitor.edwin_ai.webhook` | Edwin AI pushes to a listener | Real-time, simplest setup |
| `logicmonitor.edwin_ai.alerts` | EDA polls the Edwin AI API | Works behind firewalls; no inbound webhook |
| `logicmonitor.edwin_ai.kafka` | EDA consumes from a Kafka topic | High-volume enterprise deployments |

Events are emitted under the `edwin_ai` key (for example `event.edwin_ai.host`, `event.edwin_ai.status`).
Severity representation depends on the source.
The `webhook` source passes through the sender's value, while the `alerts` (polling) source reports the integer `cf.eventSeverity` (higher is more severe).
Write rulebook conditions to match the source you use.

## Example rulebooks

Example rulebooks live in [`../extensions/eda/rulebooks`](../extensions/eda/rulebooks).
The top-level rulebooks use the `run_playbook` action and are intended for the `ansible-rulebook` CLI.
The [`aap/`](../extensions/eda/rulebooks/aap) variants use the `run_job_template` action for the AAP EDA controller, which does not support `run_playbook`.

## Local testing with the `ansible-rulebook` CLI

Install the tooling and the collection from this checkout.
`ansible-core` provides `ansible-galaxy`, and `aiohttp`/`aiokafka` back the webhook/kafka sources.

```shell
pip install ansible-rulebook ansible-runner ansible-core requests aiohttp aiokafka
ansible-galaxy collection install . --force
```

`ansible-rulebook` requires an inventory file (the `localhost,` shorthand is not accepted).

```shell
printf 'localhost ansible_connection=local\n' > inventory.ini
```

Keep credentials in a vault-encrypted variables file rather than exporting them to your shell, where they can leak into shell history and process listings.
`EDWIN_PORTAL` is the portal subdomain only (for example `mycompany`), not a URL.

```shell
cat > vars.yml <<'YAML'
EDWIN_PORTAL: mycompany
EDWIN_ACCESS_ID: your-access-id
EDWIN_ACCESS_KEY: your-access-key
YAML
ansible-vault encrypt vars.yml
```

Run the polling source, supplying the vault password interactively.

```shell
ansible-rulebook --rulebook extensions/eda/rulebooks/alert_polling.yml \
  -i inventory.ini --vars vars.yml --ask-vault-pass --print-events
```

The polling source reports severity as the integer `cf.eventSeverity` (higher is more severe).
Tune the threshold and window with the `min_severity` and `lookback` source arguments.

To test the `webhook` source locally, start a rulebook whose source is `logicmonitor.edwin_ai.webhook`, then POST to the listener.

```shell
ansible-rulebook --rulebook extensions/eda/rulebooks/alert_remediation.yml \
  -i inventory.ini --print-events
```

```shell
curl -X POST http://127.0.0.1:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"id":"123","severity":"critical","host":"web-server-01","metric":"cpu","message":"High CPU"}'
```

When HMAC verification is enabled (set `token:` on the source), sign the raw body and send it as either `X-Hub-Signature-256: sha256=<hex>` or the legacy `X-Edwin-Signature: <hex>`.

```shell
printf '%s' '<exact-body>' | openssl dgst -sha256 -hmac '<token>'
```

## Testing on the AAP controller

The AAP EDA controller does not support `run_playbook`, so use the rulebooks under [`../extensions/eda/rulebooks/aap`](../extensions/eda/rulebooks/aap), which use `run_job_template`.

EDA source plugins must be present in the **Decision Environment** image.
A Project sync only delivers rulebooks, not the collection's plugin code.
The stock `de-minimal` Decision Environment does not include this collection, so activations using these sources fail with `SourcePluginNotFoundException` until you run them in a Decision Environment that has `logicmonitor.edwin_ai` installed.
Build one with `ansible-builder` from the published collection and register it under **Automation Decisions → Decision Environments**.

1. Create an EDA **Project** pointing at this repository.
2. In **Automation Execution → Templates** (the Automation Controller), create the Job Templates referenced by the rulebook.
   For a smoke test you can point them at the example [`../playbooks/debug_event.yml`](../playbooks/debug_event.yml), which prints the variables the rulebook passed.
   Select an actual playbook here, not a rulebook from `extensions/eda/rulebooks/`.
   Enable **Prompt on launch** for Variables so the `extra_vars` are accepted.
3. Create a **Rulebook Activation** using a Decision Environment that contains this collection, and select a rulebook from `aap/`.
   For the `webhook` rulebook, attach an **Event Stream** (HMAC credential) and map the source, or expose the activation port directly.
   For the `alerts`/`kafka` rulebooks, provide the required variables and credentials.
4. Send a test event and confirm the Job Template launches under **Jobs**.
