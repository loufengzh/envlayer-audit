# Security

Do not attach real environment files, credentials, sensitive filenames or private
configuration keys to public issues. Use synthetic fixtures and sanitized output.
For a suspected value disclosure, use the repository's private vulnerability
reporting option if enabled; otherwise contact the maintainer privately through
their published profile contact rather than opening a public issue with secrets.
There is no guaranteed response SLA or audited security certification.

The tool minimizes output, but reads input into memory. Valid key names are
intentionally public in reports. It does not encrypt files, scan for secrets,
validate application configuration or securely erase memory. Input values are
never executed. Avoid running it on untrusted, excessively large files.
