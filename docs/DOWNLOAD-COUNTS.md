# Download counts

Run `python3 scripts/download-stats.py` from the source checkout. No admin access or token is required for a public repository.

The report reads GitHub's release asset counters, grouped by version and package. It excludes install.sh, setup executables and checksum files so the stages of one installation are not incorrectly added together.

Counters may take time to update after a download.

These are **package downloads, not installed apps or unique users**. Retries, manual downloads, updates and maintainer tests are included. A download may never be installed. Counts start before public launch if the asset was used in private testing.

Notryn does not send installation, usage, note or device telemetry. There is no install-tracking endpoint or user identifier.
