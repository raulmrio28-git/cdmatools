import os
import sys
from PIL import Image
import struct
import enum
import sanyo_rle

RGB332 = b"\x00\x00\x00\x00\x00\x55\x00\x00\xaa\x00\x00\xff\x00\x24\x00\x00\x24\x55\x00\x24\xaa\x00\x24\xff\x00\x48\x00\x00\x48\x55\x00\x48\xaa\x00\x48\xff\x00\x6c\x00\x00\x6c\x55\x00\x6c\xaa\x00\x6c\xff\x00\x90\x00\x00\x90\x55\x00\x90\xaa\x00\x90\xff\x00\xb4\x00\x00\xb4\x55\x00\xb4\xaa\x00\xb4\xff\x00\xd8\x00\x00\xd8\x55\x00\xd8\xaa\x00\xd8\xff\x00\xfc\x00\x00\xfc\x55\x00\xfc\xaa\x00\xfc\xff\x24\x00\x00\x24\x00\x55\x24\x00\xaa\x24\x00\xff\x24\x24\x00\x24\x24\x55\x24\x24\xaa\x24\x24\xff\x24\x48\x00\x24\x48\x55\x24\x48\xaa\x24\x48\xff\x24\x6c\x00\x24\x6c\x55\x24\x6c\xaa\x24\x6c\xff\x24\x90\x00\x24\x90\x55\x24\x90\xaa\x24\x90\xff\x24\xb4\x00\x24\xb4\x55\x24\xb4\xaa\x24\xb4\xff\x24\xd8\x00\x24\xd8\x55\x24\xd8\xaa\x24\xd8\xff\x24\xfc\x00\x24\xfc\x55\x24\xfc\xaa\x24\xfc\xff\x48\x00\x00\x48\x00\x55\x48\x00\xaa\x48\x00\xff\x48\x24\x00\x48\x24\x55\x48\x24\xaa\x48\x24\xff\x48\x48\x00\x48\x48\x55\x48\x48\xaa\x48\x48\xff\x48\x6c\x00\x48\x6c\x55\x48\x6c\xaa\x48\x6c\xff\x48\x90\x00\x48\x90\x55\x48\x90\xaa\x48\x90\xff\x48\xb4\x00\x48\xb4\x55\x48\xb4\xaa\x48\xb4\xff\x48\xd8\x00\x48\xd8\x55\x48\xd8\xaa\x48\xd8\xff\x48\xfc\x00\x48\xfc\x55\x48\xfc\xaa\x48\xfc\xff\x6c\x00\x00\x6c\x00\x55\x6c\x00\xaa\x6c\x00\xff\x6c\x24\x00\x6c\x24\x55\x6c\x24\xaa\x6c\x24\xff\x6c\x48\x00\x6c\x48\x55\x6c\x48\xaa\x6c\x48\xff\x6c\x6c\x00\x6c\x6c\x55\x6c\x6c\xaa\x6c\x6c\xff\x6c\x90\x00\x6c\x90\x55\x6c\x90\xaa\x6c\x90\xff\x6c\xb4\x00\x6c\xb4\x55\x6c\xb4\xaa\x6c\xb4\xff\x6c\xd8\x00\x6c\xd8\x55\x6c\xd8\xaa\x6c\xd8\xff\x6c\xfc\x00\x6c\xfc\x55\x6c\xfc\xaa\x6c\xfc\xff\x90\x00\x00\x90\x00\x55\x90\x00\xaa\x90\x00\xff\x90\x24\x00\x90\x24\x55\x90\x24\xaa\x90\x24\xff\x90\x48\x00\x90\x48\x55\x90\x48\xaa\x90\x48\xff\x90\x6c\x00\x90\x6c\x55\x90\x6c\xaa\x90\x6c\xff\x90\x90\x00\x90\x90\x55\x90\x90\xaa\x90\x90\xff\x90\xb4\x00\x90\xb4\x55\x90\xb4\xaa\x90\xb4\xff\x90\xd8\x00\x90\xd8\x55\x90\xd8\xaa\x90\xd8\xff\x90\xfc\x00\x90\xfc\x55\x90\xfc\xaa\x90\xfc\xff\xb4\x00\x00\xb4\x00\x55\xb4\x00\xaa\xb4\x00\xff\xb4\x24\x00\xb4\x24\x55\xb4\x24\xaa\xb4\x24\xff\xb4\x48\x00\xb4\x48\x55\xb4\x48\xaa\xb4\x48\xff\xb4\x6c\x00\xb4\x6c\x55\xb4\x6c\xaa\xb4\x6c\xff\xb4\x90\x00\xb4\x90\x55\xb4\x90\xaa\xb4\x90\xff\xb4\xb4\x00\xb4\xb4\x55\xb4\xb4\xaa\xb4\xb4\xff\xb4\xd8\x00\xb4\xd8\x55\xb4\xd8\xaa\xb4\xd8\xff\xb4\xfc\x00\xb4\xfc\x55\xb4\xfc\xaa\xb4\xfc\xff\xd8\x00\x00\xd8\x00\x55\xd8\x00\xaa\xd8\x00\xff\xd8\x24\x00\xd8\x24\x55\xd8\x24\xaa\xd8\x24\xff\xd8\x48\x00\xd8\x48\x55\xd8\x48\xaa\xd8\x48\xff\xd8\x6c\x00\xd8\x6c\x55\xd8\x6c\xaa\xd8\x6c\xff\xd8\x90\x00\xd8\x90\x55\xd8\x90\xaa\xd8\x90\xff\xd8\xb4\x00\xd8\xb4\x55\xd8\xb4\xaa\xd8\xb4\xff\xd8\xd8\x00\xd8\xd8\x55\xd8\xd8\xaa\xd8\xd8\xff\xd8\xfc\x00\xd8\xfc\x55\xd8\xfc\xaa\xd8\xfc\xff\xfc\x00\x00\xfc\x00\x55\xfc\x00\xaa\xfc\x00\xff\xfc\x24\x00\xfc\x24\x55\xfc\x24\xaa\xfc\x24\xff\xfc\x48\x00\xfc\x48\x55\xfc\x48\xaa\xfc\x48\xff\xfc\x6c\x00\xfc\x6c\x55\xfc\x6c\xaa\xfc\x6c\xff\xfc\x90\x00\xfc\x90\x55\xfc\x90\xaa\xfc\x90\xff\xfc\xb4\x00\xfc\xb4\x55\xfc\xb4\xaa\xfc\xb4\xff\xfc\xd8\x00\xfc\xd8\x55\xfc\xd8\xaa\xfc\xd8\xff\xfc\xfc\x00\xfc\xfc\x55\xfc\xfc\xaa\xfc\xfc\xff"

