import os
from PIL import Image, ImageDraw

src_path = r'C:\Users\akuma\.gemini\antigravity-ide\brain\0c483edb-11bf-43da-8263-c5d2a24522bb\media__1784686968964.png'
out_dir = r'g:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\korean_card_pngs'
os.makedirs(out_dir, exist_ok=True)

font_atlas_path = r'g:\Downloads\Korean Traslate Project\Games\Tenshi no Uta 2\translation\card_game_extract\Galmuri7_8x8.png'
font_atlas = Image.open(font_atlas_path).convert('RGBA')

def get_hangul_glyph(char):
    encoded = char.encode('euc_kr')
    lead, trail = encoded
    index = (lead - 0xB0) * 94 + trail - 0xA1
    x = (index % 64) * 8
    y = (index // 64) * 8
    tile = font_atlas.crop((x, y, x + 8, y + 8))
    mask = Image.new('L', (8, 8), 0)
    px_mask = mask.load()
    for py in range(8):
        for px in range(8):
            c = tile.getpixel((px, py))[:3]
            if c == (99, 207, 99) or c == (57, 51, 255):
                px_mask[px, py] = 255
    return mask

cards_native = [
    {'name': '01_DARK_MIRROR_암흑경', 'ko': '암흑경', 'box_4x': (94, 178, 196, 332)},
    {'name': '02_GUILD_길드', 'ko': '길드', 'box_4x': (213, 178, 315, 332)},
    {'name': '03_HARLOCK_흑마법사', 'ko': '흑마법사', 'box_4x': (332, 178, 434, 332)},
    {'name': '04_REALM_영지', 'ko': '영지', 'box_4x': (94, 333, 196, 487)},
    {'name': '05_PARACE_파레이스', 'ko': '파레이스', 'box_4x': (213, 333, 315, 487)},
    {'name': '06_SHRINE_신전', 'ko': '신전', 'box_4x': (332, 333, 434, 487)},
    {'name': '07_SAINT_성녀', 'ko': '성녀', 'box_4x': (154, 534, 256, 688)},
    {'name': '08_FORTRESS_요새', 'ko': '요새', 'box_4x': (272, 534, 374, 688)},
    {'name': '09_PRINCE_왕자', 'ko': '왕자', 'box_4x': (390, 534, 492, 688)},
    {'name': '10_PALADIN_성기사', 'ko': '성기사', 'box_4x': (509, 534, 611, 688)},
    {'name': '11_CASTLE_성', 'ko': '성', 'box_4x': (628, 534, 730, 688)},
    {'name': '12_HOLY_SYMBOL_성표', 'ko': '성표', 'box_4x': (746, 534, 848, 688)},
]

img_4x = Image.open(src_path).convert('RGBA')

for c in cards_native:
    card_4x = img_4x.crop(c['box_4x'])
    card_1x = card_4x.resize((card_4x.width // 4, card_4x.height // 4), Image.NEAREST)
    cw, ch = card_1x.size
    
    draw_1x = ImageDraw.Draw(card_1x)
    text_box_1x = (1, ch - 9, cw - 2, ch - 2)
    draw_1x.rectangle(text_box_1x, fill=(0, 0, 0, 255))
    
    ko_str = c['ko']
    total_w = len(ko_str) * 8
    start_x = text_box_1x[0] + (text_box_1x[2] - text_box_1x[0] - total_w) // 2
    start_y = ch - 9
    
    for i, char in enumerate(ko_str):
        glyph_mask = get_hangul_glyph(char)
        gx = start_x + i * 8
        card_1x.paste((255, 255, 255, 255), (gx, start_y), mask=glyph_mask)
    
    card_name = c['name']
    path_1x = os.path.join(out_dir, f'{card_name}_1x_pce.png')
    card_1x.save(path_1x)
    
    card_4x_pixel = card_1x.resize((card_1x.width * 4, card_1x.height * 4), Image.NEAREST)
    path_4x_pixel = os.path.join(out_dir, f'{card_name}_4x_pixel.png')
    card_4x_pixel.save(path_4x_pixel)

print('Generated native 1x PCE cards and 4x pixel-art cards!')
