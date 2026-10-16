"""Create Korean card-game textures while preserving image dimensions and dynamic holes."""

from pathlib import Path
from shutil import copy2
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "card_game_extract" / "png"
OUTPUT = BASE / "card_game_extract" / "translate"
FONT_DIR = BASE.parents[2] / "Font"
FONT = FONT_DIR / "Galmuri11-Condensed.ttf"
ASCII_FONT = FONT_DIR / "Galmuri9.ttf"
BITMAP_FONT = BASE / "card_game_extract" / "Galmuri9_10x10.png"
FALLBACK_BITMAP_FONT = BASE / "card_game_extract" / "Galmuri7_8x8.png"

TEAL = (59, 90, 90, 255)
TEAL_LIGHT = (81, 107, 104, 255)
STRIP_TEAL = (82, 107, 104, 255)
GREEN = (0, 59, 0, 255)
LIGHT = (188, 214, 211, 255)
SOFT_LIGHT = (182, 207, 205, 255)
MUTED = (126, 151, 148, 255)
ORANGE = (221, 148, 56, 255)
DARK = (7, 33, 30, 255)
BLACK = (0, 0, 0, 255)

BITMAP_CELLS = (10, 8)
BITMAP_COLUMNS = 64
BITMAP_FOREGROUND = (99, 207, 99)
BITMAP_SHADOW = (57, 51, 255)
_BITMAP_ATLASES = {}
_ASCII_FONTS = {}


def clear(draw, box, color):
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=color)


def bitmap_atlas(cell):
    if cell not in _BITMAP_ATLASES:
        path = BITMAP_FONT if cell == 10 else FALLBACK_BITMAP_FONT
        _BITMAP_ATLASES[cell] = Image.open(path).convert("RGBA")
    return _BITMAP_ATLASES[cell]


def ascii_font(cell):
    if cell not in _ASCII_FONTS:
        path = ASCII_FONT if cell == 10 else FONT
        _ASCII_FONTS[cell] = ImageFont.truetype(path, cell)
    return _ASCII_FONTS[cell]


@lru_cache(maxsize=None)
def bitmap_glyph(char, cell):
    if char == " ":
        advance = cell // 2
        return Image.new("L", (advance, cell)), advance

    if char == "ㆍ":
        # A low, substantial separator for Hangul card-name lists. The regular
        # middle dot from the ASCII font is tiny and sits above the baseline.
        advance = 5 if cell == 10 else 4
        dot_width = 3 if cell == 10 else 2
        dot_height = 2
        dot_y = cell - dot_height - 1
        mask = Image.new("L", (advance, cell))
        dot_x = (advance - dot_width) // 2
        ImageDraw.Draw(mask).rectangle(
            (dot_x, dot_y, dot_x + dot_width - 1, dot_y + dot_height - 1),
            fill=255,
        )
        return mask, advance

    if "가" <= char <= "힣":
        encoded = char.encode("euc_kr")
        lead, trail = encoded
        if not (0xB0 <= lead <= 0xC8 and 0xA1 <= trail <= 0xFE):
            raise ValueError(f"Hangul glyph is not in Galmuri7_8x8.png: {char}")
        index = (lead - 0xB0) * 94 + trail - 0xA1
        x = index % BITMAP_COLUMNS * cell
        y = index // BITMAP_COLUMNS * cell
        tile = bitmap_atlas(cell).crop((x, y, x + cell, y + cell))

        # The atlas stores a foreground and its one-pixel lower-right shadow.
        # Recover the complete foreground before recoloring it for each texture.
        mask = Image.new("L", (cell, cell))
        pixels = mask.load()
        for py in range(cell):
            for px in range(cell):
                color = tile.getpixel((px, py))[:3]
                if color == BITMAP_FOREGROUND:
                    pixels[px, py] = 255
                elif color == BITMAP_SHADOW and px > 0 and py > 0:
                    pixels[px - 1, py - 1] = 255

        if char == "합" and cell == 10:
            # Separate the final consonant from the upper component. The
            # source glyph has an unused last row, so this keeps the 10 px
            # cell size while adding one clear row above the batchim.
            separated = Image.new("L", (cell, cell))
            separated.paste(mask.crop((0, 0, cell, 6)), (0, 0))
            separated.paste(mask.crop((0, 6, cell, 9)), (0, 7))
            mask = separated
        return mask, cell

    font = ascii_font(cell)
    bbox = font.getbbox(char)
    advance = max(1, round(font.getlength(char)))
    width = max(advance, bbox[2] - bbox[0])
    grayscale = Image.new("L", (width, cell))
    glyph_draw = ImageDraw.Draw(grayscale)
    glyph_draw.text((-bbox[0], -bbox[1]), char, font=font, fill=255)
    return grayscale.point(lambda value: 255 if value >= 96 else 0), advance


