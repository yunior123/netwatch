#!/usr/bin/env python3
"""NVIDIA NIM integration for netwatch — AI-powered URL/activity analysis.

Uses NVIDIA NIM API to analyze network traffic patterns and flag suspicious activity.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# NIM API configuration
NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL = "deepseek-ai/deepseek-v4-flash-0731"

HEADERS = {
    "Authorization": f"Bearer {NIM_API_KEY}",
    "Content-Type": "application/json",
}

def analyze_urls(events, devices=None):
    """Analyze a batch of network events and flag suspicious activity."""
    if not NIM_API_KEY:
        return {"error": "NVIDIA_NIM_API_KEY not set"}

    # Build context from events
    url_lines = []
    for e in events[-100:]:  # Last 100 events
        t = time.strftime("%H:%M:%S", time.localtime(e.get("t", 0)))
        dev = e.get("dev", "?")
        kind = e.get("kind", "?")
        host = e.get("host", "")
        svc = e.get("service", "")
        url_lines.append(f"{t} {dev} {kind} {host} {svc or ''}")

    # Build device context
    dev_lines = []
    if devices:
        for ip, dev in devices.items():
            name = dev.get("device_model", "") or dev.get("hostname", ip)
            icon = dev.get("device_icon", "📡")
            events_count = dev.get("traffic_events", 0)
            services = list(dev.get("services", {}).keys())[:5]
            dev_lines.append(f"{icon} {name} ({ip}) — {events_count} events, services: {', '.join(services)}")

    prompt = f"""You are a network security analyst. Analyze this network traffic data and flag any suspicious activity.

DEVICES ON NETWORK:
{chr(10).join(dev_lines[:20])}

RECENT EVENTS (last 100):
{chr(10).join(url_lines)}

Analyze and report:
1. SUSPICIOUS ACTIVITY: Any URLs, domains, or patterns that look malicious, phishing, C2, data exfiltration, or unusual
2. DEVICE BEHAVIOR: Any device acting abnormally (unusual services, high traffic, scanning behavior)
3. SECURITY CONCERNS: Any cleartext credentials, unencrypted sensitive traffic, known bad domains
4. RECOMMENDATIONS: What actions to take

Be specific with IPs, domains, and timestamps. If everything looks normal, say so."""

    payload = {
        "model": NIM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a network security analyst. Be concise and specific. Flag real threats, not theoretical ones."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    try:
        r = requests.post(f"{NIM_BASE_URL}/chat/completions",
                         headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        resp = r.json()
        content = resp["choices"][0]["message"]["content"]
        return {"analysis": content, "model": NIM_MODEL, "tokens": resp.get("usage", {})}
    except Exception as e:
        return {"error": str(e)}

def analyze_device(device_info, recent_events):
    """Analyze a specific device's behavior."""
    if not NIM_API_KEY:
        return {"error": "NVIDIA_NIM_API_KEY not set"}

    name = device_info.get("device_model", "") or device_info.get("hostname", "Unknown")
    ip = device_info.get("ip", "?")
    vendor = device_info.get("vendor", "")
    services = device_info.get("services", {})
    domains = device_info.get("domains", {})

    event_lines = []
    for e in recent_events[-50:]:
        t = time.strftime("%H:%M:%S", time.localtime(e.get("t", 0)))
        event_lines.append(f"{t} {e.get('kind','?')} {e.get('host','')}")

    prompt = f"""Analyze this device's network behavior for security concerns.

DEVICE: {name} ({ip}) — {vendor}
SERVICES: {json.dumps(services)}
TOP DOMAINS: {json.dumps(dict(sorted(domains.items(), key=lambda x: -x[1])[:10]))}

RECENT TRAFFIC:
{chr(10).join(event_lines)}

Flag anything suspicious: unusual domains, high-frequency requests, known malicious patterns, data exfiltration indicators, C2 beaconing."""

    payload = {
        "model": NIM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a network security analyst. Be concise."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500,
    }

    try:
        r = requests.post(f"{NIM_BASE_URL}/chat/completions",
                         headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        resp = r.json()
        return {"analysis": resp["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"error": str(e)}

def investigate_domain(domain):
    """Investigate a specific domain for threats."""
    if not NIM_API_KEY:
        return {"error": "NVIDIA_NIM_API_KEY not set"}

    prompt = f"""Investigate this domain for security threats: {domain}

Report:
1. What is this domain? (CDN, service, known entity)
2. Is it associated with any known threats, malware, C2, phishing?
3. What services does it typically serve?
4. Risk level: LOW/MEDIUM/HIGH/CRITICAL
5. Recommended action"""

    payload = {
        "model": NIM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a threat intelligence analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1000,
    }

    try:
        r = requests.post(f"{NIM_BASE_URL}/chat/completions",
                         headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        resp = r.json()
        return {"analysis": resp["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test with sample data
    print("NVIDIA NIM URL Analyzer for netwatch")
    print(f"API Key: {'set' if NIM_API_KEY else 'NOT SET'}")
    print(f"Model: {NIM_MODEL}")
    print()

    if len(sys.argv) > 1:
        domain = sys.argv[1]
        print(f"Investigating: {domain}")
        result = investigate_domain(domain)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python3 nim_analyzer.py <domain>")
        print("Or import and call analyze_urls(events), analyze_device(info, events), investigate_domain(domain)")
