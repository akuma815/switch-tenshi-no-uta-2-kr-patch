"""Extract supported owned NSPs with an externally supplied keyset/tool.

Output is private: NSP contents, tickets, title-key material and tool logs must
never be committed. No key material is printed or included in this repository.
"""
import argparse
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
    ap.add_argument('--base-nsp', type=Path, required=True)
    ap.add_argument('--update-nsp', type=Path, required=True)
    ap.add_argument('--keyset', type=Path, required=True)
    ap.add_argument('--hactoolnet', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    spec = json.loads((ROOT / 'config/rebuild_inputs.json').read_text(encoding='utf-8'))
    for p, expected in zip([a.base_nsp, a.update_nsp], spec['original_packages']):
        if p.stat().st_size != expected['bytes'] or sha(p) != expected['sha256']:
            raise ValueError('Unsupported original package; see config/rebuild_inputs.json')
    output = a.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('Use a private extraction directory outside the source checkout')
    output.mkdir(parents=True, exist_ok=True)

    def run(args, name):
        with (output / name).open('wb') as log:
            p = subprocess.run([str(a.hactoolnet), *map(str, args)], stdout=log, stderr=subprocess.STDOUT)
        if p.returncode:
            raise RuntimeError(f'Extraction failed; inspect private {name}')

    for p, name in [(a.base_nsp, 'base'), (a.update_nsp, 'update')]:
        run(['-t', 'pfs0', '--outdir', output / name, p], name + '_pfs.log')
    lines = []
    for name in ['base', 'update']:
        tickets = list((output / name).glob('*.tik'))
        if len(tickets) != 1:
            raise ValueError('Expected one common ticket per supported NSP')
        ticket = tickets[0]
        data = ticket.read_bytes()
        if len(data) != 704 or data[0x2A0:0x2B0].hex() != ticket.stem.lower():
            raise ValueError('Unsupported ticket layout')
        lines.append(data[0x2A0:0x2B0].hex() + ' = ' + data[0x180:0x190].hex())
    private_keys = output / 'private_title.keys'
    private_keys.write_text('\n'.join(lines) + '\n', encoding='ascii')
    base_nca = max((output / 'base').glob('*.nca'), key=lambda p: p.stat().st_size)
    update_nca = max((output / 'update').glob('*.nca'), key=lambda p: p.stat().st_size)
    romfs = output / 'romfs_updated'
    run(['-t', 'nca', '--disablekeywarns', '-k', a.keyset, '--titlekeys', private_keys,
         '--basenca', base_nca, '--romfsdir', romfs, update_nca], 'updated_romfs.log')
    paks = romfs / 'Emulator_Tenshinouta/Content/Paks'
    for name, expected in spec['original_paks_sha256'].items():
        if sha(paks / name) != expected:
            raise ValueError('Extracted original Paks mismatch')
    print('PASS: supported updated Paks extracted to ' + str(paks))


if __name__ == '__main__':
    main()