def bitmap_line_width(text, shadow, cell):
    width = sum(bitmap_glyph(char, cell)[1] for char in text)
    return width + (1 if shadow and text else 0)


def draw_fit(
    draw,
    box,
    text,
    *,
    max_size=11,
    min_size=7,
    fill=LIGHT,
    stroke_fill=DARK,
    stroke_width=1,
    align="left",
    spacing=0,
    tracking=0,
):
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    shadow = stroke_width > 0
    lines = text.split("\n")
    for cell in BITMAP_CELLS:
        line_widths = [
            bitmap_line_width(line, shadow, cell) + max(0, len(line) - 1) * tracking
            for line in lines
        ]
        text_width = max(line_widths, default=0)
        line_step = cell + spacing
        text_height = len(lines) * cell + max(0, len(lines) - 1) * spacing
        if text_width <= width and text_height <= height:
            break
    else:
        raise ValueError(
            f"bitmap text does not fit {box}: {text!r} "
            f"({text_width}x{text_height} > {width}x{height})"
        )

    if align == "center":
        block_x = x0 + (width - text_width) // 2
    elif align == "right":
        block_x = x1 - text_width
    else:
        block_x = x0
    block_y = y0 + (height - text_height) // 2

    for line_index, (line, line_width) in enumerate(zip(lines, line_widths)):
        if align == "center":
            cursor_x = block_x + (text_width - line_width) // 2
        elif align == "right":
            cursor_x = block_x + text_width - line_width
        else:
            cursor_x = block_x
        glyph_y = block_y + line_index * line_step
        for char in line:
            mask, advance = bitmap_glyph(char, cell)
            if shadow:
                draw.bitmap((cursor_x + 1, glyph_y + 1), mask, fill=stroke_fill)
            draw.bitmap((cursor_x, glyph_y), mask, fill=fill)
            cursor_x += advance + tracking


def edit(name, callback, transparent_boxes=()):
    src = SOURCE / f"{name}.png"
    original = Image.open(src).convert("RGBA")
    img = original.copy()
    original_size = img.size
    callback(img, ImageDraw.Draw(img))
    if img.size != original_size:
        raise AssertionError(f"size changed for {name}: {original_size} -> {img.size}")
    alpha = original.getchannel("A")
    alpha_draw = ImageDraw.Draw(alpha)
    for box in transparent_boxes:
        x0, y0, x1, y1 = box
        alpha_draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=0)
    img.putalpha(alpha)
    img.save(OUTPUT / f"{name}.png")


