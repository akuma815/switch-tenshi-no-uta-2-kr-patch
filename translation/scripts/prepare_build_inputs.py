"""Restore build inputs from owned original Paks and pinned public assets.

No NSP, keys, original textures, original game ISO or movies are distributed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from export_manual_png import export_one
from restore_compiled_videos import restore_videos

ROOT = Path(__file__).resolve().parents[2]
TR = ROOT / 'translation'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(args, log):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('wb') as stream:
        p = subprocess.run([str(x) for x in args], stdout=stream, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f'Input preparation command failed ({p.returncode}); see {log}')


def restore_manual(entry, legacy, output, cache, xdelta):
    src = legacy / entry['relative_path']
    header = src.with_suffix('.uasset')
    if sha(src) != entry['source_sha256'] or sha(header) != entry['source_uasset_sha256']:
        raise ValueError(f"Wrong original texture: {src.name}")
    patch = ROOT / entry['patch']
    if sha(patch) != entry['patch_sha256']:
        raise ValueError('Manual patch hash mismatch')
    target = output / entry['relative_path']
    target.parent.mkdir(parents=True, exist_ok=True)
    run([xdelta, '-f', '-d', '-s', src, patch, target], cache / (entry['name'] + '.log'))
    if sha(target) != entry['target_sha256']:
        raise ValueError('Restored cooked manual hash mismatch')
    shutil.copyfile(header, target.with_suffix('.uasset'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-paks', type=Path, required=True)
    ap.add_argument('--retoc', type=Path, required=True)
    ap.add_argument('--repak', type=Path, required=True)
    ap.add_argument('--xdelta', type=Path, required=True)
    a = ap.parse_args()
    spec = json.loads((ROOT / 'config/rebuild_inputs.json').read_text(encoding='utf-8'))
    paks = a.source_paks.resolve(strict=True)
    for name, expected in spec['original_paks_sha256'].items():
        if sha(paks / name) != expected:
            raise ValueError(f'Unsupported source Paks: {name}')
    cache = TR / 'input_cache'
    cache.mkdir(parents=True, exist_ok=True)
    font_out = TR / 'fontsrc_condensed/Emulator_Tenshinouta/Content/Ogix/Font'
    font_out.mkdir(parents=True, exist_ok=True)
    for source, target in [('Galmuri11-Condensed.ttf', 'k8x12.ufont'), ('NotoSansCJKkr-Regular.otf', 'BIZUDGothic-Regular.ufont')]:
        shutil.copyfile(ROOT / 'assets/fonts' / source, font_out / target)
    manuals = cache / 'manual_legacy'
    run([a.retoc, 'to-legacy', '--version', 'UE5_4', '-f', 'ManualBook', paks, manuals], cache / 'manual_extract.log')
    delta_spec = json.loads((ROOT / 'assets/manual_binary_deltas/manifest.json').read_text(encoding='utf-8'))
    original_pngs = cache / 'manual_original_png'
    original_pngs.mkdir(exist_ok=True)
    for entry in delta_spec['entries']:
        restore_manual(entry, manuals, TR / 'manual_patch_assets', original_pngs, a.xdelta)
    if spec['game_number'] == 2:
        cards = TR / 'card_game_extract'
        legacy = cards / 'legacy'
        run([a.retoc, 'to-legacy', '--version', 'UE5_4', '-f', 'CardGame', paks, legacy], cache / 'card_extract.log')
        png_out = cards / 'png'
        png_out.mkdir(exist_ok=True)
        textures = list(legacy.rglob('card_game_*.uexp'))
        if len(textures) != 29:
            raise ValueError(f'Expected 29 original card textures, got {len(textures)}')
        for src in textures:
            export_one(str(src), str(png_out / (src.stem + '.png')))
        for src in (ROOT / 'assets/card_fonts').glob('*.png'):
            shutil.copyfile(src, cards / src.name)
        iso_rel = 'Emulator_Tenshinouta/Content/Ogix/GamePack/install/Tenshi2/Track02.iso'
        run([a.repak, 'unpack', paks / 'Emulator_Tenshinouta-Switch.pak', '-o', cards / 'gamepack', '-f', '-i', iso_rel], cache / 'track02_extract.log')
        if sha(cards / 'gamepack' / iso_rel) != spec['track02_source_sha256']:
            raise ValueError('Original Track02.iso hash mismatch')
        video_report = restore_videos(paks, a.repak, a.xdelta)
    result = {'status': 'PASS', 'game_number': spec['game_number'], 'manuals_restored': len(delta_spec['entries']), 'source_paks': str(paks), 'compiled_media_dependency': None}
    if spec['game_number'] == 2:
        result['video_restoration'] = video_report
    (cache / 'preparation_report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
