#!/usr/bin/env python3

import email
import email.policy
import sys
import os
import re
import base64
import quopri
from datetime import datetime
from email.header import decode_header
from analyzer.helpers import (
    extract_domain,
    extract_domains_from_url,
    check_spf,
    check_dkim,
    check_dmarc,
    get_geoip,
    defang_url,
    load_config,
)


class EmailAnalyzer:
    def __init__(self, eml_path):
        self.eml_path = eml_path
        self.raw_msg = None
        self.headers = {}
        self.body_plain = ""
        self.body_html = ""
        self.urls = []
        self.attachments = []
        self.config = load_config()

    def parse(self):
        with open(self.eml_path, 'rb') as f:
            self.raw_msg = email.message_from_binary_file(
                f, policy=email.policy.default
            )

        # Core headers
        self.headers['From'] = self.raw_msg['From']
        self.headers['Return-Path'] = self.raw_msg['Return-Path']
        self.headers['Reply-To'] = self.raw_msg['Reply-To']
        self.headers['Subject'] = self.raw_msg['Subject']
        self.headers['Date'] = self.raw_msg['Date']
        self.headers['Message-ID'] = self.raw_msg['Message-ID']
        self.headers['Received'] = self.raw_msg.get_all('Received', [])
        self.headers['DKIM-Signature'] = self.raw_msg.get_all('DKIM-Signature', [])
        self.headers['Authentication-Results'] = self.raw_msg.get_all(
            'Authentication-Results', []
        )
        self.headers['ARC-Authentication-Results'] = self.raw_msg.get_all(
            'ARC-Authentication-Results', []
        )
        self.headers['X-Sender-IP'] = self.raw_msg.get('X-Sender-IP')
        self.headers['X-MS-Exchange-Organization-SCL'] = self.raw_msg.get(
            'X-MS-Exchange-Organization-SCL'
        )
        self.headers['X-MS-Exchange-Organization-PCL'] = self.raw_msg.get(
            'X-MS-Exchange-Organization-PCL'
        )
        self.headers['X-Microsoft-Antispam'] = self.raw_msg.get('X-Microsoft-Antispam')

        # Body extraction
        if self.raw_msg.is_multipart():
            for part in self.raw_msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition', ''))
                if 'attachment' in disposition:
                    self.attachments.append({
                        'filename': part.get_filename(),
                        'content_type': content_type,
                        'size': len(part.get_payload(decode=True) or b''),
                    })
                elif content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        self.body_plain = payload.decode(
                            part.get_content_charset() or 'utf-8', errors='replace'
                        )
                elif content_type == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        self.body_html = payload.decode(
                            part.get_content_charset() or 'utf-8', errors='replace'
                        )
        else:
            transfer_encoding = self.raw_msg.get('Content-Transfer-Encoding', '').lower()
            payload = self.raw_msg.get_payload()
            charset = self.raw_msg.get_content_charset() or 'utf-8'

            if transfer_encoding == 'base64':
                try:
                    decoded = base64.b64decode(payload)
                    self.body_html = decoded.decode(charset, errors='replace')
                except Exception:
                    self.body_html = payload
            elif transfer_encoding == 'quoted-printable':
                try:
                    decoded = quopri.decodestring(payload)
                    self.body_html = decoded.decode(charset, errors='replace')
                except Exception:
                    self.body_html = payload
            else:
                self.body_html = payload

        # Extract URLs from all text
        all_text = self.body_plain + self.body_html
        url_pattern = r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+'
        raw_urls = re.findall(url_pattern, all_text, re.IGNORECASE)
        self.urls = list(set(raw_urls))[: self.config.get('max_url_checks', 5)]

    def analyze_spoofing(self):
        from_domain = extract_domain(self.headers.get('From'))
        ret_domain = extract_domain(self.headers.get('Return-Path'))
        reply_to_domain = extract_domain(self.headers.get('Reply-To'))

        mismatch = False
        mismatch_reason = ""
        if from_domain and ret_domain and from_domain != ret_domain:
            mismatch = True
            mismatch_reason = (
                f"From domain ({from_domain}) differs from "
                f"Return-Path domain ({ret_domain})"
            )

        # Extract first external sender IP
        sender_ip = None
        # Prefer X-Sender-IP if present
        if self.headers.get('X-Sender-IP'):
            sender_ip = self.headers['X-Sender-IP']
        else:
            # Fall back to parsing Received headers
            for rcvd in self.headers.get('Received', []):
                ip_match = re.search(
                    r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]', rcvd
                )
                if ip_match:
                    sender_ip = ip_match.group(1)
                    break

        return {
            'from_domain': from_domain,
            'return_path_domain': ret_domain,
            'reply_to_domain': reply_to_domain,
            'sender_ip': sender_ip,
            'domain_mismatch': mismatch,
            'mismatch_reason': mismatch_reason,
        }

    def analyze_auth(self, spoof_info):
        domain = spoof_info.get('from_domain')
        sender_ip = spoof_info.get('sender_ip')
        auth = {}

        if domain:
            auth['spf'] = check_spf(domain, sender_ip)

            # Try multiple common DKIM selectors
            selectors = ['default', 'google', 'selector1', 'selector2']
            dkim_results = []
            for sel in selectors:
                dkim = check_dkim(domain, sel)
                if dkim['found']:
                    dkim_results.append(dkim)
            auth['dkim'] = dkim_results if dkim_results else [{'found': False}]

            auth['dmarc'] = check_dmarc(domain)

        return auth

    def decode_header_value(self, value):
        """Decode RFC 2047 encoded header values."""
        if not value:
            return ''
        try:
            parts = decode_header(value)
            decoded = ''
            for part, charset in parts:
                if isinstance(part, bytes):
                    decoded += part.decode(charset or 'utf-8', errors='replace')
                else:
                    decoded += part
            return decoded
        except Exception:
            return str(value)

    def generate_report(self, spoof_info, auth_info):
        lines = []
        lines.append("# Phishing Email Analysis Report")
        lines.append("")
        lines.append(f"**File:** `{os.path.basename(self.eml_path)}`")
        lines.append(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Analyst:** DFIR Team")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 1. Email Metadata")
        lines.append("")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| From | `{self.headers.get('From', 'N/A')}` |")
        lines.append(f"| Return-Path | `{self.headers.get('Return-Path', 'N/A')}` |")
        lines.append(f"| Reply-To | `{self.headers.get('Reply-To', 'N/A')}` |")
        lines.append(f"| Subject | {self.decode_header_value(self.headers.get('Subject', 'N/A'))} |")
        lines.append(f"| Date | {self.headers.get('Date', 'N/A')} |")
        lines.append(f"| Message-ID | `{self.headers.get('Message-ID', 'N/A')}` |")
        lines.append("")
        lines.append("### Received Chain (Delivery Path)")
        lines.append("```")
        for i, rcvd in enumerate(self.headers.get('Received', [])[:5]):
            lines.append(f"[{i+1}] {rcvd.strip()}")
        lines.append("```")
        lines.append("")
        lines.append("## 2. Spoofing & Origin Analysis")
        lines.append("")
        lines.append(f"- **From domain:** `{spoof_info['from_domain']}`")
        lines.append(f"- **Return-Path domain:** `{spoof_info['return_path_domain']}`")
        lines.append(f"- **Reply-To domain:** `{spoof_info['reply_to_domain']}`")
        lines.append(f"- **Sender IP:** `{spoof_info['sender_ip']}`")
        if spoof_info['sender_ip']:
            geo = get_geoip(spoof_info['sender_ip'])
            lines.append(f"- **GeoIP:** {geo}")
        lines.append("")
        if spoof_info['domain_mismatch']:
            lines.append(f"⚠️ **Domain mismatch detected:** {spoof_info['mismatch_reason']}")
        else:
            lines.append("✅ No domain mismatch between From and Return-Path.")
        lines.append("")
        lines.append("## 3. Authentication Records")
        lines.append("")

        spf = auth_info.get('spf', {})
        lines.append("### SPF")
        lines.append(f"- Record: `{spf.get('record', 'N/A')}`")
        lines.append(f"- Valid: **{spf.get('valid', False)}**")
        lines.append(f"- Reason: {spf.get('reason', '')}")
        lines.append("")

        lines.append("### DKIM")
        dkim_results = auth_info.get('dkim', [])
        if any(d.get('found') for d in dkim_results):
            for dkim in dkim_results:
                if dkim.get('found'):
                    lines.append(
                        f"- Selector `{dkim['selector']}`: "
                        f"`{dkim['record'][:100]}...`"
                    )
        else:
            lines.append("- No DKIM record found on common selectors.")
        lines.append("")

        dmarc = auth_info.get('dmarc')
        lines.append("### DMARC")
        if dmarc:
            lines.append(f"- Policy: `{dmarc['policy']}`")
            if dmarc.get('sub_policy'):
                lines.append(f"- Subdomain policy: `{dmarc['sub_policy']}`")
            lines.append(f"- Percentage: {dmarc['pct']}%")
            lines.append(f"- Full record: `{dmarc['record']}`")
        else:
            lines.append("- **No DMARC record found.**")
        lines.append("")

        lines.append("### Original Authentication Results (from headers)")
        auth_headers = self.headers.get('Authentication-Results', [])
        if auth_headers:
            for ar in auth_headers:
                lines.append(f"```\n{ar.strip()}\n```")
        else:
            lines.append("No Authentication-Results header present.")
        lines.append("")

        # Exchange-specific headers
        scl = self.headers.get('X-MS-Exchange-Organization-SCL')
        pcl = self.headers.get('X-MS-Exchange-Organization-PCL')
        antispam = self.headers.get('X-Microsoft-Antispam')
        if any([scl, pcl, antispam]):
            lines.append("### Exchange Online Protection Scores")
            if scl:
                lines.append(f"- **SCL (Spam Confidence Level):** {scl} (0-9, higher = more likely spam)")
            if pcl:
                lines.append(f"- **PCL (Phishing Confidence Level):** {pcl} (0-8, higher = more likely phishing)")
            if antispam:
                lines.append(f"- **Antispam BCL:** {antispam}")
            lines.append("")

        lines.append("## 4. Extracted URLs")
        lines.append("")
        if self.urls:
            for url in self.urls:
                defanged = defang_url(url)
                domain = extract_domains_from_url(url)
                lines.append(f"- `{defanged}`")
                if domain:
                    lines.append(f"  → Domain: `{domain}`")
        else:
            lines.append("No URLs extracted.")
        lines.append("")

        lines.append("## 5. Attachments")
        lines.append("")
        if self.attachments:
            for att in self.attachments:
                lines.append(
                    f"- **{att['filename']}** ({att['content_type']}, "
                    f"{att['size']} bytes)"
                )
        else:
            lines.append("No attachments found.")
        lines.append("")

        lines.append("## 6. Verdict & Recommendations")
        lines.append("")

        # Determine verdict based on evidence
        verdict_reasons = []
        if spoof_info['domain_mismatch']:
            verdict_reasons.append("Domain mismatch between From and Return-Path")
        if self.urls:
            verdict_reasons.append("Email contains clickable URLs")
        if auth_info.get('dmarc') is None:
            verdict_reasons.append("No DMARC record configured for sender domain")
        if not any(d.get('found') for d in auth_info.get('dkim', [])):
            verdict_reasons.append("No DKIM signature verified")

        if verdict_reasons:
            lines.append("**Verdict: HIGH CONFIDENCE PHISHING**")
            lines.append("")
            lines.append("Evidence:")
            for reason in verdict_reasons:
                lines.append(f"- {reason}")
        else:
            lines.append("**Verdict: INCONCLUSIVE** – Requires manual review.")

        lines.append("")
        lines.append("### For SOC Team")
        lines.append("- Block sender IP (`{}`) at email gateway.".format(
            spoof_info.get('sender_ip', 'N/A')
        ))
        lines.append("- Block sender domain (`{}`).".format(
            spoof_info.get('return_path_domain', 'N/A')
        ))
        if self.urls:
            lines.append("- Submit extracted URLs to sandbox (VirusTotal, urlscan.io).")
        lines.append("- Search SIEM for other recipients of this campaign.")
        lines.append("")
        lines.append("### For End-Users")
        lines.append("- **Do not click any links** in this email.")
        lines.append("- **Do not reply** to the sender.")
        lines.append("- Report this email to IT Security immediately.")
        lines.append("- If you entered credentials, reset your password now.")
        lines.append("")
        lines.append("---")
        lines.append(
            f"*Report generated by phishing-email-analysis toolkit on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        )

        return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python -m analyzer.email_analyzer <path_to_eml>")
        sys.exit(1)

    eml_path = sys.argv[1]
    if not os.path.exists(eml_path):
        print(f"Error: File not found: {eml_path}")
        sys.exit(1)

    print(f"[*] Analyzing: {eml_path}")
    eml = EmailAnalyzer(eml_path)
    eml.parse()
    print("[*] Email parsed successfully.")
    spoof = eml.analyze_spoofing()
    print("[*] Spoofing analysis complete.")
    auth = eml.analyze_auth(spoof)
    print("[*] Authentication checks complete.")
    report = eml.generate_report(spoof, auth)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # Save report
    os.makedirs('reports', exist_ok=True)
    name = os.path.splitext(os.path.basename(eml_path))[0]
    report_path = f'reports/{name}_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n✅ Report saved to {report_path}")


if __name__ == '__main__':
    main()
