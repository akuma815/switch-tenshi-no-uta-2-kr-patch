"""편집된 매뉴얼 PNG -> Texture2D uexp 재주입

사용법: python inject_manual_png.py <원본 uexp 트리> <PNG 폴더> <출력 Content 트리>

원본과 동일한 픽셀 포맷(BC1/BC3/BGRA)으로 재인코딩하므로 페이로드 크기가
원본과 같아 uexp 길이·SerialSize가 변하지 않는다 (uasset은 그대로 복사).
"""
import os
import glob
import struct
import sys

from PIL import Image
from quicktex import RawTexture
from quicktex.s3tc.bc1 import BC1Encoder
from quicktex.s3tc.bc3 import BC3Encoder

REL_DIR = os.path.join("Emulator_Tenshinouta", "Content", "Ogix", "Texture", "Game_2", "ManualBook")

def parse_uexp(data):
    n = len(data)
    if data[n-4:] != b"\xc1\x83\x2a\x9e":
        raise ValueError("missing PACKAGE_FILE_TAG")
    idx = data.find(b"PF_")
    strlen = struct.unpack_from("<i", data, idx - 4)[0]
    fmt = data[idx:idx + strlen - 1].decode()
    tx, ty, tz = struct.unpack_from("<iii", data, n - 28)
    if not (0 < tx <= 8192 and 0 < ty <= 8192 and tz == 1):
        raise ValueError(f"bad tail dims {tx}x{ty}x{tz}")
    if fmt == "PF_DXT5":
        psize = ((tx + 3) // 4) * ((ty + 3) // 4) * 16
    elif fmt == "PF_DXT1":
        psize = ((tx + 3) // 4) * ((ty + 3) // 4) * 8
    elif fmt == "PF_B8G8R8A8":
        psize = tx * ty * 4
    else:
        raise ValueError(f"unsupported format {fmt}")
    start = n - 28 - psize
    return fmt, tx, ty, start, psize

def encode(fmt, img):
    rgba = img.tobytes()
    if fmt == "PF_DXT5":
        tex = RawTexture.frombytes(rgba, img.width, img.height)
        return BC3Encoder().encode(tex).tobytes()
    if fmt == "PF_DXT1":
        tex = RawTexture.frombytes(rgba, img.width, img.height)
        return BC1Encoder().encode(tex).tobytes()
    if fmt == "PF_B8G8R8A8":
        return img.convert("RGBA").tobytes("raw", "BGRA")
    raise ValueError(fmt)

def main():
    src_root = sys.argv[1]   # retoc to-legacy 결과 트리 (원본)
    png_dir = sys.argv[2]
    out_root = sys.argv[3]   # patch_src (to-zen 입력 트리)

    pngs = sorted(glob.glob(os.path.join(png_dir, "Manual2_*.png")))
    if not pngs:
        print("no PNGs found, skipping")
        return

    src_dir = os.path.join(src_root, REL_DIR)
    out_dir = os.path.join(out_root, REL_DIR)
    os.makedirs(out_dir, exist_ok=True)

    ok = 0
    for png in pngs:
        name = os.path.splitext(os.path.basename(png))[0]
        uexp_path = os.path.join(src_dir, name + ".uexp")
        uasset_path = os.path.join(src_dir, name + ".uasset")
        if not os.path.exists(uexp_path):
            print(f"  {name}: SKIP (원본 uexp 없음)")
            continue

        data = bytearray(open(uexp_path, "rb").read())
        fmt, tx, ty, start, psize = parse_uexp(bytes(data))

        img = Image.open(png).convert("RGBA")
        if img.size != (tx, ty):
            print(f"  {name}: FAILED - PNG {img.size} != 원본 {tx}x{ty}")
            continue

        payload = encode(fmt, img)
        if len(payload) != psize:
            print(f"  {name}: FAILED - 인코딩 크기 {len(payload)} != 원본 {psize}")
            continue

        data[start:start + psize] = payload
        with open(os.path.join(out_dir, name + ".uexp"), "wb") as f:
            f.write(bytes(data))
        with open(uasset_path, "rb") as fsrc, open(os.path.join(out_dir, name + ".uasset"), "wb") as fdst:
            fdst.write(fsrc.read())
        print(f"  {name}: {fmt} {tx}x{ty} 재인코딩 완료")
        ok += 1

    print(f"injected: {ok}/{len(pngs)}")

if __name__ == "__main__":
    main()
