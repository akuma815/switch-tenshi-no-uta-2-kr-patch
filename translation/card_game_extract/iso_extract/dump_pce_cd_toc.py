import os
import struct

ISO_PATH = r'G:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\gamepack\Emulator_Tenshinouta\Content\Ogix\GamePack\install\Tenshi2\Track02.iso'

with open(ISO_PATH, 'rb') as f:
    iso_data = f.read()

print("Scanning early sectors (0 to 30) for directory structures & sector pointers...")

for sec in range(0, 30):
    chunk = iso_data[sec*2048:(sec+1)*2048]
    # Check for text or printable ASCII in chunk
    text_chars = sum(1 for b in chunk if 32 <= b <= 126 or b in (10, 13, 9))
    ratio = text_chars / 2048
    print(f"Sector {sec:02d}: text ratio {ratio:.2%}, first 32 bytes: {chunk[:32].hex()}")
