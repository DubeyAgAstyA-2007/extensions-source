#!/usr/bin/env python3
"""
Sync and filter Keiyoushi extensions repository.
Fetches upstream Keiyoushi index.pb and repo.json, filters for packages specified
in sources.json, and outputs a curated index.pb, index.min.json, and repo.json.
"""

import gzip
import json
import os
import sys
import urllib.request

UPSTREAM_PB_URL = "https://github.com/keiyoushi/extensions/raw/repo/index.pb"
UPSTREAM_REPO_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/repo.json"

def read_varint(stream, pos):
    res, shift = 0, 0
    while True:
        b = stream[pos]
        pos += 1
        res |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return res, pos

def encode_varint(val):
    res = bytearray()
    while val > 0x7F:
        res.append((val & 0x7F) | 0x80)
        val >>= 7
    res.append(val & 0x7F)
    return bytes(res)

def parse_extension_item(item_bytes):
    """
    Parses a single extension protobuf message into a structured dictionary.
    """
    ext = {
        'raw_bytes': item_bytes,
        'name': '',
        'pkg': '',
        'apk': '',
        'lang': '',
        'code': 0,
        'version': '',
        'nsfw': 0,
        'sources': []
    }
    p = 0
    while p < len(item_bytes):
        val, p = read_varint(item_bytes, p)
        fn, wt = val >> 3, val & 7
        if wt == 0:
            v_int, p = read_varint(item_bytes, p)
            if fn == 5:
                ext['code'] = v_int
            elif fn == 7:
                ext['nsfw'] = v_int
        elif wt == 2:
            length, p = read_varint(item_bytes, p)
            content = item_bytes[p:p + length]
            p += length
            if fn == 1:
                ext['name'] = content.decode('utf-8', errors='ignore')
            elif fn == 2:
                ext['pkg'] = content.decode('utf-8', errors='ignore')
            elif fn == 3:
                # Subfields of field 3 (APK url, icon, jar)
                sub_p = 0
                while sub_p < len(content):
                    s_val, sub_p = read_varint(content, sub_p)
                    s_fn, s_wt = s_val >> 3, s_val & 7
                    if s_wt == 2:
                        s_len, sub_p = read_varint(content, sub_p)
                        s_bytes = content[sub_p:sub_p + s_len]
                        sub_p += s_len
                        if s_fn == 1:
                            ext['apk'] = s_bytes.decode('utf-8', errors='ignore')
                    elif s_wt == 0:
                        _, sub_p = read_varint(content, sub_p)
            elif fn == 6:
                ext['version'] = content.decode('utf-8', errors='ignore')
            elif fn == 8:
                # Source sub-entry
                src = {'name': '', 'lang': '', 'id': '', 'baseUrl': ''}
                sp = 0
                while sp < len(content):
                    sv, sp = read_varint(content, sp)
                    sfn, swt = sv >> 3, sv & 7
                    if swt == 0:
                        si, sp = read_varint(content, sp)
                        if sfn == 1:
                            src['id'] = str(si)
                    elif swt == 2:
                        sl, sp = read_varint(content, sp)
                        sc = content[sp:sp + sl]
                        sp += sl
                        if sfn == 2:
                            src['name'] = sc.decode('utf-8', errors='ignore')
                        elif sfn == 3:
                            src['lang'] = sc.decode('utf-8', errors='ignore')
                        elif sfn == 4:
                            src['baseUrl'] = sc.decode('utf-8', errors='ignore')
                ext['sources'].append(src)
                if not ext['lang'] and src.get('lang'):
                    ext['lang'] = src['lang']
        elif wt == 1:
            p += 8
        elif wt == 5:
            p += 4
    if not ext['lang'] and '.all.' in ext['pkg']:
        ext['lang'] = 'all'
    elif not ext['lang'] and '.en.' in ext['pkg']:
        ext['lang'] = 'en'
    return ext

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sources_path = os.path.join(base_dir, 'sources.json')
    output_dir = os.path.join(base_dir, 'repo')
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(sources_path):
        print(f"Error: {sources_path} not found!", file=sys.stderr)
        sys.exit(1)

    with open(sources_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    target_packages = {p['pkg'] for p in config.get('packages', [])}
    repo_name = config.get('name', "Curated Keiyoushi Repo")
    repo_website = config.get('website', "https://github.com/DubeyAgAstyA-2007/extensions-source")

    print(f"Targeting {len(target_packages)} packages from {sources_path}...")

    # 1. Fetch upstream repo.json for metadata & signing key
    print(f"Fetching {UPSTREAM_REPO_URL}...")
    req = urllib.request.Request(UPSTREAM_REPO_URL, headers={'User-Agent': 'Mozilla/5.0'})
    upstream_repo_data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    signing_key = (upstream_repo_data.get('meta', {}).get('signingKeyFingerprint')
                   or upstream_repo_data.get('signingKeyFingerprint', ''))

    # 2. Fetch upstream index.pb
    print(f"Fetching {UPSTREAM_PB_URL}...")
    req = urllib.request.Request(UPSTREAM_PB_URL, headers={'User-Agent': 'Mozilla/5.0'})
    compressed_upstream = urllib.request.urlopen(req).read()
    raw_upstream = gzip.decompress(compressed_upstream)
    print(f"Decompressed upstream index: {len(raw_upstream):,} bytes")

    # 3. Parse and filter
    pos = 0
    header_bytes = bytearray()
    filtered_items = []
    json_entries = []

    while pos < len(raw_upstream):
        val, pos = read_varint(raw_upstream, pos)
        fn, wt = val >> 3, val & 7
        if wt == 0:
            _, next_pos = read_varint(raw_upstream, pos)
            header_bytes.extend(encode_varint(val))
            header_bytes.extend(raw_upstream[pos:next_pos])
            pos = next_pos
        elif wt == 2:
            length, pos = read_varint(raw_upstream, pos)
            chunk = raw_upstream[pos:pos + length]
            if fn == 101:
                # Subfield 101 holds the repeated extension items
                p101 = 0
                while p101 < len(chunk):
                    item_val, p101 = read_varint(chunk, p101)
                    item_len, p101 = read_varint(chunk, p101)
                    item_bytes = chunk[p101:p101 + item_len]
                    p101 += item_len

                    ext_info = parse_extension_item(item_bytes)
                    if ext_info['pkg'] in target_packages:
                        filtered_items.append((item_val, item_bytes))
                        json_entries.append({
                            'name': ext_info['name'],
                            'pkg': ext_info['pkg'],
                            'apk': ext_info['apk'],
                            'lang': ext_info['lang'],
                            'code': ext_info['code'],
                            'version': ext_info['version'],
                            'nsfw': ext_info['nsfw'],
                            'sources': ext_info['sources']
                        })
            else:
                # Keep top-level repo metadata header (fields 1, 2, 3, etc.)
                header_bytes.extend(encode_varint(val))
                header_bytes.extend(encode_varint(length))
                header_bytes.extend(chunk)
            pos += length
        elif wt == 1:
            header_bytes.extend(encode_varint(val))
            header_bytes.extend(raw_upstream[pos:pos + 8])
            pos += 8
        elif wt == 5:
            header_bytes.extend(encode_varint(val))
            header_bytes.extend(raw_upstream[pos:pos + 4])
            pos += 4

    print(f"Successfully matched {len(filtered_items)} / {len(target_packages)} target extensions:")
    for entry in sorted(json_entries, key=lambda x: x['name']):
        print(f"  • {entry['name']} ({entry['pkg']}) v{entry['version']} [code {entry['code']}]")

    # 4. Construct filtered index.pb
    f101_payload = bytearray()
    for item_val, item_bytes in filtered_items:
        f101_payload.extend(encode_varint(item_val))
        f101_payload.extend(encode_varint(len(item_bytes)))
        f101_payload.extend(item_bytes)

    new_raw = bytearray()
    new_raw.extend(header_bytes)
    new_raw.extend(encode_varint((101 << 3) | 2))
    new_raw.extend(encode_varint(len(f101_payload)))
    new_raw.extend(f101_payload)

    new_compressed = gzip.compress(new_raw)

    pb_path = os.path.join(output_dir, 'index.pb')
    with open(pb_path, 'wb') as f:
        f.write(new_compressed)
    print(f"Wrote {pb_path} ({len(new_compressed):,} bytes)")

    # 5. Construct index.min.json
    json_path = os.path.join(output_dir, 'index.min.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_entries, f, separators=(',', ':'))
    print(f"Wrote {json_path} ({os.path.getsize(json_path):,} bytes)")

    # 6. Construct repo.json
    repo_meta = {
        "meta": {
            "name": repo_name,
            "website": repo_website,
            "signingKeyFingerprint": signing_key
        },
        "index_v2": f"https://raw.githubusercontent.com/DubeyAgAstyA-2007/extensions-source/repo/index.pb"
    }
    repo_path = os.path.join(output_dir, 'repo.json')
    with open(repo_path, 'w', encoding='utf-8') as f:
        json.dump(repo_meta, f, indent=2)
    print(f"Wrote {repo_path}")

    # 7. Write .nojekyll
    nojekyll_path = os.path.join(output_dir, '.nojekyll')
    with open(nojekyll_path, 'w') as f:
        f.write('')
    print("Wrote .nojekyll")

    print("\nRepo sync complete! All index files ready.")

if __name__ == '__main__':
    main()
