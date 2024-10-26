import typing
import io
import struct

def OldSanyoRLE_Decompress(data: typing.Union[bytes, bytearray], bpp: int=8):
    output = bytearray()

    data_buf = io.BytesIO(data)
    while data_buf.tell()<len(data):
        image_bit = data_buf.read(1)
        flag = data_buf.read(1)[0]
        count = flag

        if flag == 0:
            count = struct.unpack("<H", data_buf.read(2))[0]

        output += image_bit*count

    return output

def SanyoRLE_Decompress(data: typing.Union[bytes, bytearray], width: int, bpp: int=8, max_size: int=-1):
    output = bytearray()

    data_buf = io.BytesIO(data)
    while data_buf.tell()<len(data) and (max_size < 0 or len(output) < (max_size * (bpp//8))):
        flag = data_buf.read(1)[0]
        pRev = data_buf.tell() - 1
        assert flag in [0, 0xff], f"error: {hex(flag)}), {hex(pRev)}"

        if flag == 0:
            output += data_buf.read(width*int(bpp/8))

        else:
            pixel = 0
            while pixel<width:
                count = data_buf.read(1)[0]
                #if count == 0: count = 2
                xpp = data_buf.read(int(bpp/8))
                #print("c:", hex(count), "x:", xpp, "px:", hex(pixel), hex(pRev))
                output += xpp*count
                pixel += count

    return output

def OldSanyoRLE_DecompressFD(data: io.IOBase, width: int, height: int, bpp: int=8):
    output = bytearray()

    while len(output)<int((width*height)*(bpp/8)):
        image_bit = data.read(1)
        if image_bit == b"": break
        flag = data.read(1)[0]
        count = flag

        if flag == 0:
            count = struct.unpack("<H", data.read(2))[0]

        output += image_bit*count

    return output

def SanyoRLE_DecompressFD(data: io.IOBase, width: int, height: int, bpp: int=8):
    output = bytearray()
    
    while len(output)<int((width*height)*(bpp/8)):
        flag = data.read(1)[0]
        if flag == b"": break
        if flag == 0:
            output += data.read(width*int(bpp/8))
        else:
            pixel = 0
            while pixel<width:
                count = data.read(1)[0]
                output += data.read(int(bpp/8))*count
                pixel += count

    return output    