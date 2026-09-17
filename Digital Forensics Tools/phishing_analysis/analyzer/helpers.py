import re
import requests
import tldextract
import dns.resolver
import yaml
import os
from datetime import datetime


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def extract_domain(email_or_header):
    """Extract domain from a From, Return-Path, or Reply-To header."""
    if not email_or_header:
        return None
    # Match addresses like user@domain.com or <user@domain.com>
    match = re.search(r'<?([^@\s<>]+@[^@\s<>]+)>?', email_or_header)
    if match:
        addr = match.group(1).strip('<>')
        parts = addr.split('@')
        if len(parts) == 2:
            return parts[1].lower().strip('>')
    return None


def extract_domains_from_url(url):
    """Extract registrable domain from a full URL."""
    try:
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}"
    except Exception:
        return None


def check_spf(domain, sender_ip=None):
    """Query SPF TXT record for a domain."""
    try:
        answers = dns.resolver.resolve(domain, 'TXT')
        spf_record = None
        for rdata in answers:
            txt = rdata.to_text().strip('"')
            if txt.startswith('v=spf1'):
                spf_record = txt
                break
        if not spf_record:
            return {'record': None, 'valid': False, 'reason': 'No SPF record found'}
        return {
            'record': spf_record,
            'valid': True,
            'reason': 'Record exists (manual IP verification required)'
        }
    except dns.resolver.NXDOMAIN:
        return {'record': None, 'valid': False, 'reason': f'Domain {domain} does not exist'}
    except dns.resolver.NoAnswer:
        return {'record': None, 'valid': False, 'reason': 'No TXT records found'}
    except Exception as e:
        return {'record': None, 'valid': False, 'reason': str(e)}


def check_dkim(domain, selector='default'):
    """Query DKIM TXT record at selector._domainkey.domain."""
    try:
        query = f"{selector}._domainkey.{domain}"
        answers = dns.resolver.resolve(query, 'TXT')
        dkim_record = ''.join([r.to_text().strip('"') for r in answers])
        return {'selector': selector, 'record': dkim_record, 'found': True}
    except Exception:
        return {'selector': selector, 'found': False}


def check_dmarc(domain):
    """Query _dmarc.domain TXT record and extract policy."""
    try:
        query = f"_dmarc.{domain}"
        answers = dns.resolver.resolve(query, 'TXT')
        dmarc_record = ''.join([r.to_text().strip('"') for r in answers])
        policy = 'none'
        sub_policy = None
        pct = 100
        for part in dmarc_record.split(';'):
            part = part.strip()
            if part.startswith('p='):
                policy = part[2:]
            elif part.startswith('sp='):
                sub_policy = part[3:]
            elif part.startswith('pct='):
                try:
                    pct = int(part[4:])
                except ValueError:
                    pass
        return {
            'record': dmarc_record,
            'policy': policy,
            'sub_policy': sub_policy,
            'pct': pct
        }
    except Exception:
        return None


def get_geoip(ip):
    """Geo-IP lookup using ip-api.com (free, no key)."""
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return (
                f"{data.get('city', 'Unknown')}, "
                f"{data.get('country', 'Unknown')} "
                f"({data.get('isp', 'Unknown ISP')})"
            )
    except Exception:
        return "GeoIP lookup failed"


def defang_url(url):
    """Replace protocols and dots for safe reporting."""
    return url.replace('http', 'hxxp').replace('.', '[.]')
