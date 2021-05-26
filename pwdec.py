import os
import sys
from PIL import Image
import struct

sz = os.path.getsize(sys.argv[1])
df = open(sys.argv[1], "rb")
pts = []

assert df.read(3) == b"PW\x00" # PW\x00
palette_size = df.read(1)[0]+1
width = df.read(1)[0]
height = df.read(1)[0]
df.read(2)

def rgb565toi24(data):
	from io import BytesIO
	offset = 0
	outp = BytesIO()
	while offset<len(data):
		inp = struct.unpack("<H", data[offset:offset+2])[0]
		rgb = (((inp & 0xF800) >> 8), ((inp & 0x07E0) >> 3), ((inp & 0x001F) << 3))
		outp.write(struct.pack("<BBB", *rgb))
		offset += 2
	return outp.getvalue()

for _ in range(palette_size):
	pts.append(rgb565toi24(df.read(2)))

temp = bytearray()
raw = False
pixel = 0

while df.tell()<sz:
	cnt = df.read(1)[0]
	if cnt == 0xff: 
		raw = False
		pixel = 0
		continue
	if cnt == 0x00 and (not raw or pixel >= width): 
		raw = True
		pixel = 0
		continue

	if raw:
		if cnt > len(pts): 
			print(f"wrong palette {cnt}")
			cnt = 0
		pixel += 1
		temp += pts[cnt]
		continue
	cpl = df.read(1)[0]
	if cpl > len(pts): 
		print(f"wrong palette {cpl}")
		cpl = 0
	adt = pts[cpl]
	temp += adt*cnt
	
Image.frombuffer("RGB", (width, height), bytes(temp)).save(sys.argv[2])
	