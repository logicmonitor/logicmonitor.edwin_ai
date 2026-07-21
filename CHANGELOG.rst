==============================================
LogicMonitor Edwin AI Collection Release Notes
==============================================

.. contents:: Topics

v1.2.0
======

Release Summary
---------------

Packaging and documentation release for Red Hat Automation Hub certification. Adds a populated changelog, uses absolute README links so the page renders correctly outside the repository, documents Automation Hub support, and trims non-user-facing files from the built collection artifact.

Minor Changes
-------------

- docs - the README now links to the Event-Driven Ansible documentation using an absolute URL and adds a Red Hat Automation Hub support statement.
- packaging - exclude non-user-facing files (for example ``codecov.yml``, ``sample_playbook.yml``, ``REVIEW_CHECKLIST.md``, ``SECURITY.md``, ``MAINTAINERS``, and editor/config directories) from the built collection via ``build_ignore``.

v1.1.0
======

Release Summary
---------------

Make Event-Driven Ansible usable on Ansible Automation Platform and the ansible-rulebook CLI. Adds AAP-ready rulebooks, aligns webhook HMAC with standard headers, fixes alert polling against the real Edwin AI query API, and documents EDA setup and testing.

Minor Changes
-------------

- eda rulebooks - add AAP-ready example rulebooks under ``extensions/eda/rulebooks/aap/`` that use ``run_job_template`` (supported by the AAP EDA controller), alongside the existing ``ansible-rulebook`` CLI examples that use ``run_playbook``. Includes a raw-payload variant for the AAP gateway Event Stream path.
- playbooks - add an example ``playbooks/debug_event.yml`` that prints the variables passed by a rulebook, so AAP job templates triggered by EDA have a runnable smoke-test target.
- webhook event source - accept the standard ``X-Hub-Signature-256`` HMAC header (with optional ``sha256=`` prefix) in addition to the legacy ``X-Edwin-Signature`` header for signature verification.

Bugfixes
--------

- alerts (polling) event source - query the real Edwin AI endpoint ``POST /ui/query/records`` (as the ``query_api`` module does) instead of the non-existent ``GET /api/v1/alerts`` that returned HTTP 404, and read records from ``results``. Normalize using the real record keys (``cf.*``/``meta.*``/``alertDetails.*``); ``severity`` is now the integer ``cf.eventSeverity``. Adds ``min_severity`` (integer threshold) and ``lookback`` arguments.
- requirements - declare the ``aiohttp`` and ``aiokafka`` runtime dependencies needed by the webhook and kafka event sources in ``requirements.txt`` and ``meta/ee-requirements.txt``.
- webhook event source - guard the optional ``aiohttp`` import so module import (and sanity/import checks) no longer fail when the dependency is absent.
