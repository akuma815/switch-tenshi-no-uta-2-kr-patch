import os
from PIL import Image, ImageDraw
import numpy as np

ISO = r'g:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\gamepack\Emulator_Tenshinouta\Content\Ogix\GamePack\install\Tenshi2\Track02.iso'
out_dir = r'g:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\iso_extract\pure_iso_korean_cards'
os.makedirs(out_dir, exist_ok=True)

font_atlas_path = r'g:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\Galmuri7_8x8.png'
font_atlas = Image.open(font_atlas_path).convert('RGBA')

with open(ISO, 'rb') as f:
    iso_data = f.read()

# Load sector 6080 to 6153 directly from Track02.iso (NO screenshot used!)
sec_data = bytearray(iso_data[6080*2048:6154*2048])
n_tiles = len(sec_data) // 32

def encode_4bpp_pce_tile(arr_8x8):
    tile_data = bytearray(32)
    for r in range(8):
        b0, b1, b2, b3 = 0, 0, 0, 0
        for c in range(8):
            val = arr_8x8[r, c] & 0x0F
            bit = 7 - c
            b0 |= ((val >> 0) & 1) << bit
            b1 |= ((val >> 1) & 1) << bit
            b2 |= ((val >> 2) & 1) << bit
            b3 |= ((val >> 3) & 1) << bit
        tile_data[r * 2] = b0
        tile_data[r * 2 + 1] = b1
        tile_data[16 + r * 2] = b2
        tile_data[16 + r * 2 + 1] = b3
    return bytes(tile_data)

def get_hangul_tile_4bpp(char, fg_val=15, bg_val=0):
    encoded = char.encode('euc_kr')
    lead, trail = encoded
    index = (lead - 0xB0) * 94 + trail - 0xA1
    x = (index % 64) * 8
    y = (index // 64) * 8
    tile_img = font_atlas.crop((x, y, x + 8, y + 8))
    arr = np.zeros((8, 8), dtype=np.uint8)
    for py in range(8):
        for px in range(8):
            c = tile_img.getpixel((px, py))[:3]
            if c == (99, 207, 99) or c == (57, 51, 255):
                arr[py, px] = fg_val
            else:
                arr[py, px] = bg_val
    return encode_4bpp_pce_tile(arr)

# 1. Render the ORIGINAL ISO tile bank image
def render_tile_bank(data_bytes, tiles_per_row=32):
    n = len(data_bytes) // 32
    rows = (n + tiles_per_row - 1) // tiles_per_row
    img = Image.new('L', (tiles_per_row * 8, rows * 8), 0)
    px = img.load()
    for t in range(n):
        tx = (t % tiles_per_row) * 8
        ty = (t // tiles_per_row) * 8
        base = t * 32
        for r in range(8):
            b0 = data_bytes[base + r*2]
            b1 = data_bytes[base + r*2 + 1]
            b2 = data_bytes[base + 16 + r*2]
            b3 = data_bytes[base + 16 + r*2 + 1]
            for bit in range(8):
                v = ((b0 >> (7-bit)) & 1) | (((b1 >> (7-bit)) & 1) << 1) | (((b2 >> (7-bit)) & 1) << 2) | (((b3 >> (7-bit)) & 1) << 3)
                px[tx+bit, ty+r] = v * 17
    return img

orig_bank_img = render_tile_bank(sec_data, tiles_per_row=32)
orig_bank_img.save(os.path.join(out_dir, '00_Track02_ISO_original_tile_bank.png'))

# 2. Modify the text tiles directly inside the ISO tile bank (sectors 6102..6117)
# Replacing English font/label tiles in sector 6102+ with Korean 4bpp tiles
modified_sec_data = bytearray(sec_data)

# Sector 6102 relative tile offset = (6102 - 6080) * 64 = 1408 tiles
font_start_tile = (6102 - 6080) * 64

card_korean_labels = [
    ("성녀", "SAINT"),
    ("왕자", "PRINCE"),
    ("성기사", "PALADIN"),
    ("흑마법사", "HARLOCK"),
    ("암흑경", "DARK MIRROR"),
    ("신전", "SHRINE"),
    ("요새", "FORTRESS"),
    ("영지", "REALM"),
    ("파레이스", "PARACE"),
    ("길드", "GUILD"),
    ("성", "CASTLE"),
    ("성표", "HOLY SYMBOL"),
]

# Write Korean tiles into the tile bank starting at tile 1408
curr_tile = font_start_tile
for ko_str, en_name in card_korean_labels:
    for char in ko_str:
        tile_4bpp = get_hangul_tile_4bpp(char, fg_val=15, bg_val=0)
        start_byte = curr_tile * 32
        modified_sec_data[start_byte : start_byte + 32] = tile_4bpp
        curr_tile += 1

# Render MODIFIED ISO tile bank with Korean text embedded
korean_bank_img = render_tile_bank(modified_sec_data, tiles_per_row=32)
korean_bank_img.save(os.path.join(out_dir, '01_Track02_ISO_korean_tile_bank.png'))

# 3. Create high-resolution comparison sheet between Original ISO tiles and Korean ISO tiles
scale = 2
orig_scaled = orig_bank_img.resize((orig_bank_img.width * scale, orig_bank_img.height * scale), Image.NEAREST)
korean_scaled = korean_bank_img.resize((korean_bank_img.width * scale, korean_bank_img.height * scale), Image.NEAREST)

comparison = Image.new('L', (orig_scaled.width * 2 + 20, orig_scaled.height), 0)
comparison.paste(orig_scaled, (0, 0))
comparison.paste(korean_scaled, (orig_scaled.width + 20, 0))
comparison.save(os.path.join(out_dir, '02_ISO_pure_extraction_comparison.png'))

print('Pure ISO extraction and tile replacement completed!')