'''
def getpalette(num, arr):
	index = num*3
	return arr[index:index+3]
'''

'''
def delta(data):
    offset = 0
    output = bytearray()
    while offset<len(data):
        output += struct.pack("<B", data[offset]^(0 if offset+1 >= len(data) else data[offset+1]))
        offset += 1
    return output
'''

def getpalette3(num, arr):
    index = num*3    
    #assert arr[index:index+3]
    return arr[index:index+3]+b"\xff"

def getpalette4(num, arr):
    index = num*4
    #assert arr[index:index+4]
    return arr[index:index+4]

def rgb444toi32(data, transp):
	from io import BytesIO
	offset = 0
	outp = BytesIO()
	while offset<len(data):
		inp = struct.unpack("<H", data[offset:offset+2])[0]
		rgb = (((inp>>12)&0xf)<<4,((inp>>8)&0xf)<<4,((inp>>4)&0xf)<<4, 0 if data[offset:offset+2] == transp else 255)
		outp.write(struct.pack("<BBBB", *rgb))
		offset += 2
	return outp.getvalue()
	
def rgb565toi32(data, transp):
	from io import BytesIO
	offset = 0
	outp = BytesIO()
	while offset<len(data):
		inp = struct.unpack("<H", data[offset:offset+2])[0]
		rgb = (((inp & 0xF800) >> 8), ((inp & 0x07E0) >> 3), ((inp & 0x001F) << 3), 0 if data[offset:offset+2] == transp else 255)
		outp.write(struct.pack("<BBBB", *rgb))
		offset += 2
	return outp.getvalue()	

