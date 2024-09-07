from construct import *
import sys
import struct
import io
import typing
import hexdump

CODING = "latin-1"

superblock_data = Struct(
    "page_header" / Hex(Int32ul),
    "version" / Hex(Int16ul),
    "age" / Hex(Int16ul),
    "magic1" / Const(b'\x45\x46\x53\x53'),
    "magic2" / Const(b'\x75\x70\x65\x72'),
    "block_size" / Hex(Int32ul),
    "page_size" / Hex(Int32ul),
    "block_count" / Hex(Int32ul),
    "block_length" / Hex(Computed(this.block_size * \
                                  this.page_size)),
    "page_total" / Hex(Computed(this.block_size * this.block_count)),
    "is_nand" / IfThenElse(this.version > 0xa, Computed((this.version & 1) == 1), Computed((this.version & 1) == 0)),
    "log_head" / Hex(Int32ul),
    "alloc_next" / Array(4, Hex(Int32ul)),
    "gc_next" / Array(4, Hex(Int32ul)),
    "upper_data" / IfThenElse(this.version >= 0x24, Array(32, Hex(Int32ul)), Array(7, Hex(Int32ul))),
    "nand_info" / IfThenElse(this.is_nand, Struct(
        "nodes_per_page" / Hex(Int16ul),
        "page_depth" / Hex(Int16ul),
        "super_nodes" / Hex(Int16ul),
        "num_regions" / Hex(Int16ul),
        "regions" / Array(this.num_regions, Hex(Int32ul)),
        "logr_badmap" / Hex(Int32ul),
        "pad" / Hex(Int32ul),        
        "tables" / IfThenElse(this._.page_size == 0x800, Array(0xe2, Hex(Int32ul)), IfThenElse(this._.version >= 0x24, Array(0x22, Hex(Int32ul)), Array(0x30, Hex(Int32ul)))),
        "tables2" / IfThenElse(this._.page_size == 0x800, Array(0xe2, Hex(Int32ul)), IfThenElse(this._.version >= 0x24, Array(0x22, Hex(Int32ul)), Array(0x30, Hex(Int32ul)))),
    ), Struct(
        "nor_style" / Hex(Int16ul)
    )),    
    "db_root_clust" / Computed(this.upper_data[2]),
    "fs_info_clust" / Computed(this.upper_data[3]),
)

fs_inode_data = Struct(
    "mode" / Hex(Int16ul),
    "nlink" / Hex(Int16ul),
    "attr" / Hex(Int32ul),
    "size" / Hex(Int32ul),
    "uid" / Hex(Int16ul),
    "gid" / Hex(Int16ul),
    "generation" / Hex(Int32ul),
    "blocks" / Hex(Int32ul),
    "mtime" / Hex(Int32ul),
    "ctime" / Hex(Int32ul),
    "atime" / Hex(Int32ul),
    "reserved" / Array(7, Hex(Int32ul)),
    "direct_cluster_id" / Array(13, Hex(Int32ul)),
    "indirect_cluster_id" / Array(3, Hex(Int32ul)),
)

fs_inode_data_old = Struct(
    "mode" / Hex(Int16ul),
    "nlink" / Hex(Int16ul),    
    "size" / Hex(Int32ul),    
    "generation" / Hex(Int32ul),
    "blocks" / Hex(Int32ul),
    "mtime" / Hex(Int32ul),
    "ctime" / Hex(Int32ul),        
    "direct_cluster_id" / Array(6, Hex(Int32ul)),
    "indirect_cluster_id" / Array(3, Hex(Int32ul)),
)

node_data = Struct(
    "prev" / Hex(Int32ul),
    "next" / Hex(Int32ul),
    "used" / Hex(Int16ul),
    "pad" / Hex(Int16ul),
    "gid" / Hex(Int32ul),
    "bogus_count" / Hex(Byte),
    "level" / Hex(Byte),
    "data" / Bytes(this.used),
)

node_data_old = Struct(
    "prev" / Hex(Int32ul),
    "next" / Hex(Int32ul),
    "used" / Hex(Int16ul),    
    "bogus_count" / Hex(Byte),
    "level" / Hex(Byte),
    "data" / Bytes(this.used),
)

