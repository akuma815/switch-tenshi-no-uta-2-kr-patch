"""Verify rebuilt container payloads against the frozen published release."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--retoc', type=Path, required=True)
    ap.add_argument('--repak', type=Path, required=True)
    a = ap.parse_args()
    expected = json.loads((ROOT / 'config/release_payloads.json').read_text(encoding='utf-8'))
    artifacts = ROOT / 'translation/patch_P'
    evidence = ROOT / 'qa' / ('rebuild_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    evidence.mkdir(parents=True, exist_ok=False)
    with (evidence / 'unpack.log').open('wb') as log:
        p = subprocess.run([str(a.retoc), 'unpack', str(artifacts / expected['utoc_name']), str(evidence / 'chunks')], stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError('Rebuilt IoStore unpack failed')
    actual = {p.relative_to(evidence / 'chunks').as_posix(): sha(p) for p in (evidence / 'chunks').rglob('*') if p.is_file()}
    if actual != expected['iostore_payload_sha256']:
        raise ValueError('Rebuilt IoStore payloads differ from the frozen release')
    font = artifacts / 'TenshiKR_Font_P.pak'
    if sha(font) != expected['container_sha256']['TenshiKR_Font_P.pak']:
        raise ValueError('Font pak differs from the release')
    if expected.get('ufs_payload_sha256'):
        data = subprocess.check_output([str(a.repak), 'hash-list', str(artifacts / expected['pak_name'])], encoding='utf-8')
        hashes = {}
        for line in data.splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) == 2 and len(parts[0]) == 64:
                hashes[parts[1]] = parts[0].lower()
        if hashes != expected['ufs_payload_sha256']:
            raise ValueError('Rebuilt UFS payloads differ from the release')
    actual_containers = {name: sha(artifacts / name) for name in expected['container_sha256']}
    result = {
        'status': 'PASS', 'evidence_class': 'Build and decoded container payload verification; no new runtime test',
        'iostore_payload_count': len(actual), 'all_iostore_payloads_equal_release': True,
        'ufs_payload_count': len(expected.get('ufs_payload_sha256', {})),
        'all_ufs_payloads_equal_release': True, 'font_pak_byte_identical': True,
        'container_sha256': actual_containers,
        'container_byte_identity': {name: value == expected['container_sha256'][name] for name, value in actual_containers.items()},
        'container_identity_note': 'Container assembly bytes can differ. Payload equality is checked separately; byte-identical distribution archives remain on the pinned GitHub releases.',
    }
    encoded = json.dumps(result, indent=2) + '\n'
    (evidence / 'verification.json').write_text(encoded, encoding='utf-8')
    (ROOT / 'translation/input_cache/latest_rebuild_verification.json').write_text(encoded, encoding='utf-8')
    print(encoded)


if __name__ == '__main__':
    main()
