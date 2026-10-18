"""Playlist-specific XMLTV merger. Python 3.11+, standard library only."""
import argparse
import copy
import gzip
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_BYTES = 256 * 1024 * 1024


def read_xml(location):
    if location.startswith(('https://', 'http://')):
        request = urllib.request.Request(location, headers={'User-Agent': 'PersonalXMLTV/1.0'})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_BYTES + 1)
    else:
        with open(location, 'rb') as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Source exceeds download size limit')
    if data[:2] == b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('Source exceeds expanded size limit')
    # Some legitimate XMLTV files have an external DTD. ElementTree does not
    # fetch it. Internal entities are unnecessary here and are rejected.
    if b'<!ENTITY' in data.upper():
        raise ValueError('Entity declarations are not accepted')
    root = ET.fromstring(data)
    if root.tag != 'tv':
        raise ValueError('Not an XMLTV document')
    return root


def timestamp(value):
    # Partial dates or missing offsets are ambiguous; do not guess local time.
    if not re.fullmatch(r'\d{14}\s+[+-]\d{4}', value or ''):
        raise ValueError('Expected full XMLTV timestamp with UTC offset')
    return datetime.strptime(value, '%Y%m%d%H%M%S %z').astimezone(timezone.utc)


def key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def merge(wanted, sources, mappings, now):
    candidates = defaultdict(list)
    inventory = []
    diagnostics = []
    invalid = 0
    for rank, source in enumerate(sources):
        root = read_xml(source['url'])
        channel_map = {}
        for element in root.findall('channel'):
            sid = element.get('id', '')
            if not sid:
                continue
            if sid in channel_map:
                raise ValueError('Duplicate channel ID within source ' + source['name'])
            channel_map[sid] = element
            inventory.append({'source': source['name'], 'source_id': sid,
                              'names': [x.text or '' for x in element.findall('display-name')]})
        targets = defaultdict(list)
        for target in wanted:
            explicit = mappings.get(target)
            if explicit is not None:
                if explicit.get('source') == source['name']:
                    targets[explicit['source_id']].append(target)
            elif target in channel_map:
                targets[target].append(target)
        usable = 0
        for programme in root.findall('programme'):
            sid = programme.get('channel', '')
            if sid not in targets or sid not in channel_map:
                continue
            try:
                start = timestamp(programme.get('start'))
                stop = timestamp(programme.get('stop'))
                if stop <= start:
                    raise ValueError('Non-positive duration')
            except ValueError:
                invalid += 1
                continue
            if stop < now - timedelta(hours=12) or start > now + timedelta(days=7):
                continue
            if not (programme.findtext('title') or '').strip():
                invalid += 1
                continue
            usable += 1
            for target in targets[sid]:
                candidates[target].append((rank, start, stop, programme, channel_map[sid]))
        diagnostics.append({'name': source['name'], 'channels': len(channel_map),
                            'usable_matching_programmes': usable})
    output = ET.Element('tv', {'generator-info-name': 'Personal XMLTV merger'})
    programmes = []
    covered, overlaps = [], 0
    for target in sorted(wanted):
        accepted = []
        seen = set()
        # Earlier sources win conflicting time slots. Later sources fill gaps.
        for rank, start, stop, programme, channel in sorted(candidates[target], key=lambda x: x[:3]):
            signature = (start, stop, programme.findtext('title'))
            if signature in seen:
                continue
            seen.add(signature)
            if any(start < old_stop and stop > old_start for old_start, old_stop, *_ in accepted):
                overlaps += 1
                continue
            accepted.append((start, stop, programme, channel))
        if not accepted or not any(stop > now for _, stop, *_ in accepted):
            continue
        channel = copy.deepcopy(accepted[0][3])
        channel.set('id', target)
        output.append(channel)
        covered.append(target)
        for start, stop, programme, _ in sorted(accepted, key=lambda x: x[0]):
            item = copy.deepcopy(programme)
            item.set('channel', target)
            item.set('start', start.strftime('%Y%m%d%H%M%S +0000'))
            item.set('stop', stop.strftime('%Y%m%d%H%M%S +0000'))
            programmes.append(item)
    output.extend(programmes)
    # Suggestions are NEVER applied automatically: a name is not proof of region.
    lookup = defaultdict(list)
    for row in inventory:
        for name in set([row['source_id']] + row['names']):
            lookup[key(re.sub(r'\.[a-z]{2}$', '', name))].append(row)
    missing = []
    for target in sorted(set(wanted) - set(covered)):
        base = re.sub(r'\.[a-z]{2}@.*$', '', target)
        options = lookup.get(key(base), [])
        unique = {(x['source'], x['source_id']): x for x in options}
        missing.append({'playlist_id': target, 'name': wanted[target],
                        'candidates_for_review': list(unique.values())[:20]})
    report = {'generated_utc': now.isoformat(), 'requested_ids': len(wanted),
              'covered_ids': len(covered), 'programme_count': len(programmes),
              'covered': covered, 'unmatched': missing, 'sources': diagnostics,
              'invalid_programmes_skipped': invalid, 'overlaps_skipped': overlaps}
    return output, report, inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--audit', action='store_true', help='Report only; do not create feed')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding='utf-8-sig'))
    wanted = json.loads(Path(config['channels']).read_text(encoding='utf-8-sig'))
    mappings = json.loads(Path(config['mappings']).read_text(encoding='utf-8-sig'))
    unknown = set(mappings) - set(wanted)
    if unknown:
        raise ValueError('Mapping targets are not present in the playlist')
    now = datetime.now(timezone.utc)
    root, report, inventory = merge(wanted, config['sources'], mappings, now)
    reports = Path('reports')
    reports.mkdir(exist_ok=True)
    for name, value in [('coverage.json', report), ('source-channels.json', inventory)]:
        (reports / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Covered {report['covered_ids']} of {len(wanted)} IDs; {report['programme_count']} programmes")
    if args.audit:
        return
    if not config.get('coverage_reviewed', False):
        raise ValueError('Review the audit and mappings before enabling publication')
    if report['covered_ids'] < config['minimum_covered_ids'] or not report['programme_count']:
        raise ValueError('Coverage below approved minimum; previous hosted guide remains unchanged')
    required = set(config.get('required_ids', []))
    if required - set(report['covered']):
        raise ValueError('Required guide coverage missing; previous hosted guide remains unchanged')
    public = Path('public')
    public.mkdir(exist_ok=True)
    data = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    ET.fromstring(data)
    for name, value in [('epg.xml', data), ('epg.xml.gz', gzip.compress(data, mtime=0))]:
        temp = public / (name + '.tmp')
        temp.write_bytes(value)
        temp.replace(public / name)
    (public / 'status.json').write_text(json.dumps({k: report[k] for k in
        ['generated_utc', 'requested_ids', 'covered_ids', 'programme_count']}, indent=2), encoding='utf-8')
    (public / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Personal EPG</title>'
        '<h1>Personal EPG</h1><p><a href="epg.xml">XML guide</a> | '
        '<a href="epg.xml.gz">Compressed guide</a> | <a href="status.json">Update status</a></p>', encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Avoid logging credential-bearing source URLs from network exceptions.
        print('Build failed; no deployment. Error type: ' + type(error).__name__, file=sys.stderr)
        sys.exit(1)
