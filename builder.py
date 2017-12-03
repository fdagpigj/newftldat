import struct
import os



class FileInfo:
	def __init__(self, pathname, index_entry):
		self.pathname = pathname
		self.index_entry = index_entry
		
class IndexEntry:
	def __init__(self, hash_, nameofs_flags, offset, filesize):
		self.hash = hash_
		self.nameofs_flags = nameofs_flags
		self.offset = offset
		# the C program tracks datalen and filesize separately but for us they're always the same
		# since FTL doesn't compress the files
		self.filesize = filesize
		self.__name = None

	def get_name(self, name_buf):
		#this method exists solely for performance reasons because I use a slow af way to read null-terminated strings
		if not self.__name:
			self.__name = readcstr(name_buf, ((self.nameofs_flags) & 0x00FFFFFF)).lower()
		return self.__name

	def get_data(self):
		#returns the contents in the order they need to be written
		# the first filesize is actually datalen, they're just always the same in FTL
		return self.hash, self.nameofs_flags, self.offset, self.filesize, self.filesize




def main():
	#I'll just assume exe_icon.png and every file inside audio, data, fonts and img
	# (all under the current dir) are to be packed
	file_list = read_control_file()
	nfiles = len(file_list)
	index, name_buf, name_size = file_list_to_index(file_list, nfiles)
	write_package("ftl.dat", file_list, index, name_buf, name_size)


def write_package(dest, file_list, index, name_buf, name_size):
	#w+b = truncate and open in binary write mode
	with open(dest, "w+b") as pkg:
		offset = 0
		#4 bytes magic, 2 bytes header size, 2 bytes entry size, 4 bytes entry count, 4 bytes name size
		HEADER_SIZE = 16
		#4 bytes hash, 4 bytes nameofs_flags, 4 bytes offset, 4 bytes datalen, 4 bytes filesize
		INDEX_ENTRY_SIZE = 20
		# ">" means write in big endian - all numbers in the header and index are stored this way
		# "PKG\012" is a magic constant, we need it as a number for packing though
		header = struct.pack(">LHHLL", int(bytes("PKG\012", "ascii").hex(), 16), HEADER_SIZE, INDEX_ENTRY_SIZE, len(file_list), name_size)
		pkg.write(header)
		offset += HEADER_SIZE
		index_offset = offset
		nfiles = len(index)
		# this part exists for whatever mysterious reason in the c program but it clearly is completely pointless
		# since it needs to be overwritten later anyway as we don't know each file's offset yet
		"""for index_entry in index:
			b = struct.pack(">LLLLL", *index_entry.get_data())
			pkg.write(b)"""
		offset += INDEX_ENTRY_SIZE * nfiles
		pkg.seek(offset) #to compensate for the commented-out block
		#after the header and index goes the string of all names
		pkg.write(bytes(name_buf, "ascii"))
		offset += name_size

		#after name_buf goes actual file contents
		for file in file_list:
			#pad with null for alignment (4 is the default alignment, it can be overwritten in the C program but that's not needed for FTL)
			while offset % 4 != 0:
				pkg.write(b"\0")
				offset += 1
			#we finally know the offset of this file so write it to the index
			index[file.index_entry].offset = offset
			with open(file.pathname, "rb") as f:
				filesize = index[file.index_entry].filesize

				#copy the contents up to 65536 bytes at a time
				buf = ""
				copied = 0
				while copied < filesize:
					nread = min(filesize - copied, 65536)
					buf = f.read(nread)
					if nread > 0:
						pkg.write(buf)
					copied += nread
					offset += nread

		#we need to return to "rewrite" the index at this point since we didn't know the offset of each file before
		pkg.seek(index_offset)
		for index_entry in index:
			#pack in big endian mode the contents of each index entry
			b = struct.pack(">LLLLL", *index_entry.get_data())
			pkg.write(b)


