import os
import struct

ISO_PATH = r'G:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\gamepack\Emulator_Tenshinouta\Content\Ogix\GamePack\install\Tenshi2\Track02.iso'

with open(ISO_PATH, 'rb') as f:
    iso_data = f.read()

total_secs = len(iso_data) // 2048
print(f"ISO loaded: {len(iso_data)} bytes ({total_secs} sectors)")

# Search for magic bytes or signatures
magics = [b'LZ', b'RL', b'CMP', b'GFX', b'PC Engine', b'TELENET', b'RIOT']
for m in magics:
    matches = []
    pos = 0
    while True:
        idx = iso_data.find(m, pos)
        if idx == -1:
            break
        sec = idx // 2048
        off_in_sec = idx % 2048
        matches.append((idx, sec, off_in_sec))
        pos = idx + len(m)
    print(f"Magic {m}: {len(matches)} matches found.")
    if len(matches) < 20 and len(matches) > 0:
        for idx, sec, off in matches:
            print(f"  Offset 0x{idx:08X} (Sector {sec}, Offset 0x{off:03X})")
