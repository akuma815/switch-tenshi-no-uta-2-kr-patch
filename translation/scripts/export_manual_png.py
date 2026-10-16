"""매뉴얼 Texture2D uexp -> PNG 일괄 추출

사용법: python export_manual_png.py <uexp 폴더> <PNG 출력 폴더>

cooked Texture2D(uexp) 구조 (이 게임 기준):
  ... SizeX(i32) SizeY(i32) PackedData(u32) PixelFormat(FString) ... [mip payload]
  SizeX(i32) SizeY(i32) SizeZ(i32) [12B] PACKAGE_FILE_TAG(4B)   <- 파일 끝 28바이트
mip payload는 끝에서 28바이트 앞에서 역산한다.
"""
import os
import struct
import sys
import glob

import texture2ddecoder
from PIL import Image

def payload_size(fmt, w, h):
    if fmt == "PF_DXT5":
        return ((w + 3) // 4) * ((h + 3) // 4) * 16
    if fmt == "PF_DXT1":
        return ((w + 3) // 4) * ((h + 3) // 4) * 8
    if fmt == "PF_B8G8R8A8":
        return w * h * 4
    if fmt.startswith("PF_ASTC_"):
        bx, by = map(int, fmt.rsplit("_", 1)[1].split("x"))
        return ((w + bx - 1) // bx) * ((h + by - 1) // by) * 16
    raise ValueError(f"unsupported format {fmt}")

def decode(fmt, data, w, h):
    if fmt == "PF_DXT5":
        return texture2ddecoder.decode_bc3(data, w, h)
    if fmt == "PF_DXT1":
        return texture2ddecoder.decode_bc1(data, w, h)
    if fmt == "PF_B8G8R8A8":
        return data
    if fmt.startswith("PF_ASTC_"):
        bx, by = map(int, fmt.rsplit("_", 1)[1].split("x"))
        return texture2ddecoder.decode_astc(data, w, h, bx, by)
    raise ValueError(fmt)

def export_one(uexp_path, out_png):
    data = open(uexp_path, "rb").read()
    n = len(data)
    if data[n-4:] != b"\xc1\x83\x2a\x9e":
        raise ValueError("missing PACKAGE_FILE_TAG")

    idx = data.find(b"PF_")
    if idx < 0:
        raise ValueError("no PF_ string")
    strlen = struct.unpack_from("<i", data, idx - 4)[0]
    fmt = data[idx:idx + strlen - 1].decode()
    hx, hy, _packed = struct.unpack_from("<iiI", data, idx - 16)

    tx, ty, tz = struct.unpack_from("<iii", data, n - 28)
    if not (0 < tx <= 8192 and 0 < ty <= 8192 and tz == 1):
        raise ValueError(f"bad tail dims {tx}x{ty}x{tz}")

    psize = payload_size(fmt, tx, ty)
    start = n - 28 - psize
    if start < idx:
        raise ValueError(f"payload start {start} overlaps header")
    payload = data[start:n - 28]

    bgra = decode(fmt, payload, tx, ty)
    img = Image.frombytes("RGBA", (tx, ty), bytes(bgra), "raw", "BGRA")
    img.save(out_png)
    return fmt, tx, ty, hx, hy

def main():
    src_dir = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src_dir, "**", "Manual*_*.uexp"), recursive=True),
                   key=lambda p: int(os.path.splitext(os.path.basename(p))[0].rsplit("_", 1)[1]))
    ok = 0
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        out_png = os.path.join(out_dir, f"{name}.png")
        try:
            fmt, tx, ty, hx, hy = export_one(f, out_png)
            note = "" if (tx, ty) == (hx, hy) else f" (header says {hx}x{hy})"
            print(f"  {name}: {fmt} {tx}x{ty}{note} -> {os.path.basename(out_png)}")
            ok += 1
        except Exception as e:
            print(f"  {name}: FAILED - {e}")
    print(f"done: {ok}/{len(files)}")

if __name__ == "__main__":
    main()
