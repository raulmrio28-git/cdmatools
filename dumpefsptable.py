import dumpefs
import sys

if __name__ == "__main__":
    inp = dumpefs.EFS2(open(sys.argv[1], "rb"), parse_nodes=False, super=int(sys.argv[3]))
    out = open(sys.argv[2], "wb")
            
    for q, p in enumerate(inp.yield_ptable_data()):
        assert len(p) == inp.sb.page_size, f"{q}: {hex(len(p))} {hex(inp.sb.page_size)}"
        out.write(p)