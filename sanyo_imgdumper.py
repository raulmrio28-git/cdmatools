import os
import sanyo_rle
import sanyo_dec_mod
import sys
import struct

if __name__ == "__main__":
    file_size = os.path.getsize(sys.argv[1])
    file_io = open(sys.argv[1], "rb")
    EXTRACT_PATH = f"{sys.argv[1]}_extracted/"
    os.makedirs(EXTRACT_PATH, exist_ok=True)

    if len(sys.argv) >= 3:
        file_io.seek(int(sys.argv[2], 16))

    count = 0
    while file_io.tell()<file_size:
        sof = file_io.tell()        
        
        header = file_io.read(3)

        if len(header) < 3: break

        if header in [b"UP\0", b"I8\0", b"IC\0", b"MT\0"]:
            print(count+1, hex(file_io.tell()), header)

            width = file_io.read(1)[0]
            height = file_io.read(1)[0]

            if header == b"IC\0":
                sanyo_rle.OldSanyoRLE_DecompressFD(file_io, width, height)
            elif header == b"I8\0":
                file_io.read(width*height)
            else:
                file_io.read(int((width*height)/8))

        elif header in [b"CW\0", b"CH\0", b"IX\0", b"IW\0", b"IH\0"]:
            print(count+1, hex(file_io.tell()), header)
            if header == b"IH\0" or header == b"IX\0":
                file_io.read(1)

            width = file_io.read(1)[0]
            height = file_io.read(1)[0]
            file_io.read(2)
            
            #print(hex(header[0]))
            if header[0] == 0x43:                
                sanyo_rle.SanyoRLE_DecompressFD(file_io, width, height, 16)
            else:
                #print((width*height)*2)
                file_io.read((width*height)*2)

        elif header in [b"PW\0", b"PH\0"]:
            print(count+1, hex(file_io.tell()), header)

            palette_size = file_io.read(1)[0]+1  

            width = file_io.read(1)[0]
            height = file_io.read(1)[0]
            file_io.read(2)

            file_io.read(palette_size*2)
            sanyo_rle.SanyoRLE_DecompressFD(file_io, width, height)

        elif header == b"PP\0":
            print(count+1, hex(file_io.tell()), header)

            palette_size = file_io.read(1)[0]+1  

            width = struct.unpack("<H", file_io.read(2))[0]
            height = struct.unpack("<H", file_io.read(2))[0]
            file_io.read(2)

            if width > 480 or height > 480: continue

            file_io.read(palette_size*2)
            sanyo_rle.SanyoRLE_DecompressFD(file_io, width, height)

        elif header in [b"SI\x10", b"SR\x10"]:
            file_io.read(3)
            width = struct.unpack("<H", file_io.read(2))[0]
            height = struct.unpack("<H", file_io.read(2))[0]
            print("SI ahead")

            if width > 480 or height > 480: continue

            if header == b"SR\x10":
                file_io.read(6)
                sanyo_rle.SanyoRLE_DecompressFD(file_io, width, height)
            
            else:
                file_io.read(3)
                palette_size = struct.unpack("<H", file_io.read(2))[0]+1

                file_io.read(1)

                file_io.read(palette_size*2)
                sanyo_rle.SanyoRLE_DecompressFD(file_io, width, height)

        else:            
            file_io.seek(file_io.tell()-2)
            continue
                    
        eof = file_io.tell()
        print(hex(sof), hex(eof))
        file_io.seek(sof)

        count += 1
        #print(count, hex(file_io.tell()))

        open(f"{EXTRACT_PATH}/{count}.{header[:2].decode('ascii').lower()}", "wb").write(file_io.read(eof-sof))
        
        if header[:2].decode('ascii') != "UP":
            try:
                sanyo_dec_mod.decompress(f"{EXTRACT_PATH}/{count}.{header[:2].decode('ascii').lower()}", f"{EXTRACT_PATH}/{count}.{header[:2].decode('ascii').lower()}.png")
            except Exception:
                import traceback
                traceback.print_exc()   

