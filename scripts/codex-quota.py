#!/usr/bin/env python3
"""Export official Codex account/rateLimits/read data, without copying tokens."""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

def read_limits(executable):
    process = subprocess.Popen([executable, 'app-server'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding='utf-8')
    lines = queue.Queue()
    def reader():
        for line in process.stdout:
            lines.put(line)
    threading.Thread(target=reader, daemon=True).start()
    def send(message):
        process.stdin.write(json.dumps(message) + '\n')
        process.stdin.flush()
    def receive(request_id):
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            data = json.loads(lines.get(timeout=max(0.1, deadline-time.monotonic())))
            if data.get('id') == request_id:
                if 'error' in data:
                    raise RuntimeError('Codex account unavailable')
                return data['result']
        raise TimeoutError('Codex timeout')
    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'homelab_metrics', 'version': '1.0'}}})
        receive(1)
        send({'method': 'initialized', 'params': {}})
        send({'id': 2, 'method': 'account/rateLimits/read', 'params': {}})
        return receive(2)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

def metrics(result):
    output = ['homelab_quota_collection_success{provider="codex"} 1']
    buckets = result.get('rateLimitsByLimitId') or {'codex': result.get('rateLimits', {})}
    found = False
    for name, bucket in buckets.items():
        for window in ('primary', 'secondary'):
            details = (bucket or {}).get(window)
            if not details:
                continue
            found = True
            labels = 'provider="codex",bucket=' + json.dumps(name) + ',window=' + json.dumps(window)
            for key, metric in [('usedPercent', 'used_percent'), ('resetsAt', 'reset_timestamp_seconds'), ('windowDurationMins', 'window_minutes')]:
                if details.get(key) is not None:
                    output.append('homelab_quota_' + metric + '{' + labels + '} ' + str(float(details[key])))
    if not found:
        raise RuntimeError('No quota returned')
    output.append('homelab_quota_collection_timestamp_seconds{provider="codex"} ' + str(time.time()))
    return '\n'.join(output) + '\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--codex', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = metrics(read_limits(args.codex))
    except Exception:
        result = 'homelab_quota_collection_success{provider="codex"} 0\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix('.tmp')
        temp.write_text(result)
        os.replace(temp, args.output)
    else:
        print(result, end='')

if __name__ == '__main__':
    main()
