from pathlib import Path
import struct
import sys


SOURCE_OFFSET = 15235
SCENE_ID_OFFSET = SOURCE_OFFSET + 12
START_TIME_OFFSET = SOURCE_OFFSET + 16
END_TIME_OFFSET = SOURCE_OFFSET + 20
EXPECTED_CONTEXT = bytes.fromhex(
    "a7000000000000008013180013000000000050416666d441"
)
EXPECTED_SCENE_ID = 19
REPLACEMENT_SCENE_ID = 8
EXPECTED_START_TIME = 13.0
REPLACEMENT_START_TIME = 22.0
EXPECTED_END_TIME = 26.55


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: patch_visualscene_scene_id.py <src.uexp> <dst.uexp>")
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    data = bytearray(src.read_bytes())

    actual_context = bytes(data[SOURCE_OFFSET : SOURCE_OFFSET + len(EXPECTED_CONTEXT)])
    if actual_context != EXPECTED_CONTEXT:
        raise RuntimeError(
            f"visual-scene metadata mismatch at {SOURCE_OFFSET}: "
            f"expected {EXPECTED_CONTEXT.hex()}, got {actual_context.hex()}"
        )

    if data.count(EXPECTED_CONTEXT) != 1:
        raise RuntimeError("visual-scene metadata context is not unique")

    scene_id = struct.unpack_from("<I", data, SCENE_ID_OFFSET)[0]
    if scene_id != EXPECTED_SCENE_ID:
        raise RuntimeError(
            f"unexpected scene ID at {SCENE_ID_OFFSET}: "
            f"expected {EXPECTED_SCENE_ID}, got {scene_id}"
        )

    start_time = struct.unpack_from("<f", data, START_TIME_OFFSET)[0]
    end_time = struct.unpack_from("<f", data, END_TIME_OFFSET)[0]
    if start_time != EXPECTED_START_TIME or abs(end_time - EXPECTED_END_TIME) > 0.0001:
        raise RuntimeError(
            f"unexpected subtitle timing: expected "
            f"{EXPECTED_START_TIME:.2f}-{EXPECTED_END_TIME:.2f}, got "
            f"{start_time:.2f}-{end_time:.2f}"
        )

    struct.pack_into("<I", data, SCENE_ID_OFFSET, REPLACEMENT_SCENE_ID)
    struct.pack_into("<f", data, START_TIME_OFFSET, REPLACEMENT_START_TIME)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    print(
        f"patched VisualSceneID at {SCENE_ID_OFFSET}: "
        f"{EXPECTED_SCENE_ID} -> {REPLACEMENT_SCENE_ID}; "
        f"timing {EXPECTED_START_TIME:.2f}-{EXPECTED_END_TIME:.2f} -> "
        f"{REPLACEMENT_START_TIME:.2f}-{EXPECTED_END_TIME:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
