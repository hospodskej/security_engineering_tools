# Phishing Email Analysis Toolkit

A Python-based framework for standardized investigation of phishing emails. Built for SOC analysts and DFIR teams to streamline triage, header analysis, authentication validation, and reporting.

## Features

- Parses `.eml` files (multipart, base64, quoted-printable, 7bit, 8bit)
- Extracts and analyzes all email headers
- Detects display name and domain spoofing (From vs Return-Path vs Reply-To)
- Validates SPF, DKIM, and DMARC records via live DNS queries
- Geo-locates sender IP address
- Extracts and defangs URLs from HTML and plain text bodies
- Reads Exchange Online Protection spam/phishing scores (SCL, PCL, BCL)
- Generates detailed Markdown reports with verdict and actionable recommendations

## Samples

**bradesco_livelo_phish.eml**
- Type: Credential harvester (bank rewards scam)
- Language: Portuguese
- Indicators: Domain mismatch, SPF fail, DMARC missing, DigitalOcean VPS origin

**microsoft_unusual_signin.eml**
- Type: Credential harvester (Microsoft account)
- Language: English
- Indicators: Domain mismatch, Reply-To Gmail, SPF none, DKIM none, tracking pixel

**zonnepanelen_phish.eml**
- Type: Data collection scam (solar panel quotes)
- Language: Dutch
- Indicators: Three-domain mismatch, SPF none, DKIM none, DMARC none, click tracker

## Investigation Workflow

1. Obtain the email in `.eml` format
2. Run: `uv run python -m analyzer.email_analyzer <path/to/email.eml>`
3. Review the generated report
4. Escalate based on findings (see `SOP.md` for full procedure)

## License

MIT
