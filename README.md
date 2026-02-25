# Edwin AI Ansible Collection
<!-- Add CI and code coverage badges here. Samples included below. -->
[![CI](https://github.com/ansible-collections/logicmonitor.edwin_ai/workflows/CI/badge.svg?event=push)](https://github.com/ansible-collections/logicmonitor.edwin_ai/actions) [![Codecov](https://img.shields.io/codecov/c/github/ansible-collections/logicmonitor.edwin_ai)](https://codecov.io/gh/ansible-collections/logicmonitor.edwin_ai)

*Automate interactions with LogicMonitor’s Edwin AI services using Ansible.*

[Edwin AI][edwin-ai] is [LogicMonitor][logicmonitor]’s agentic AI-powered ITOps platform that surfaces intelligent insights.
It provides automation to proactively detect, diagnose, and remediate incidents thereby reducing alert noise and time to resolution.

This collection provides interactions with LogicMonitor’s Edwin AI enabling automation of incident response, AI-driven remediation steps, and operational tasks.

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

## Example Rulebooks

For examples, please refer to the individual plugins.
Each plugin must document itself and its parameters.
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

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.

[create-issue]: https://github.com/logicmonitor/logicmonitor.edwin_ai/issues/new
[edwin-ai]: https://www.logicmonitor.com/edwin-ai
[feature-request]: https://support.logicmonitor.com/hc/en-us/requests/new
[logicmonitor]: https://www.logicmonitor.com/