def read_control_file():
	#yeah the name of this func is a fake but I couldn't think of a better name
	#for the time being, everything is hardcoded
	file_list = []
	for topdir in ("audio", "data", "fonts", "img"):
		for root, dirs, files in os.walk(topdir):
			for file in files:
				pathname = root+"/"+file
				# the C program actually tracks pathname and realfile separately but they're always the same
				# since FTL doesn't rename the file paths or even if it does, it doesn't require us to
				file_list.append(FileInfo(pathname, -1))
	# I heard someone else doesn't even get this png file out of extracting but I get it so idk what to believe anymore
	# either way it exists at the same level as the 4 "topdir" folders so it has to be handled separately
	# because we don't want to include every file in current dir
	file_list.append(FileInfo("exe_icon.png", -1))
	return file_list


def file_list_to_index(file_list, nfiles):
	# this func creates the "index", a list of IndexEntry:s which contain the information needed
	# to find a file from the package, eg. offset, size, name
	index = []
	#name_buf is a string which contains all filenames as null-terminated strings, name_size is len(name_buf)
	name_buf = ""
	name_size = 0
	for file in file_list:
		pathname = file.pathname
		#size of the file in bytes
		filesize = os.path.getsize(pathname)
		#idk why hashes are so important but they just are
		hash_ = pkg_hash(pathname)
		#flags is always 0 since FTL doesn't compress the files so bitwise OR'ing with it does nothing
		#nameofs_flags = name_size | file.flags
		nameofs_flags = name_size
		#offset will be set later since we apparently don't know them yet
		offset = 0
		index.append(IndexEntry(hash_, nameofs_flags, offset, filesize))
		#append the name and null to the name_buf
		thisnamelen = len(pathname) + 1
		name_size += thisnamelen
		name_buf += pathname + "\0"

	#seemingly arbitrarily sort the files
	pkg_sort(index, name_buf, 0, nfiles-1)

	#now after sorting, find the index entry that corresponds to each file (same hash and lowercased pathname)
	for file in file_list:
		#idk why this needs to be reset
		file.index_entry = -1
		hash_ = pkg_hash(file.pathname)
		for j, index_entry in enumerate(index):
			if index_entry.hash == hash_ and index_entry.get_name(name_buf) == file.pathname.lower():
				file.index_entry = j
				break
		#why am I even tracking this error when I'm basically ignoring all other errors?
		if file.index_entry < 0:
			print("File %s lost from index!"%file.pathname)

	#we could just recalculate name_size but might as well return it
	return index, name_buf, name_size


#these functions are for the sorting
def NAME(index, name_buf, a):
	return index[a].get_name(name_buf)
	#return readcstr(name_buf, ((index[a].nameofs_flags) & 0x00FFFFFF))
def LESS(index, name_buf, pivot_hash, pivot_name, a):
	return (index[a].hash < pivot_hash) or (index[a].hash == pivot_hash and NAME(index, name_buf, a) < pivot_name)
def SWAP(index, a, b):
	index[a], index[b] = index[b], index[a]

def pkg_sort(index, name_buf, left, right):
	# I'm sure there's a less C-like way to write this but I don't really dare to touch it
	# in case the order somehow is important
	if left > right:
		return
	pivot = (left + right + 1) // 2
	pivot_hash = index[pivot].hash
	pivot_name = NAME(index, name_buf, pivot)
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
	# this function is super important
	#I named the variable hash_ because I think hash is a built-in function in python
	hash_ = 0
	for char in pathname:
		#read each byte in the name as a number
		c = bytes(char, "ascii")[0]
		#convert uppercase letters to lowercase
		if 0x41 <= c <= 0x5a:
			c += 0x20
		#bitshifhting and XOR'ing does the actual hashing
		hash_ = hash_<<27 | hash_>>5;
		hash_ ^= c;
		# the hash is stored as a 32-bit unsigned int in the C program but Python's numbers are infinite
		# so after every iteration I need to crop off the bits that would've overflowed in C
		# else they come back and haunt us in the next iteration when bitshifted right and mess everything up
		hash_ &= 0xFFFFFFFF
	return hash_


def readcstr(string, start_i):
	#just a super crude func for reading null-terminated substrings from a bigger string
	i = start_i
	while True:
		if string[i] == "\0":
			break
		i += 1
	return string[start_i:i]


main()