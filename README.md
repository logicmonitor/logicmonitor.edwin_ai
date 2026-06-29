# Edwin AI Ansible Collection
<!-- Add CI and code coverage badges here. Samples included below. -->
[![CI](https://github.com/ansible-collections/logicmonitor.edwin_ai/workflows/CI/badge.svg?event=push)](https://github.com/ansible-collections/logicmonitor.edwin_ai/actions) [![Codecov](https://img.shields.io/codecov/c/github/ansible-collections/logicmonitor.edwin_ai)](https://codecov.io/gh/ansible-collections/logicmonitor.edwin_ai)

*Automate interactions with LogicMonitor's Edwin AI services using Ansible.*

[Edwin AI][edwin-ai] is [LogicMonitor][logicmonitor]'s agentic AI-powered ITOps platform that surfaces intelligent insights.
It provides automation to proactively detect, diagnose, and remediate incidents thereby reducing alert noise and time to resolution.

This collection provides interactions with LogicMonitor's Edwin AI enabling automation of incident response, AI-driven remediation steps, and operational tasks.

## Requirements

The plugins in this collection require API access to your EdwinAI portal.
Please contact your Edwin AI admin if you need new API tokens created for your account.

## Installation

### Installing the Collection from Ansible Galaxy

Before using this collection, you need to install it with the Ansible Galaxy command-line tool:
```bash
ansible-galaxy collection install logicmonitor.edwin_ai
```

You can also include it in a `requirements.yml` file and install it with `ansible-galaxy collection install -r requirements.yml`, using the format:
```yaml
---
collections:
  - name: logicmonitor.edwin_ai
```

Note that if you install the collection from Ansible Galaxy, it will not be upgraded automatically when you upgrade the `ansible` package. To upgrade the collection to the latest available version, run the following command:
```bash
ansible-galaxy collection install logicmonitor.edwin_ai --upgrade
```

You can also install a specific version of the collection, for example, if you need to downgrade when something is broken in the latest version (please [report an issue][create-issue] in this repository).
Use the following syntax to install version `0.1.0`:

```bash
ansible-galaxy collection install logicmonitor.edwin_ai:==0.1.0
```

See [using Ansible collections](https://docs.ansible.com/projects/ansible/devel/user_guide/collections_using.html) for more details.

## Event-Driven Ansible (EDA)

In addition to the `query_api` module (a "pull" model for querying Edwin AI), this collection ships
[Event-Driven Ansible][eda-docs] source plugins so Edwin AI can trigger Ansible automation in
response to alerts.

### Event source plugins

| Source | Pattern | Use case |
| --- | --- | --- |
| `logicmonitor.edwin_ai.webhook` | Edwin AI pushes to a listener | Real-time, simplest setup |
| `logicmonitor.edwin_ai.alerts` | EDA polls the Edwin AI API | Works behind firewalls; no inbound webhook |
| `logicmonitor.edwin_ai.kafka` | EDA consumes from a Kafka topic | High-volume enterprise deployments |

All three emit a normalized event under the `edwin_ai` key (e.g. `event.edwin_ai.host`,
`event.edwin_ai.message`, `event.edwin_ai.status`). Note that severity representation depends on the
source: the `webhook` source passes through the sender's value, while the `alerts` (polling) source
reports the integer `cf.eventSeverity` (higher is more severe). Write rulebook conditions to match
the source you use.

### Example rulebooks

Example rulebooks live in [`extensions/eda/rulebooks`](extensions/eda/rulebooks):

* The top-level rulebooks use the `run_playbook` action and are intended for the
  [`ansible-rulebook`][ansible-rulebook] CLI.
* The [`aap/`](extensions/eda/rulebooks/aap) variants use the `run_job_template` action for the
  AAP EDA controller (which does not support `run_playbook`). The referenced job templates must
  exist in the Automation Controller with "Prompt on launch" enabled for Variables.

### Two ingestion architectures for the webhook path

* **AAP gateway Event Stream:** point your sender at the gateway event-stream URL. AAP authenticates
  the request and forwards it to the rulebook; note that AAP replaces the rulebook's webhook source
  with its own, so the `webhook` plugin's normalization does not run (the rulebook sees the raw
  payload).
* **Raw webhook plugin:** the sender posts directly to the `webhook` plugin's listener, in which case
  the plugin runs and normalizes the payload into `event.edwin_ai.*`. When using HMAC, the plugin
  accepts the standard `X-Hub-Signature-256` header (with optional `sha256=` prefix) or the legacy
  `X-Edwin-Signature` header.

### Quick local test (CLI)

```bash
pip install ansible-rulebook ansible-runner ansible-core requests aiohttp aiokafka
ansible-galaxy collection install . --force
printf 'localhost ansible_connection=local\n' > inventory.ini
# EDWIN_PORTAL is the portal subdomain only (e.g. "mycompany"), not a URL
export EDWIN_PORTAL=mycompany EDWIN_ACCESS_ID=... EDWIN_ACCESS_KEY=...
ansible-rulebook --rulebook extensions/eda/rulebooks/alert_polling.yml -i inventory.ini \
  --env-vars EDWIN_PORTAL,EDWIN_ACCESS_ID,EDWIN_ACCESS_KEY --print-events
```

If any documentation is incorrect or incomplete, please [report an issue][create-issue] or submit a pull request.

## Release notes

See the [changelog](https://github.com/logicmonitor/logicmonitor.edwin_ai/blob/main/CHANGELOG.rst).

## Support

* For feature requests, please [submit a feature request][feature-request] for consideration in our product roadmap.
* For bugs, please [submit a feature request][feature-request] or [report an issue][create-issue] with a clear replication path.
   * Pull requests are also encouraged.
   However, a replication path is still required to validate the problematic behavior and the fix.
* For documentation issues, and other clerical edits, we gladly encourage pull requests!

## Licensing

Apache License, Version 2.0

See [LICENSE](https://github.com/logicmonitor/logicmonitor.edwin_ai/blob/main/LICENSE) to see the full text.

[ansible-rulebook]: https://ansible.readthedocs.io/projects/rulebook/
[create-issue]: https://github.com/logicmonitor/logicmonitor.edwin_ai/issues/new
[eda-docs]: https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/using_automation_decisions/index
[edwin-ai]: https://www.logicmonitor.com/edwin-ai
[feature-request]: https://support.logicmonitor.com/hc/en-us/requests/new
[logicmonitor]: https://www.logicmonitor.com/
