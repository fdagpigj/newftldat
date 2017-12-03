import struct
import os



class FileInfo:
	def __init__(self, pathname, flags, index_entry):
		self.pathname = pathname
		self.flags = flags
		self.index_entry = index_entry
		
class IndexEntry:
	def __init__(self, hash_, nameofs_flags, offset, datalen, filesize):
		self.hash = hash_
		self.nameofs_flags = nameofs_flags
		self.offset = offset
		self.datalen = datalen
		self.filesize = filesize
		self.__name = None

	def get_name(self, name_buf):
		if not self.__name:
			self.__name = readcstr(name_buf, ((self.nameofs_flags) & 0x00FFFFFF)).lower()
		return self.__name

	def get_data(self):
		return self.hash, self.nameofs_flags, self.offset, self.datalen, self.filesize




def main():
	#I'll just assume exe_icon.png and every file inside audio, data, fonts and img
	# (all under the current dir) are to be packed
	file_list = read_control_file()
	nfiles = len(file_list)
	index, name_buf, name_size = file_list_to_index(file_list, nfiles)
	write_package("ftl.dat", file_list, index, name_buf, name_size)


def write_package(dest, file_list, index, name_buf, name_size):
	with open(dest, "w+b") as pkg:
		offset = 0
		HEADER_SIZE = 16
		INDEX_ENTRY_SIZE = 20
		header = struct.pack(">LHHLL", int(bytes("PKG\012", "ascii").hex(), 16), HEADER_SIZE, INDEX_ENTRY_SIZE, len(file_list), name_size)
		pkg.write(header)
		offset += HEADER_SIZE
		index_offset = offset
		nfiles = len(index)
		"""for index_entry in index:
			b = struct.pack(">LLLLL", *index_entry.get_data())
			pkg.write(b)"""
		offset += INDEX_ENTRY_SIZE * nfiles
		pkg.seek(offset) #to compensate for the commented-out block
		pkg.write(bytes(name_buf, "ascii"))
		offset += name_size
		for i in range(nfiles):
			while offset % 4 != 0:
				pkg.write(b"\0")
				offset += 1
			index[file_list[i].index_entry].offset = offset
			with open(file_list[i].pathname, "rb") as f:
				filesize = index[file_list[i].index_entry].filesize
				buf = ""
				copied = 0
				while copied < filesize:
					nread = min(filesize - copied, 65536)
					buf = f.read(nread)
					if nread > 0:
						pkg.write(buf)
					copied += nread
					offset += nread
		pkg.seek(index_offset)
		for index_entry in index:
			b = struct.pack(">LLLLL", *index_entry.get_data())
			pkg.write(b)


def read_control_file():
	file_list = []
	#do I even need to track nfiles?
	nfiles = 0
	for topdir in ("audio", "data", "fonts", "img"):
		for root, dirs, files in os.walk(topdir):
			for file in files:
				pathname = root+"/"+file
				flags = 0
				file_list.append(FileInfo(pathname, flags, -1))
				nfiles += 1
	file_list.append(FileInfo("exe_icon.png", 0, nfiles))
	return file_list


def file_list_to_index(file_list, nfiles):
	name_size = 0
	name_buf = ""
	index = []
	for file in file_list:
		pathname = file.pathname
		filesize = os.path.getsize(pathname)
		hash_ = pkg_hash(pathname)
		nameofs_flags = name_size | file.flags
		offset = 0 #will be set later
		datalen = filesize
		index.append(IndexEntry(hash_, nameofs_flags, offset, datalen, filesize))
		thisnamelen = len(pathname) + 1
		name_size += thisnamelen
		name_buf += pathname + "\0"

	pkg_sort(index, name_buf, 0, nfiles-1)
	for file in file_list:
		file.index_entry = -1
		hash_ = pkg_hash(file.pathname)
		for j, index_entry in enumerate(index):
			if index_entry.hash == hash_ and index_entry.get_name(name_buf) == file.pathname.lower():
				file.index_entry = j
				break
		if file.index_entry < 0:
			print("File %s lost from index!"%file.pathname)

	return index, name_buf, name_size


def NAME(index, name_buf, a):
	return index[a].get_name(name_buf)
	#return readcstr(name_buf, ((index[a].nameofs_flags) & 0x00FFFFFF))
def LESS(index, name_buf, pivot_hash, pivot_name, a):
	return (index[a].hash < pivot_hash) or (index[a].hash == pivot_hash and NAME(index, name_buf, a) < pivot_name)
def SWAP(index, a, b):
	index[a], index[b] = index[b], index[a]

def pkg_sort(index, name_buf, left, right):
	if left > right:
		return
	pivot = (left + right + 1) // 2
	pivot_hash = index[pivot].hash
	#def NAME(a):
	#	return readcstr(name_buf, ((index[a].nameofs_flags) & 0x00FFFFFF))
	pivot_name = NAME(index, name_buf, pivot)
	#def LESS(a):
	#	return (index[a].hash < pivot_hash) or (index[a].hash == pivot_hash and NAME(a).lower() < pivot_name.lower())
	#def SWAP(a, b):
	#	index[a], index[b] = index[b], index[a]
	SWAP(index, pivot, right)
	store = left
	while store < right and LESS(index, name_buf, pivot_hash, pivot_name, store):
		store += 1
	for i in range(store + 1, right):
		if LESS(index, name_buf, pivot_hash, pivot_name, i):
			SWAP(index, i, store)
			store += 1
	SWAP(index, right, store)
	if store > 0:
		pkg_sort(index, name_buf, left, store-1)
	pkg_sort(index, name_buf, store+1, right)




def pkg_hash(pathname):
	hash_ = 0
	for char in pathname:
		c = bytes(char, "ascii")[0]
		if 0x41 <= c <= 0x5a:
			c += 0x20
		hash_ = hash_<<27 | hash_>>5;
		hash_ ^= c;
		hash_ &= 0xFFFFFFFF
	return hash_ & 0xFFFFFFFF


def readcstr(string, start_i):
	i = start_i
	while True:
		if string[i] == "\0":
			break
		i += 1
	return string[start_i:i]


main()