def translate_awards():
    awards = [
        ("기도의 방패", "2000"),
        ("달의 목걸이", "1500"),
        ("나무요정의 장갑", "1000"),
        ("신주 리레이트", "800"),
        ("엘의 마법수", "500"),
        ("에이놈 열매", "200"),
        ("라이히초", "100"),
    ]

    def draw_award_row(draw, y, name, points, *, offset=0, fill=SOFT_LIGHT):
        # Keep the original four-column layout: item / separator / value / unit.
        draw_fit(
            draw, (offset, y, offset + 100, y + 15), name,
            max_size=9, min_size=7, fill=fill,
            stroke_fill=(48, 74, 71, 255),
        )
        draw_fit(
            draw, (offset + 102, y, offset + 115, y + 15), "~",
            max_size=9, min_size=8, fill=fill,
            stroke_fill=(48, 74, 71, 255), align="center",
        )
        draw_fit(
            draw, (offset + 118, y, offset + 160, y + 15), points,
            max_size=9, min_size=8, fill=fill,
            stroke_fill=(48, 74, 71, 255), align="right",
        )
        draw_fit(
            draw, (offset + 166, y, offset + 198, y + 15), "점",
            max_size=9, min_size=8, fill=fill,
            stroke_fill=(48, 74, 71, 255), align="center",
        )

    def main(_img, draw):
        clear(draw, (8, 3, 145, 25), TEAL_LIGHT)
        draw_fit(draw, (15, 4, 120, 23), "교환", fill=SOFT_LIGHT)
        clear(draw, (40, 27, 256, 151), TEAL_LIGHT)
        for i, (name, points) in enumerate(awards):
            # Reward icons are baked into the base texture at a fixed 16 px
            # pitch, so text rows must retain the same pitch to stay aligned.
            y = 31 + i * 16
            # Highlight strips are 204 px wide and right-aligned in the
            # 256 px screen, giving them a runtime origin of x=52. Align the
            # base list to that origin so highlighted text needs no clipping.
            draw_award_row(draw, y, name, points, offset=52, fill=MUTED)

    edit("card_game_award", main)
    for index, (name, points) in enumerate(awards, 1):
        def strip(_img, draw, item=name, value=points):
            clear(draw, (0, 0, 204, 16), STRIP_TEAL)
            # Runtime places the highlight strip one pixel below the base row.
            # Compensate inside the strip so its glyph baseline stays aligned.
            draw_award_row(draw, -1, item, value)
        edit(f"card_game_award{index}", strip)


def translate_board():
    def window(_img, draw):
        # The emulated card board still contains the English text underneath the
        # replacement labels. Cover the full inner panel before drawing labels.
        clear(draw, (6, 6, 186, 58), BLACK)

    def board(_img, draw):
        clear(draw, (0, 0, 144, 32), GREEN)
        draw_fit(
            draw, (18, 1, 142, 31), "[선택] 설명\n[I] 카드 보기",
            max_size=11, min_size=9, stroke_fill=BLACK, spacing=0,
        )

    def master(_img, draw):
        clear(draw, (0, 0, 72, 16), GREEN)
        draw_fit(draw, (2, 1, 70, 15), "상대 차례", align="center", stroke_fill=BLACK)

    def player(_img, draw):
        clear(draw, (0, 0, 72, 32), GREEN)
        draw_fit(
            draw, (2, 1, 70, 31), "카드를\n보여 주세요",
            max_size=11, min_size=9, align="center", stroke_fill=BLACK,
        )

    def start(_img, draw):
        clear(draw, (7, 5, 159, 26), TEAL)
        draw_fit(
            draw, (20, 6, 156, 25), "선공을 정합니다",
            max_size=11, min_size=9, align="center", stroke_fill=BLACK,
        )

    edit("card_game_window", window)
    edit("card_game_board", board)
    edit("card_game_board_master", master)
    edit("card_game_board_player", player)
    edit("card_game_game_start", start)


def translate_hands():
    def hand(_img, draw, title):
        clear(draw, (110, 4, 254, 23), TEAL)
        draw_fit(draw, (113, 4, 251, 23), title, align="center", stroke_fill=BLACK)

        for box, text in [
            ((4, 22, 57, 47), "20점\n카드"),
            ((4, 72, 57, 97), "10점\n카드"),
            ((3, 127, 72, 144), "5점 카드"),
            ((3, 152, 72, 169), "1점 카드"),
        ]:
            clear(draw, box, TEAL)
            draw_fit(draw, box, text, max_size=10, min_size=8, stroke_fill=BLACK)

        for box in [(120, 128, 153, 144), (120, 152, 153, 168)]:
            clear(draw, box, TEAL)
            draw_fit(draw, box, "장", max_size=10, min_size=8, align="center", stroke_fill=BLACK)

    edit("card_game_have", lambda img, draw: hand(img, draw, "보유 카드"))
    edit("card_game_have_other", lambda img, draw: hand(img, draw, "상대 카드"))


