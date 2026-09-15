#!/usr/bin/env python3
"""Collect personal Copilot billing for the current calendar month."""
import argparse
import datetime
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error

def collect(config):
    token = config.get('token')
    if not token:
        raise RuntimeError('Missing billing token')
    def get(path):
        request = urllib.request.Request('https://api.github.com' + path, headers={
            'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2026-03-10', 'User-Agent': 'homelab-quota-collector'})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)
    login = get('/user')['login']
    date = datetime.datetime.now(datetime.timezone.utc)
    report = get(f'/users/{login}/settings/billing/ai_credit/usage?year={date.year}&month={date.month}')
    output = ['homelab_quota_collection_success{provider="copilot"} 1']
    totals = {}
    for item in report['usageItems']:
        key = (item.get('model', 'unknown'), item.get('unitType', 'unknown'))
        totals[key] = totals.get(key, 0.0) + float(item['grossQuantity'])
    for (model, unit), quantity in totals.items():
        labels = 'provider="copilot",model=' + json.dumps(model) + ',unit=' + json.dumps(unit)
        output.append('homelab_copilot_month_usage{' + labels + '} ' + str(quantity))
    output.append('homelab_quota_collection_timestamp_seconds{provider="copilot"} ' + str(time.time()))
    return '\n'.join(output) + '\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = collect(json.loads(args.config.read_text()))
    except urllib.error.HTTPError as error:
        result = ('homelab_quota_collection_success{provider="copilot"} 0\n'
                  'homelab_quota_http_error{provider="copilot",code="' + str(error.code) + '"} 1\n')
    except Exception as error:
        result = ('homelab_quota_collection_success{provider="copilot"} 0\n'
                  'homelab_quota_collection_error{provider="copilot",type="' + type(error).__name__ + '"} 1\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(result)
    os.replace(temporary, args.output)

if __name__ == '__main__':
    main()