efs_info_data = Struct(
    "magic" / Const(b"\xa0\x3e\xb9\xa7"),
    "version" / Hex(Int32ul),
    "inode_top" / Hex(Int32ul),
    "inode_next" / Hex(Int32ul),
    "inode_free" / Hex(Int32ul),
    "root_inode" / Hex(Int32ul),
    "partial_delete" / Hex(Int8ul),
    "partial_delete_mid" / Hex(Int8ul),
    "partial_delete_gid" / Hex(Int16ul),
    "partial_delete_data" / Array(4, Hex(Int32ul)),
)

class EFS2():
    def __init__(self, file, base_offset: int=-1, super: int=-1, parse_nodes: bool=True):            
        self.file = file
        self.sb = None        
        
        if base_offset != -1:
            self.file.seek(base_offset)
        
        self.super_offsets = []        
        sbs = []        

        while True:
            try:                          
                sb_temp = self.file.tell()  
                t = superblock_data.parse(self.file.read(0x4000))
                self.super_offsets.append(sb_temp)

                sbs.append(t)
                if self.sb is None or (t["age"] > self.sb["age"]):
                    self.cur_super_offset = len(self.super_offsets) - 1
                    self.sb = t                                    
            
            except ConstError as e:            
                pass

            except StreamError as e:                            
                break
                        
        if super != -1: 
            self.sb = sbs[super]
            self.cur_super_offset = super        

        self.ptables = [0xffffffff] * self.sb.page_total        

        self.efs_size = self.sb.page_total * self.sb.page_size
        sb_padding = 0 if (len(self.super_offsets) & 7) == 0 else 8 - (len(self.super_offsets) & 7)        

        self.efs_end = (self.super_offsets[-1] + (sb_padding * self.sb.block_length) + self.sb.block_length) if self.sb.is_nand else (self.super_offsets[-1] + self.sb.block_length)
        self.efs_start = (self.efs_end - (self.sb.page_total * self.sb.page_size)) if self.sb.is_nand else self.super_offsets[0]
        
        if base_offset == -1:
            print(f"AUTOEFS: {self.efs_start:08x}")
            base_offset = self.efs_start

        self.base_offset = base_offset        
                    
        if not self.sb.is_nand: 
            sb_mask = 0
            while True:
                if ((1 << sb_mask) >= self.sb.block_size):
                    break

                sb_mask += 1             

            minor_mask = (self.sb.page_size >> (2 if self.sb.nand_info.nor_style == 0 else 3)) - 1
            temp = minor_mask

            major_shift = 0
            while temp != 0:
                temp >>= 1
                major_shift += 1

            reserved = self.sb.block_size - ((self.sb.block_size + minor_mask) >> major_shift)            

            major_pt = reserved + ((self.sb.block_size - 1) >> major_shift)        
            minor_pt = (self.sb.block_size - 1) & minor_mask            
            
            def lookup_rtable(page: int):
                curBlock = (page >> sb_mask) << sb_mask
                pOffset = page % self.sb.block_size

                if pOffset >= reserved:
                    return 0xfffffff9 # Reserved
                
                pMajor = reserved + (pOffset >> major_shift)
                pMinor = pOffset & minor_mask

                pCurMajorPP = curBlock + pMajor
                pCurMajorMinorMagicCheckPP = curBlock + major_pt

                self.file.seek(base_offset + (pCurMajorMinorMagicCheckPP * self.sb.page_size + (minor_pt * 4)))
                if self.file.read(4) != b"\xe1\xe1\xf0\xf0": return 0xfffffff4 # Garbage                

                self.file.seek(base_offset + (pCurMajorPP * self.sb.page_size + (pMinor * 4)))
                return int.from_bytes(self.file.read(4), "little")
            
            for p in range(self.sb.page_total):
                t = lookup_rtable(p)
                if (t >> 31) == 0 and (t & 0xffffff) != 0:                
                    if self.ptables[t & 0xffffff] != 0xffffffff:
                        raise Exception("remap detected?")

                    self.ptables[t & 0xffffff] = p            

        else:
            c = 0
            
            for t in self.sb.nand_info.tables:
                if t >= self.sb.page_total: break                
                                                
                if self.sb.nand_info.page_depth > 1:
                    self.file.seek(base_offset + (t * self.sb.page_size))

                    def recurse_node(depth):
                        nonlocal c

                        for _ in range(self.sb.nand_info.nodes_per_page):
                            if depth > 0:
                                ptr = int.from_bytes(self.file.read(4), "little")
                                if ptr >= self.sb.page_total:
                                    c += self.sb.nand_info.nodes_per_page * depth

                                else:
                                    temp = self.file.tell()
                                    self.file.seek(base_offset + (ptr * self.sb.page_size))

                                    recurse_node(depth - 1)

                                    self.file.seek(temp)

                            else:
                                ptr = int.from_bytes(self.file.read(4), "little")

                                if ptr < self.sb.page_total:
                                    self.ptables[c] = ptr

                                c += 1

                    recurse_node(self.sb.nand_info.page_depth - 2)

                else:
                    self.ptables[c] = t
                    c += 1                           

        if parse_nodes:
            self.file.seek(base_offset + (self.ptables[self.sb.fs_info_clust] * self.sb.page_size))
            self.efs_info = efs_info_data.parse_stream(self.file)            
            self.nodes = self.parse_node(self.sb.db_root_clust)    

            self.cur_inode = self.efs_info.root_inode
            self.pwd = "/"

    def resolve(self, pathname_actual: str):       
        pathname = pathname_actual if len(pathname_actual) <= 1 else pathname_actual.rstrip("/")        
        fPath = []

        path_count = pathname.split("/")        
        if len(path_count[0]) <= 0:
            fPath.append("")
            inode_cur = self.efs_info.root_inode        
            path_count.pop(0)

        else:
            inode_cur = self.cur_inode

        for e, f in enumerate(path_count):            
            if e != 0 and len(f) <= 0: continue
            fPath.append(f)

            isLast = e >= len(path_count) - 1
            matchNode = None
            
            for i in self.nodes[inode_cur]:
                if i["node_name"] == b"" and f in [".", ""]:
                    matchNode = i
                elif i["node_name"] == b"\0" and f == "..":
                    matchNode = i
                elif i["node_name"].decode(CODING) == f:
                    matchNode = i

            if matchNode == None: raise FileNotFoundError(pathname_actual)

            if isLast:                
                return matchNode, fPath

            else:
                if "inode" not in matchNode or matchNode["inode"][3] not in self.nodes: raise NotADirectoryError(pathname_actual)
                inode_cur = matchNode["inode"][3]

        raise Exception("should not end here")

    def ls(self, pathname=""):
        def format_name(s):
            if s["node_name"] == b"":
                return b"."

            elif s["node_name"] == b"\0":
                return b".."
            
            elif "inode" in s and s["inode"][3] in self.nodes:
                return s["node_name"] + b"/"

            return s["node_name"]

        if len(pathname) <= 0:
            return [format_name(x).decode(CODING) for x in self.nodes[self.cur_inode]]
        
        else:
            tempI, _ = self.resolve(pathname)
            if "inode" not in tempI or tempI["inode"][3] not in self.nodes:
                return [tempI["node_name"].decode(CODING)]

            else:
                return [format_name(x).decode(CODING) for x in self.nodes[tempI["inode"][3]]]

    def ls_recursive(self, pathname=""):
        temp = []
        for f in self.ls(pathname):
            if f.endswith("/"):
                temp.append(pathname + f)
                temp.extend(self.ls_recursive(pathname + f))

            elif f not in [".", ".."]:
                temp.append(pathname + f)

        return temp

    def cd(self, pathname):
        tempI, followedPath = self.resolve(pathname)
        if "inode" not in tempI or tempI["inode"][3] not in self.nodes:
            raise NotADirectoryError(pathname)

        else:
            tempP = self.pwd.rstrip("/").split("/")                

            if pathname.startswith("/"):
                tempP = []                                

            for fp in followedPath:
                if fp == "..":                        
                    tempP.pop()                        

                elif fp != ".":
                    tempP.append(fp)

            self.pwd = "/".join(tempP) + "/"
            self.cur_inode = tempI["inode"][3]

    def open(self, pathname):
        tempI, _ = self.resolve(pathname)
        if "inode" in tempI and tempI["inode"][3] in self.nodes:
            raise IsADirectoryError(pathname)
        
        fn = self.get_file_node(tempI)

        if isinstance(fn, tuple):
            inod_tbl, inod = fn
            return INodeReader(self, inod, inod_tbl)    
        
        else:
            return io.BytesIO(fn)

    def parse_node(self, db_id: int, tFiles: dict={}):        
        self.file.seek(self.base_offset + (self.ptables[db_id] * self.sb.page_size))        
        node = (node_data if self.sb.version >= 0x24 else node_data_old).parse_stream(self.file)                        
        
        if node.level > 5:
            print(f"bad db: {hex(db_id)} {hex(node.level)} {hex(self.base_offset + (self.ptables[db_id] * self.sb.page_size))}")
        
        elif node.level != 0:            
            dbpages = [int.from_bytes(node.data[:4], "little")]
            db_offset = 4            

            while db_offset < len(node.data):                
                size = node.data[db_offset]
                data = node.data[db_offset+1:db_offset+1+size]
                assert data[0] == ord("d")
                tFiles[int.from_bytes(data[1:5], "little")] = []
                
                clust = int.from_bytes(node.data[db_offset+1+size:db_offset+1+size+4], "little")
                
                db_offset += 5 + size
                dbpages.append(clust)
            
            for d in dbpages:                
                if self.ptables[d] < self.sb.page_total and self.ptables[d] > 0:
                    tFiles = self.parse_node(d, tFiles)

        else:
            db_offset = 0          

            while db_offset < len(node.data):                
                sized = node.data[db_offset]
                sizei = node.data[db_offset+1]

                datad = node.data[db_offset+2:db_offset+2+sized]
                datai = node.data[db_offset+2+sized:db_offset+2+sized+sizei]

                assert datad[0] == ord("d")
                d_inode = int.from_bytes(datad[1:5], "little")
                d_inode_page = (d_inode >> (4 if self.sb.page_size == 0x800 else (3 if self.sb.version < 0x24 and self.sb.version not in [0xe, 0xf] else 2)))
                d_inode_index = (d_inode & (15 if self.sb.page_size == 0x800 else (7 if self.sb.version < 0x24 and self.sb.version not in [0xe, 0xf] else 3)))

                d_name = datad[5:]                
                if not d_inode in tFiles: tFiles[d_inode] = []
                
                if datai[0] == ord("i"):
                    i_inode = int.from_bytes(datai[1:5], "little")
                    i_inode_page = (i_inode >> (4 if self.sb.page_size == 0x800 else (3 if self.sb.version < 0x24 and self.sb.version not in [0xe, 0xf] else 2)))
                    i_inode_index = (i_inode & (15 if self.sb.page_size == 0x800 else (7 if self.sb.version < 0x24 and self.sb.version not in [0xe, 0xf] else 3)))
                    
                    tFiles[d_inode].append({"parent_inode": [d_inode_page, d_inode_index, 0x80 if self.sb.version >= 0x24 or self.sb.version in [0xe, 0xf] else 0x3c, d_inode], "node_name": d_name, "inode": [i_inode_page, i_inode_index, 0x80 if self.sb.version >= 0x24 or self.sb.version in [0xe, 0xf] else 0x3c, i_inode]})                

                elif datai[0] == ord("n"):
                    i_nmode = int.from_bytes(datai[1:3], "little")                    
                    tFiles[d_inode].append({"parent_inode": [d_inode_page, d_inode_index, 0x80 if self.sb.version >= 0x24 or self.sb.version in [0xe, 0xf] else 0x3c, d_inode], "node_name": d_name, "data": datai[3:]})

                elif datai[0] == ord("N"):
                    i_nmode, gid, time = struct.unpack("<HHL", datai[1:9])                    
                    tFiles[d_inode].append({"parent_inode": [d_inode_page, d_inode_index, 0x80 if self.sb.version >= 0x24 or self.sb.version in [0xe, 0xf] else 0x3c, d_inode], "node_name": d_name, "data": datai[9:]})

                else:
                    print("Unknown datatype:", chr(datai[0]), datai[1:], d_name)

                db_offset += 2 + sized + sizei          

        return tFiles      
    
    def get_file_node(self, node):
        if "data" in node:
            #print("IS DATA")
            return node["data"]

        elif "inode" in node:
            inode_table = []            

            inode_page, inode_index, inode_size, _ = tuple(node["inode"])                        
            self.file.seek(self.base_offset + (self.ptables[inode_page] * self.sb.page_size) + (inode_index * inode_size))
            #print(hex(self.file.tell()), hex(self.ptables[inode_page]), hex(inode_index))

            inod = (fs_inode_data if self.sb.version >= 0x24 or self.sb.version in [0xe, 0xf] else fs_inode_data_old).parse_stream(self.file)                        

            for cid in inod.direct_cluster_id:                
                if cid >= self.sb.page_total or cid <= 0: break
                inode_table.append(cid)                

            for r, cid in enumerate(inod.indirect_cluster_id):
                if cid >= self.sb.page_total or cid <= 0: continue                

                def recurse_nodes(cid, pRecurse):    
                    #print("BEG")                
                    #print(cid, pRecurse)

                    t = []
                    if pRecurse <= 0:
                        for nC in range(self.sb.page_size // 4):
                            self.file.seek(self.base_offset + (self.ptables[cid] * self.sb.page_size) + (4 * nC))
                            tNode = int.from_bytes(self.file.read(4), "little")
                            if tNode >= self.sb.page_total or tNode <= 0: break

                            #print(f"{self.file.tell() - 4:08x} {tNode - 4:08x}")
                            t.append(tNode)

                    else:                        
                        for nC in range(self.sb.page_size // 4):
                            self.file.seek(self.base_offset + (self.ptables[cid] * self.sb.page_size) + (4 * nC))
                            tNode = int.from_bytes(self.file.read(4), "little")                            
                            if tNode >= self.sb.page_total or tNode <= 0: break
                            
                            #print(f"SUB: {self.file.tell() - 4:08x} {tNode - 4:08x} {pRecurse}")
                            t.extend(recurse_nodes(tNode, pRecurse - 1))

                    #print("END")
                    return t
                                      
                inode_table.extend(recurse_nodes(cid, r))

            #print(inode_table)                    
            return inode_table, inod

    def get_ptable(self, id: int):        
        if self.ptables[id] >= self.sb.page_total:
            return b"\xff" * self.sb.page_size
    
        self.file.seek(self.base_offset + (self.ptables[id] * self.sb.page_size))
        return self.file.read(self.sb.page_size)
    
    def yield_ptable_data(self, id: int=0):        
        for p in self.ptables[id:]:
            if p >= self.sb.page_total:  
                if p != 0xffffffff: print(hex(p), hex(self.sb.page_total))              
                yield b"\xff" * self.sb.page_size
        
            else:                
                self.file.seek(self.base_offset + (p * self.sb.page_size))
                yield self.file.read(self.sb.page_size)

class INodeReader(io.RawIOBase):
    def __init__(self, efs2: EFS2, inode: typing.Union[fs_inode_data, fs_inode_data_old], inode_table: list):
        self.efs2 = efs2
        self.inod = inode
        self.inod_table = inode_table
        self.offset = 0        

    def read(self, count=-1):
        temp = bytearray()

        if self.closed or self.offset >= self.inod.size or count == 0: return b""
        read_count = (self.inod.size - self.offset) if count == -1 else count
        while read_count:            
            self.efs2.file.seek(self.efs2.base_offset + (self.efs2.ptables[self.inod_table[self.offset // self.efs2.sb.page_size]] * self.efs2.sb.page_size))
            t_read_count = min(self.efs2.sb.page_size, read_count)

            temp += self.efs2.file.read(t_read_count)
            self.offset += t_read_count
            read_count -= t_read_count

        return temp
        
    def tell(self):
        return self.offset
    
    def seek(self, offset: int, where: int):
        if where == io.SEEK_SET:
            self.offset = offset

        elif where == io.SEEK_CUR:
            self.offset += offset

        elif where == io.SEEK_END:
            if offset <= 0: raise ValueError("offset in SEEK_END must not be 0")
            self.offset = (self.inod.size) - offset    

    def close(self):
        super().close()
        self.efs2 = None
        self.inod = None
        self.inod_table = None

def _do_efs_shell(s: EFS2):
    global CODING
    import shlex
    import os

    print("EFS2 shell")
    print(f"source file: {sys.argv[1]} @ 0x{s.base_offset:08x}")

    while True:
        cmd = shlex.split(input(f"[{s.pwd}]> "))        

        try:
            if len(cmd) > 0:
                if cmd[0] == "exit":
                    break

                elif cmd[0] == "ls":                    
                    if len(cmd) == 1:
                        for l in s.ls(""):
                            if l not in [".", ".."]: print(l)

                    elif len(cmd) == 2:
                        for l in s.ls(cmd[1]):
                            if l not in [".", ".."]: print(l)

                    else:
                        for k in cmd[1:]:
                            print(f"{k}:")
                            for l in s.ls(k):
                                if l not in [".", ".."]: print(l)

                elif cmd[0] == "cd":
                    if len(cmd) > 2:
                        print(f"{cmd[0]}: too many arguments")

                    elif len(cmd) == 2:
                        s.cd(cmd[1])

                elif cmd[0] == "dump":
                    if len(cmd) != 3:
                        print(f"{cmd[0]}: usage: {cmd[0]} filename destination")

                    elif cmd[1].endswith("*"):
                        def sf_recurse(p, h="", k=""):                            
                            for f in s.ls(h + p):                                
                                if f.endswith("/"):
                                    sf_recurse(f, h + p, p + k)

                                elif f not in [".", ".."]:                                    
                                    t = s.open(h + p + f)
                                    os.makedirs(os.path.split(os.path.join(cmd[2], k, f))[0], exist_ok=True)
                                    open(os.path.join(cmd[2], k, f), "wb").write(t.read())
                            
                        sf_recurse(cmd[1].rstrip("*"))

                    else:
                        t = s.open(cmd[1])
                        os.makedirs(os.path.split(cmd[2])[0], exist_ok=True)
                        open(cmd[2], "wb").write(t.read())

                elif cmd[0] == "pwd":
                    print(s.pwd)

                elif cmd[0] == "encoding":
                    if len(cmd) == 1:
                        print(CODING)

                    elif len(cmd) > 2:
                        print(f"{cmd[0]}: too many arguments")

                    else:
                        CODING = cmd[1]

                elif cmd[0] == "cat":
                    if len(cmd) == 1:
                        print(f"{cmd[0]}: usage: {cmd[0]} files...")

                    else:
                        for f in cmd[1:]:
                            t = s.open(f)
                            sys.stdout.buffer.write(t.read())

                elif cmd[0] in ["hd", "hexdump"]:                    
                    if len(cmd) == 1:
                        print(f"{cmd[0]}: usage: {cmd[0]} files...")

                    else:
                        for f in cmd[1:]:
                            t = s.open(f)
                            hexdump.hexdump(t.read())

                elif cmd[0] == "help":
                    print("ls [files...] (list all files and folders in this directory)")
                    print("cd [dir] (change the working directory)")
                    print("dump [files...] (read files and save)")
                    print("pwd (get the current working directory)")
                    print("encoding [encoding] (set the encoding used to read node filenames)")
                    print("cat files... (read files and output to console)")
                    print("hexdump files... (read files and output in hexdump)")
                    print("hd files... (short for hexdump)")
                    print("help (show this help message)")

                else:
                    print(f"{cmd[0]}: command not found")

        except Exception as e:            
            print(f"{cmd[0]}: {type(e).__name__}: {e}")

if __name__ == "__main__":
    import zipfile
    s = EFS2(open(sys.argv[1], "rb"))

    if len(sys.argv) == 2:
        _do_efs_shell(s)

    else:                    
        if len(sys.argv) > 3:
            CODING = sys.argv[3]

        with zipfile.ZipFile(sys.argv[2], "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:            
            for f in s.ls_recursive("/"):
                print(f)
                try:
                    if f.endswith("/"):
                        zf.open(f.lstrip("/"), "w").write(b"")

                    else:
                        zf.open(f.lstrip("/"), "w").write(s.open(f).read())
                
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"error: {e}")
    