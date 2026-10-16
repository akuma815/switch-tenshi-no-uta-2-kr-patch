import struct
import sys

uasset_path = sys.argv[1]
old_serial_size = int(sys.argv[2])
serial_offset = int(sys.argv[3])
new_serial_size = int(sys.argv[4])
out_path = sys.argv[5]

with open(uasset_path, "rb") as f:
    data = bytearray(f.read())

# modern UE FObjectExport stores SerialSize/SerialOffset as int64, SerialSize immediately followed by SerialOffset
needle = struct.pack("<qq", old_serial_size, serial_offset)
positions = []
start = 0
while True:
    idx = data.find(needle, start)
    if idx == -1:
        break
    positions.append(idx)
    start = idx + 1

if len(positions) != 1:
    print(f"ERROR: expected exactly 1 match for (SerialSize={old_serial_size}, SerialOffset={serial_offset}) as int64 pair, found {len(positions)}: {positions}")
    sys.exit(1)

pos = positions[0]
new_bytes = struct.pack("<q", new_serial_size)
data[pos:pos+8] = new_bytes

with open(out_path, "wb") as f:
    f.write(bytes(data))

print(f"patched SerialSize at byte offset {pos}: {old_serial_size} -> {new_serial_size} (file size unchanged: {len(data)})")
