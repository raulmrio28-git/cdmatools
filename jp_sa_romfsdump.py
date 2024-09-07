import struct
import sys
import os

if __name__ == "__main__":
    f = open(sys.argv[1], "rb")
    os.makedirs(f"{sys.argv[2]}/", exist_ok=True)

    unk0, unk1, unk2, unk3 = struct.unpack("<LLLL", f.read(0x10))
    while True:
        name = f.read(0x100).replace(b"\0", b"").decode("ascii")
        if len(name) <= 0: break

        print(name)
        size, unk, offset_2k, pad_start = struct.unpack("<LLLL", f.read(0x10))

        if unk: print(hex(unk))

        temp = f.tell()
        f.seek(((offset_2k - 1) * 0x800) + pad_start)
        open(f"{sys.argv[2]}/{name}", "wb").write(f.read(size))
        f.seek(temp)
        