if __name__ == "__main__":
    file_size = os.path.getsize(sys.argv[1])
    file_io = open(sys.argv[1], "rb")
    output = bytearray()
    output_name = sys.argv[2]

    header = file_io.read(3)

    bpp, width, height, transparency, palette_size, i_bpp, palette, data, codec = (0,0,0,None,0,0,b"",b"",0)

    class Codecs(enum.IntEnum):
        SanyoRLE = 0
        OldSanyoRLE = 1
        RAW = 2

    if header == b"SI\x10" or header == b"SR\x10" or header == b"PL\x00":
        transp_index = None
        sr_compressed = False

        if header == b"PL\x00":
            assert file_io.read(1)[0] == 0xff
            bpp = 2

        else:
            transp_index = file_io.read(1)[0]-1    
            bpp = file_io.read(1)[0]
            sr_compressed = file_io.read(1)[0] > 0

            assert bpp in [2], f"{8*bpp} SI images were currently unsupported."    
        
        width = struct.unpack("<H", file_io.read(2))[0]
        height = struct.unpack("<H", file_io.read(2))[0]

        if header == b"PL\x00":
            file_io.read(1)
            
            transparency = file_io.read(2)
            if transparency == b"\xff\xff":
                transparency = None

            palette_size = struct.unpack("<H", file_io.read(2))[0]+1

        else:
            file_io.read(2)

            if header == b"SI\x10":
                file_io.read(1)
                palette_size = struct.unpack("<H", file_io.read(2))[0]+1
            else:
                transparency = file_io.read(2)
                if transp_index < 0:
                    transparency = None
                file_io.read(1)

        i_bpp = file_io.read(1)[0]
        assert i_bpp in [0,8], f"{i_bpp} formatted SI images were currently unsupported."
        
        if i_bpp == 0:
            i_bpp = 8*bpp

        if header == b"SI\x10" or header == b"PL\x00":
            i_bpp = 8

        if header == b"SI\x10" or header == b"PL\x00":
            palette = file_io.read(palette_size*bpp)
            if header == b"SI\x10" and transp_index >= 0:
                transparency = palette[(transp_index*bpp):(transp_index*bpp)+bpp]

        data = file_io.read()
        codec = Codecs.SanyoRLE if header == b"SI\x10" or header == b"PL\x00" or sr_compressed else Codecs.RAW

    elif header == b"CW\0" or header == b"CH\0" or header == b"IX\0" or header == b"IW\0" or header == b"IH\0":
        if header == b"IH\0" or header == b"IX\0":
            file_io.read(1)

        width = file_io.read(1)[0]
        height = file_io.read(1)[0]

        transparency = file_io.read(2)
        if transparency == b"\xff\xff":
            transparency = None

        data = file_io.read()
        codec = Codecs.SanyoRLE if header[0] == 0x43 else Codecs.RAW
        i_bpp = 15 if header[1] == 0x48 else 16

    elif header == b"PW\0" or header == b"PH\0" or header == b"PP\0":
        palette_size = file_io.read(1)[0]+1        

        if header[1] == 0x50:
            width = struct.unpack("<H", file_io.read(2))[0]
            height = struct.unpack("<H", file_io.read(2))[0]
        else:
            width = file_io.read(1)[0]
            height = file_io.read(1)[0]        

        transparency = file_io.read(2)
        if transparency == b"\xff\xff":
            transparency = None

        palette = file_io.read(palette_size*2)        

        data = file_io.read()
        codec = Codecs.SanyoRLE
        
        i_bpp = 8
        bpp = 3 if header[1] == 0x48 else 2

    elif header == b"UP\0" or header == b"I8\0" or header == b"IC\0" or header == b"MT\0":
        width = file_io.read(1)[0]
        height = file_io.read(1)[0]

        data = file_io.read()
        codec = Codecs.OldSanyoRLE if header == b"IC\0" else Codecs.RAW
        i_bpp = 8 if header == b"I8\0" or header == b"IC\0" else 1
    
    else:
        raise Exception("not a sanyo image format")

    if bpp == 3:
        palette = rgb444toi32(palette, transparency)
    elif bpp == 2:
        palette = rgb565toi32(palette, transparency)
            
    if codec == Codecs.SanyoRLE:
        output = sanyo_rle.SanyoRLE_Decompress(data, width, 16 if i_bpp == 15 else i_bpp)
    elif codec == Codecs.OldSanyoRLE:
        output = sanyo_rle.OldSanyoRLE_Decompress(data)
    elif codec == Codecs.RAW:
        output = data
    else:
        raise Exception("unknown codec")

    if i_bpp == 8:
        getpalette = getpalette4

        if not palette:
            palette = RGB332
            getpalette = getpalette3        

        output = b"".join([getpalette(a, palette) for a in output])

    elif i_bpp == 15:
        output = rgb444toi32(output, transparency)
    elif i_bpp == 16:
        output = rgb565toi32(output, transparency)
    
    Image.frombytes("1" if i_bpp == 1 else "RGBA", (width,height), output).save(output_name)
