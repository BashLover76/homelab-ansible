#!/usr/bin/env python3
"""Snapshot supported application configuration; SQLite uses online backup.

Archives contain credentials. Restore only with the destination app stopped.
Home Assistant recorder history, caches and media are intentionally excluded.
"""
import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile

APPS = {
    'homarr': ['/appdata'],
    'nginx-proxy-manager': ['/data', '/etc/letsencrypt'],
    'AdGuardHome': ['/opt/adguardhome/conf'],
    'Home-Assistant': ['/config'],
}
EXCLUDED = {'home-assistant_v2.db', 'home-assistant_v2.db-wal',
            'home-assistant_v2.db-shm', '__pycache__', '.cache', 'logs', 'backups'}

def copy_configuration(source, target):
    for src in source.iterdir():
        if src.name in EXCLUDED or src.name.endswith(('-wal', '-shm', '.log')):
            continue
        dst = target / src.name
        if src.is_symlink():
            dst.symlink_to(os.readlink(src))
        elif src.is_dir():
            dst.mkdir()
            copy_configuration(src, dst)
        elif src.is_file():
            with src.open('rb') as handle:
                sqlite = handle.read(16) == b'SQLite format 3\x00'
            if sqlite:
                with sqlite3.connect(src.as_uri() + '?mode=ro', uri=True) as db:
                    with sqlite3.connect(str(dst)) as backup:
                        db.backup(backup)
                        if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                            raise RuntimeError('SQLite integrity check failed')
            else:
                shutil.copy2(src, dst)

def main():
    os.umask(0o077)
    root = Path('/volume1/Docker/backups/configuration')
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    with tempfile.TemporaryDirectory(prefix='snapshot-', dir=root) as work:
        work = Path(work)
        manifest = {}
        for app, destinations in APPS.items():
            info = json.loads(subprocess.check_output(['docker', 'inspect', app]))[0]
            manifest[app] = {'image': info['Image'], 'mounts': []}
            for mount in info['Mounts']:
                if mount['Destination'] not in destinations:
                    continue
                source = Path(mount['Source']).resolve(strict=True)
                relative = app + '/' + mount['Destination'].strip('/').replace('/', '_')
                target = work / relative
                target.mkdir(parents=True)
                copy_configuration(source, target)
                manifest[app]['mounts'].append({'archive': relative, 'destination': str(source)})
        (work / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        archive = root / (stamp + '.tar.gz')
        with tarfile.open(archive, 'w:gz') as tar:
            for entry in work.iterdir():
                tar.add(entry, arcname=entry.name)
        print(archive)

if __name__ == '__main__':
    main()
