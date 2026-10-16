"""Restore compiled Korean videos from original MP4s and tracked VCDIFFs.

The original MP4s are extracted from user-supplied Paks. No released patch
archive, installed mod, network request or video encoder is used at restore time.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MOVIE_REL = 'Emulator_Tenshinouta/Content/Ogix/Movie/Game2'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(args, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('wb') as stream:
        result = subprocess.run([str(x) for x in args], stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Video restoration failed; see {log}')


def restore_videos(source_paks, repak, xdelta, output=None, cache=None):
    source_paks = Path(source_paks).resolve(strict=True)
    output = Path(output) if output is not None else ROOT / 'translation/cutscene_translate'
    cache = Path(cache) if cache is not None else ROOT / 'translation/input_cache/video_deltas'
    inputs = json.loads((ROOT / 'config/rebuild_inputs.json').read_text(encoding='utf-8'))
    original_pak = source_paks / 'Emulator_Tenshinouta-Switch.pak'
    if sha(original_pak) != inputs['original_paks_sha256'][original_pak.name]:
        raise ValueError('Unsupported original video pak')
    manifest = json.loads((ROOT / inputs['video_delta_manifest']).read_text(encoding='utf-8'))
    expected = json.loads((ROOT / 'config/release_payloads.json').read_text(encoding='utf-8'))['ufs_payload_sha256']
    expected_movies = {k: v for k, v in expected.items() if k.startswith(MOVIE_REL + '/') and k.endswith('.mp4')}
    entries = manifest['entries']
    if len(entries) != 10 or {e['source_relative_path']: e['target_sha256'] for e in entries} != expected_movies:
        raise ValueError('Video manifest differs from the frozen release profile')
    originals = cache / 'originals'
    run([repak, 'unpack', original_pak, '-o', originals, '-f', '-i', MOVIE_REL], cache / 'extract_original_movies.log')
    output.mkdir(parents=True, exist_ok=True)
    verified = []
    for entry in entries:
        name = entry['name']
        if Path(name).name != name or not name.endswith('.mp4'):
            raise ValueError('Invalid video filename')
        source = originals / entry['source_relative_path']
        patch = ROOT / entry['patch']
        if source.stat().st_size != entry['source_bytes'] or sha(source) != entry['source_sha256']:
            raise ValueError(f'Wrong original movie: {name}')
        if patch.stat().st_size != entry['patch_bytes'] or sha(patch) != entry['patch_sha256']:
            raise ValueError(f'Video delta mismatch: {name}')
        target = output / name
        run([xdelta, '-f', '-d', '-s', source, patch, target], cache / (name + '_decode.log'))
        if target.stat().st_size != entry['target_bytes'] or sha(target) != entry['target_sha256']:
            raise ValueError(f'Restored Korean movie mismatch: {name}')
        verified.append({'name': name, 'bytes': target.stat().st_size, 'sha256': entry['target_sha256']})
    result = {
        'status': 'PASS', 'restored_video_count': len(verified),
        'input_method': 'Owned original MP4s plus Git-tracked xdelta3 patches',
        'release_archive_required': False, 'installed_mod_required': False,
        'network_used_by_restoration': False, 'videos': verified,
        'limits': 'Preserves compiled video bytes; no subtitle-authoring or re-encoding recipe claim. No new playback/visual QA.',
    }
    (cache / 'video_restoration_report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-paks', type=Path, required=True)
    ap.add_argument('--repak', type=Path, required=True)
    ap.add_argument('--xdelta', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--cache', type=Path)
    args = ap.parse_args()
    print(json.dumps(restore_videos(args.source_paks, args.repak, args.xdelta, args.output, args.cache), indent=2))


if __name__ == '__main__':
    main()
