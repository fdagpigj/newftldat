import struct
from pathlib import Path



class IndexEntry:
	def __init__(self, hash_, nameofs_flags, offset, datalen, filesize):
		self.hash = hash_
		self.nameofs_flags = nameofs_flags
		self.offset = offset
		# the C program tracks datalen and filesize separately but for us they're always the same
		# since FTL doesn't compress the files
		self.filesize = filesize




def main():
	with open("ftl.dat", "rb") as pkg:
		#for the time being, everything is hardcoded
		outdir = "extractions1"
		nfiles, index_list, names_string = read_package(pkg)
		for i in range(nfiles):
			# the bitwise anding is just to filter out the flags (flags and name position share a 4-byte number)
			# but flags are always 0 for FTL anyway so that is not necessary
			#name_start = ((index_list[i].nameofs_flags) & 0x00FFFFFF)
			name_start = index_list[i].nameofs_flags
			path = readcstr(names_string, name_start)
			#print(path)
			extract(pkg, index_list[i], outdir+"/"+path)


def extract(pkg, index_entry, outpath):
	#create any necessary directories
	path = Path(outpath)
	path.parent.mkdir(parents=True, exist_ok=True)
	#truncate (or create if doesn't exist) and open for writing in binary mode
	with open(outpath, "w+b") as f:
		#we don't even check for deflating flag as FTL doesn't use that
		#copy the contents in blocks of up to 65536 bytes
		datalen = index_entry.filesize
		pkg.seek(index_entry.offset)
		readbuf = ""
		pos = 0
		while pos < datalen:
			readbuf = pkg.read(min(datalen - pos, 65536))
			nwritten = f.write(readbuf)
			pos += len(readbuf)


def read_package(pkg):
	header_size = 16
	header = pkg.read(header_size)
	magic, header_size, entry_size, entry_count, name_size = struct.unpack(">LHHLL", header)
	assert magic == int(b"PKG\012".hex(), 16)
	assert header_size == 16
	assert entry_size == 20

	index_size = entry_count * entry_size

	index_list = []
	for i in range(entry_count):
		b = pkg.read(entry_size)
		#5 big endian 32-bit ints
		data = struct.unpack(">LLLLL", b)
		index_list.append(IndexEntry(*data))

	names_string = str(pkg.read(name_size), "ascii")

	return entry_count, index_list, names_string


def readcstr(string, start_index):
	index = start_index
	while True:
		if string[index] == "\0":
			break
		index += 1
	return string[start_index:index]


#this would be one way to convert a number to big endian and back if there wasn't a convenient way to do it
"""def be_to_u32(num):
	b0 = (num & 0x000000ff) << 24
	b1 = (num & 0x0000ff00) << 8
	b2 = (num & 0x00ff0000) >> 8
	b3 = (num & 0xff000000) >> 24
	return b0 | b1 | b2 | b3"""


main()