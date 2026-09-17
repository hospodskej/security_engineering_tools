# SOP: Phishing Email Investigation

## Scope
This procedure applies to all emails reported by users, flagged by automated systems, or discovered during threat hunting.

## Prerequisites
- Access to the original `.eml` file
- Python 3.9+ with `phishing-email-analysis` toolkit installed (`uv sync`)
- Internet access for DNS and GeoIP lookups

## Investigation Steps

### 1. Obtain the email
Save the message as `.eml` from Outlook (File → Save As), Gmail (Show original → Download), or export from quarantine.

### 2. Run automated analysis
```bash
uv run python -m analyzer.email_analyzer <path/to/email.eml>
```

This generates a Markdown report in the reports/ directory.

### 3. Review the report
- **Spoofing & Origin:** If domain mismatch is flagged, escalate immediately.
- **Authentication:** Check SPF, DKIM, DMARC results. Missing or failed records are strong phishing indicators.
- **URLs:** Submit defanged URLs to sandbox (VirusTotal, urlscan.io).
- **Attachments:** If present, compute SHA256 and check against threat intelligence.

### 4. Manual correlation
- Check sender IP against AbuseIPDB or internal threat intel.
- Verify any domains in URLs against phishing blocklists.
- Search SIEM for other recipients of the same campaign (pivot on sender IP, domain, or Message-ID).

### 5. Classification
- **Phishing:** Clear deception, credential harvesting, or domain spoofing.
- **Spam:** Unwanted but no immediate threat.
- **Legitimate:** False positive — release from quarantine.

### 6. Response
- Block sender IP and domain at email gateway.
- Purge the email from all user inboxes.
- If credential compromise is suspected, force password reset for affected users.
- Document findings in case management system.

### 7. Reporting
- Provide technical report to SOC with all indicators.
- Provide simplified summary to end-user: do not click links, do not reply, report to IT.

---