def translate_help():
    def help_panel(_img, draw):
        # Combination names and their required cards. Card thumbnails stay untouched.
        clear(draw, (56, 4, 216, 38), TEAL_LIGHT)
        draw_fit(draw, (58, 4, 145, 16), "비너스", max_size=10, min_size=8, fill=ORANGE)
        draw_fit(
            draw, (58, 16, 151, 38), "여왕ㆍ공주ㆍ시녀\n성녀ㆍ엘프",
            max_size=10, min_size=8, fill=DARK, stroke_width=0, spacing=2,
        )
        draw_fit(draw, (154, 4, 214, 16), "별", max_size=10, min_size=8, fill=ORANGE, align="center")
        draw_fit(
            draw, (151, 16, 215, 38), "왕자ㆍ공주\n성녀",
            max_size=10, min_size=8, fill=DARK, stroke_width=0, align="center", spacing=2,
        )

        clear(draw, (40, 38, 216, 85), TEAL_LIGHT)
        draw_fit(draw, (45, 39, 130, 52), "공작", max_size=10, min_size=8, fill=ORANGE)
        draw_fit(
            draw, (45, 53, 151, 75), "성기사ㆍ암흑기사\n흑마법사",
            max_size=10, min_size=8, fill=DARK, stroke_width=0, spacing=2,
        )
        draw_fit(draw, (154, 39, 214, 52), "에드워드 왕", max_size=10, min_size=7, fill=ORANGE, align="center")
        draw_fit(
            draw, (151, 53, 215, 75), "성검ㆍ오브\n암흑경",
            max_size=10, min_size=8, fill=DARK, stroke_width=0, align="center", spacing=2,
        )

        clear(draw, (3, 86, 253, 170), TEAL_LIGHT)
        rules = [
            ("세계", "150점", "같은 색 카드 모두"),
            ("위인", "75~125점", "20점 카드 4장 이상"),
            ("인물", "10점", "캐릭터 카드 7장 이상"),
            ("아이템", "10점", "아이템 카드 5장 이상"),
            ("건물", "10점", "1점 카드 10장 이상"),
        ]
        # Use the full available height: a 17 px row step leaves room below
        # Hangul final consonants and their one-pixel shadow.
        for i, (role, points, description) in enumerate(rules):
            y = 87 + i * 17
            draw_fit(
                draw, (5, y, 43, y + 15), role,
                max_size=9, min_size=7, fill=ORANGE, stroke_fill=DARK,
            )
            draw_fit(
                draw, (44, y, 94, y + 15), points,
                max_size=8, min_size=7, fill=ORANGE, stroke_fill=DARK,
            )
            draw_fit(
                draw, (96, y, 154, y + 15), "······",
                max_size=8, min_size=7, fill=MUTED,
                stroke_width=0, align="center",
            )
            draw_fit(
                draw, (156, y, 251, y + 15), description,
                max_size=9, min_size=7, fill=SOFT_LIGHT, stroke_fill=DARK,
            )

    edit("card_game_help", help_panel)


def translate_result():
    def result(_img, draw):
        rows = [
            ((16, 15, 124, 33), "내 점수", (214, 15, 251, 33)),
            ((16, 38, 124, 56), "상대 점수", (214, 38, 251, 56)),
            (None, None, (214, 72, 251, 89)),
            ((16, 102, 126, 121), "현재 점수", (214, 102, 251, 121)),
        ]
        for label_box, label, suffix_box in rows:
            if label_box:
                clear(draw, label_box, TEAL)
                draw_fit(draw, label_box, label, max_size=11, min_size=9, stroke_fill=BLACK)
            clear(draw, suffix_box, TEAL)
            draw_fit(draw, suffix_box, "점", max_size=10, min_size=8, align="center", stroke_fill=BLACK)
        # Keep the original Y / N pixels untouched so their spacing and
        # placement remain exactly identical to the source texture.
        clear(draw, (75, 149, 190, 169), TEAL)
        draw_fit(
            draw, (78, 150, 190, 168), "계속할까요?",
            max_size=11, min_size=9, align="center", stroke_fill=BLACK,
        )

    # The game draws the score-difference sign dynamically. The English
    # overlay contains an opaque fixed '+', so expose only that sign cell.
    edit("card_game_result", result, transparent_boxes=((154, 74, 168, 88),))


def translate_roles():
    labels = {
        "card_game_role02": ("공작", -1),
        "card_game_role03": ("인물", -1),
        "card_game_role04": ("별", 0),
        "card_game_role05": ("위인", 0),
        "card_game_role06": ("아이템", 0),
        "card_game_role07": ("에드워드 왕", 1),
    }
    for name, (label, y_shift) in labels.items():
        def role(img, draw, value=label, shift=y_shift):
            clear(draw, (0, 0, img.width, img.height), STRIP_TEAL)
            draw_fit(
                draw, (1, 1 + shift, img.width - 1, img.height - 1 + shift), value,
                max_size=11, min_size=8, fill=ORANGE,
                stroke_fill=(48, 74, 71, 255), align="center",
            )
        edit(name, role)


