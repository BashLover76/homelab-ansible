#!/usr/bin/env python3
"""Read only integration identifiers, never credentials from .storage."""
import json
from pathlib import Path
root = Path('/share/Docker/HomeAssistant/config/.storage')
entries = json.loads((root / 'core.config_entries').read_text())['data']['entries']
print(json.dumps([{'domain': e['domain'], 'title': e.get('title'),
                   'disabled_by': e.get('disabled_by')} for e in entries], ensure_ascii=False))
