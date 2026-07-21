# LogicMonitor Edwin AI Collection Release Notes

**Topics**

- <a href="#v1-2-0">v1\.2\.0</a>
    - <a href="#release-summary">Release Summary</a>
    - <a href="#minor-changes">Minor Changes</a>
- <a href="#v1-1-0">v1\.1\.0</a>
    - <a href="#release-summary-1">Release Summary</a>
    - <a href="#minor-changes-1">Minor Changes</a>
    - <a href="#bugfixes">Bugfixes</a>

<a id="v1-2-0"></a>
## v1\.2\.0

<a id="release-summary"></a>
### Release Summary

Packaging and documentation release for Red Hat Automation Hub certification\. Adds a populated changelog\, uses absolute README links so the page renders correctly outside the repository\, documents Automation Hub support\, and trims non\-user\-facing files from the built collection artifact\.

<a id="minor-changes"></a>
### Minor Changes

* docs \- the README now links to the Event\-Driven Ansible documentation using an absolute URL and adds a Red Hat Automation Hub support statement\.
* packaging \- exclude non\-user\-facing files \(for example <code>codecov\.yml</code>\, <code>sample\_playbook\.yml</code>\, <code>REVIEW\_CHECKLIST\.md</code>\, <code>SECURITY\.md</code>\, <code>MAINTAINERS</code>\, and editor/config directories\) from the built collection via <code>build\_ignore</code>\.

<a id="v1-1-0"></a>
## v1\.1\.0

<a id="release-summary-1"></a>
### Release Summary

Make Event\-Driven Ansible usable on Ansible Automation Platform and the ansible\-rulebook CLI\. Adds AAP\-ready rulebooks\, aligns webhook HMAC with standard headers\, fixes alert polling against the real Edwin AI query API\, and documents EDA setup and testing\.

<a id="minor-changes-1"></a>
### Minor Changes

* eda rulebooks \- add AAP\-ready example rulebooks under <code>extensions/eda/rulebooks/aap/</code> that use <code>run\_job\_template</code> \(supported by the AAP EDA controller\)\, alongside the existing <code>ansible\-rulebook</code> CLI examples that use <code>run\_playbook</code>\. Includes a raw\-payload variant for the AAP gateway Event Stream path\.
* playbooks \- add an example <code>playbooks/debug\_event\.yml</code> that prints the variables passed by a rulebook\, so AAP job templates triggered by EDA have a runnable smoke\-test target\.
* webhook event source \- accept the standard <code>X\-Hub\-Signature\-256</code> HMAC header \(with optional <code>sha256\=</code> prefix\) in addition to the legacy <code>X\-Edwin\-Signature</code> header for signature verification\.

<a id="bugfixes"></a>
### Bugfixes

* alerts \(polling\) event source \- query the real Edwin AI endpoint <code>POST /ui/query/records</code> \(as the <code>query\_api</code> module does\) instead of the non\-existent <code>GET /api/v1/alerts</code> that returned HTTP 404\, and read records from <code>results</code>\. Normalize using the real record keys \(<code>cf\.\*</code>/<code>meta\.\*</code>/<code>alertDetails\.\*</code>\)\; <code>severity</code> is now the integer <code>cf\.eventSeverity</code>\. Adds <code>min\_severity</code> \(integer threshold\) and <code>lookback</code> arguments\.
* requirements \- declare the <code>aiohttp</code> and <code>aiokafka</code> runtime dependencies needed by the webhook and kafka event sources in <code>requirements\.txt</code> and <code>meta/ee\-requirements\.txt</code>\.
* webhook event source \- guard the optional <code>aiohttp</code> import so module import \(and sanity/import checks\) no longer fail when the dependency is absent\.