def translate_scores():
    def score(_img, draw, title):
        clear(draw, (96, 4, 250, 24), TEAL)
        draw_fit(draw, (99, 4, 247, 23), title, max_size=11, min_size=9, align="center", stroke_fill=BLACK)

        for box, label in [
            ((5, 33, 73, 48), "20점 카드"),
            ((5, 49, 73, 64), "10점 카드"),
            ((5, 65, 73, 80), "5점 카드"),
            ((5, 81, 73, 96), "1점 카드"),
        ]:
            clear(draw, box, TEAL)
            # Preserve the original X at x=74..84 and the original equals
            # sign. Right-align only the translated label immediately before X.
            draw_fit(
                draw, box, label,
                max_size=9, min_size=7, stroke_fill=BLACK, align="right",
            )

        for box in [(192, 33, 251, 47), (192, 49, 251, 63), (192, 65, 251, 79), (192, 81, 251, 95)]:
            clear(draw, box, TEAL)
            draw_fit(draw, box, "점", max_size=9, min_size=7, align="center", stroke_fill=BLACK)

        clear(draw, (5, 97, 220, 162), TEAL)
        draw_fit(draw, (6, 97, 68, 111), "완성 조합", max_size=9, min_size=7, stroke_fill=BLACK)

        categories = [
            ("비너스", "공작", "인물"),
            ("별", "위인", "아이템"),
            ("에드워드 왕", "세계", "건물"),
        ]
        # These are the actual 56x16 highlight slots used by
        # card_game_role02..07. The text baselines use a 17 px step while the
        # original fixed-size overlay slots remain 16 px tall.
        role_boxes = [
            ((8, 111, 64, 127), (80, 111, 136, 127), (136, 111, 192, 127)),
            ((8, 128, 64, 144), (80, 128, 136, 144), (136, 128, 196, 144)),
            ((8, 145, 64, 161), (80, 145, 136, 161), (136, 145, 192, 161)),
        ]
        for values, boxes in zip(categories, role_boxes):
            for value, box in zip(values, boxes):
                draw_fit(
                    draw, box, value,
                    max_size=8, min_size=7, fill=MUTED,
                    stroke_width=0, align="center",
                )

        clear(draw, (120, 161, 160, 182), TEAL)
        draw_fit(
            draw, (122, 163, 157, 179), "합계",
            max_size=9, min_size=7, align="center", stroke_fill=BLACK, tracking=2,
        )
        clear(draw, (205, 161, 252, 182), TEAL)
        draw_fit(draw, (208, 163, 250, 178), "점", max_size=9, min_size=7, align="center", stroke_fill=BLACK)

    edit("card_game_score_master", lambda img, draw: score(img, draw, "상대 점수 내역"))
    edit("card_game_score_player", lambda img, draw: score(img, draw, "내 점수 내역"))


def main():
    if not FONT.exists():
        raise FileNotFoundError(FONT)
    if not ASCII_FONT.exists():
        raise FileNotFoundError(ASCII_FONT)
    if not BITMAP_FONT.exists():
        raise FileNotFoundError(BITMAP_FONT)
    if not FALLBACK_BITMAP_FONT.exists():
        raise FileNotFoundError(FALLBACK_BITMAP_FONT)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_files = sorted(SOURCE.glob("card_game_*.png"))
    for path in source_files:
        copy2(path, OUTPUT / path.name)

    translate_awards()
    translate_board()
    translate_hands()
    translate_help()
    translate_result()
    translate_roles()
    translate_scores()

    output_files = sorted(
        path for path in OUTPUT.glob("card_game_*.png")
        if path.name not in {
            "card_game_translate_contact_sheet.png",
            "card_game_bitmap_preview.png",
        }
        and not path.stem.endswith("_debug4x")
    )
    if len(output_files) != len(source_files):
        raise AssertionError(f"output count {len(output_files)} != source count {len(source_files)}")
    print(f"translated textures: {len(output_files)} -> {OUTPUT}")


if __name__ == "__main__":
    main()
