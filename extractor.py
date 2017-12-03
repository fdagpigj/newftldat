import struct
from pathlib import Path










def main():
	with open("ftl.dat", "rb") as pkg:
		outdir = "extractions1"
		nfiles, index_list, names_string = read_package(pkg)
		for i in range(nfiles):
			path = readcstr(names_string, ((index_list[i][1]) & 0x00FFFFFF))
			#print(path)
			extract(pkg, index_list[i], outdir+"/"+path)


def extract(pkg, index_entry, outpath):
	path = Path(outpath)
	path.parent.mkdir(parents=True, exist_ok=True)
	with open(outpath, "w+b") as f:
		#I'm gonna skip the deflating flag as I don't think FTL uses that
		datalen = index_entry[3]
		pkg.seek(index_entry[2])
		readbuf = ""
		pos = 0
		while pos < datalen:
			readbuf = pkg.read(min(datalen - pos, 65536))
			nwritten = f.write(readbuf)
			pos += len(readbuf)


def read_package(pkg):
		b = pkg.read(16)
		_, header_size, entry_size, entry_count, name_size = struct.unpack(">LHHLL", b)
		#print(entry_count, name_size, name_size/entry_count)

		pkg_index_entry_size = 4 * 5
		index_size = entry_count * pkg_index_entry_size

		index_list = []
		for i in range(entry_count):
			b = pkg.read(pkg_index_entry_size)
			index_list.append(struct.unpack(">LLLLL", b))

		names_string = str(pkg.read(name_size), "ascii")

		return entry_count, index_list, names_string


def readcstr(string, start_index):
	index = start_index
	while True:
		if string[index] == "\0":
			break
		index += 1
	return string[start_index:index]


"""def be_to_u32(num):
	b0 = (num & 0x000000ff) << 24
	b1 = (num & 0x0000ff00) << 8
	b2 = (num & 0x00ff0000) >> 8
	b3 = (num & 0xff000000) >> 24
	return b0 | b1 | b2 | b3"""


main()