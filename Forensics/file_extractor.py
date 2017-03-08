#!/usr/bin/python
# (1) A folder containing all of the recovered files
# (2) A single SQLite database with the filename, md5, and all metadata for each file
# (3) A single report containing the same information as the database (any format). The report should be in a human readable format.
# 
#
#
#

import sys
import os
import hashlib
import sqlite3

try:
	import pytsk3
except ImportError:
	print 'Pytsk3 module not installed. Run the following commands:'
	print 'git clone https://github.com/py4n6/pytsk.git'
	print 'cd pytsk'
	print 'apt-get install autotools-dev automake libtool'
	print 'python setup.py update'
	print 'python setup.py build'
	print 'python setup.py install'
	sys.exit(0)

try:
	import magic
except ImportError:
	print 'Magic module not installed. Run the following command:'
	print 'pip install python-magic'
	sys.exit(0)

try:
	import argparse
except ImportError:
	print 'ArgParse module not installed. Run the following command:'
	print 'pip install argparse'
	sys.exit(0)

try:
	from prettytable import PrettyTable
except ImportError:
	print 'PrettyTable module not installed. Run the following command:'
	print 'pip install prettytable'
	sys.exit(0)

class DB(object):
	def __init__(self):
		# Report File Initialization
		self.report_output = 'ajk665_report.txt'
		if os.path.exists(self.report_output):
				os.remove(self.report_output)

		# Database Initialization:
		self.sqlite_file = 'ajk665_file_system_database.sqlite'   

		if os.path.exists(self.sqlite_file):
			os.remove(self.sqlite_file)

		# Create a database
		self.image_table_name = 'image_data'
		self.file_table_name = 'file_data'

		# Connecting to the database file
		self.database_connection = sqlite3.connect(self.sqlite_file)
		self.cursor = self.database_connection.cursor()

		# Creating image table
		self.cursor.execute('CREATE TABLE {tn} (id integer primary key AUTOINCREMENT, image_name varchar(512))'.format(tn=self.image_table_name))

		# Creating file table
		self.cursor.execute('CREATE TABLE {tn} (id integer primary key AUTOINCREMENT, filename varchar(512), image integer, extension varchar(128), mimetype varchar(128), md5 varchar(128), size integer, creation_time integer, modification_time integer, FOREIGN KEY(image) REFERENCES {fn}(id))'.format(tn=self.file_table_name, fn=self.image_table_name))
	
		self.database_connection.commit()

	def __del__(self):
		self.database_connection.close()

	# Return database connection
	def database_connect(self):
		return self.database_connection

	# Print database for debugging
	def print_database(self):
		self.cursor.execute('SELECT * FROM {tn}'.format(tn=self.file_table_name))
		all_rows = self.cursor.fetchall()
		print all_rows
		return

	# Export database for report
	def export_database(self, report_output=None):

		if not report_output:
			report_output = self.report_output

		print "[+] Exporting database to " + self.sqlite_file
		print "[+] Exporting report to " + report_output
		report = open(report_output, 'w')

		# To-do - print summary 

		# Print Images table
		self.cursor.execute('SELECT * FROM {image_table}'.format(image_table=self.image_table_name))

		col_names = [cn[0] for cn in self.cursor.description]
		rows = self.cursor.fetchall()

		file_table = PrettyTable()
		file_table.padding_width = 1
		for x in xrange(0, len(col_names)):
			file_table.add_column(col_names[x],[row[x] for row in rows])

		print(file_table)
		tabstring1 = file_table.get_string()

		report.write(tabstring1.encode('utf-8'))
		report.write('\n')

		# Print Files Table
		self.cursor.execute('SELECT {file_table}.id, {file_table}.filename, {image_table}.image_name, {file_table}.mimetype, {file_table}.md5, {file_table}.size, {file_table}.creation_time, {file_table}.modification_time  FROM {file_table} LEFT OUTER JOIN {image_table} ON {file_table}.image = {image_table}.id'.format(file_table=self.file_table_name, image_table=self.image_table_name))

		col_names = [cn[0] for cn in self.cursor.description]
		rows = self.cursor.fetchall()

		file_table = PrettyTable()
		file_table.padding_width = 1
		for x in xrange(0, len(col_names)):
			file_table.add_column(col_names[x],[row[x] for row in rows])

		print(file_table)
		tabstring2 = file_table.get_string()

		report.write(tabstring2.encode('utf-8'))
		report.write('\n')

		report.close()
		return


class Fls(object):

	FILE_MIMETYPES_TO_EXTRACT = [
		'application/pdf',
		'image/png',
		'image/jpeg',
		'image/gif',
		'image/bmp',
		'image/svg+xml',
		'image/x-ms-bmp'
	]
	FILE_MIMETYPES_DICTIONARY = {
		'application/pdf' : '.pdf',
		'image/png' : '.png',
		'image/jpeg' : '.jpg',
		'image/gif' : '.gif',
		'image/bmp' : '.bmp',
		'image/svg+xml' : '.svg',
		'image/x-ms-bmp': '.bmp'
	}

	def __init__(self, image_file, count):
		self._fs_info = None
		self._img_info = None
		self._long_listing = False
		self._output_folder = 'OUT/'

		self.database_connection = None
		self.cursor = None
		self.image_table_name = 'image_data'  
		self.file_table_name = 'file_data'
		
		self.image_file = image_file
		self.image_count = count

	# Get connection details from DB() class
	def connect_database(self, connection):
		self.database_connection = connection
		self.cursor = connection.cursor()

	# Parse options from command line and setup background variables
	def parse_options(self, options):

		if getattr(options, "output", False):
			output_folder = getattr(options, "output", False)

			# Checking for trailing '/'
			if output_folder[len(output_folder) - 1] != '/':
				output_folder = output_folder + '/'

			self._output_folder = output_folder

		# Create output folder if not exists
		if not os.path.exists(self._output_folder):
			os.makedirs(self._output_folder)

	# Open a fileimage
	def open_image(self):
		self._img_info = pytsk3.Img_Info(self.image_file)
		self._fs_info = pytsk3.FS_Info(self._img_info, offset=0)

		try:
			#print 'INSERT INTO {tn} (filename, image, mimetype) VALUES ("a", {im}, {mt})'.format(tn=self.file_table_name, im=image, mt=str(mimetype))
			self.cursor.execute('INSERT INTO {tn} (image_name) VALUES ("{image_name}")'.format(tn=self.image_table_name, image_name=self.image_file))
		except Exception as e:
			print "Reached here"
			print e.message

		return self._fs_info.open_dir(path='/')

	# Go through the filesystem recursively
	def parse_directory(self, directory, stack=None):
		
		stack.append(directory.info.fs_file.meta.addr)

		for directory_entry in directory:
			if (not hasattr(directory_entry, "info") or not hasattr(directory_entry.info, "name") or not hasattr(directory_entry.info.name, "name") or directory_entry.info.name.name in [".", ".."]) or not hasattr(directory_entry.info.meta, 'type'):
				continue

			extenstion_type = False
			if directory_entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG and directory_entry.info.meta.size != 0:
				fileData = directory_entry.read_random(0, 256)
				extenstion_type = magic.from_buffer(fileData, mime=True)
				if extenstion_type in self.FILE_MIMETYPES_TO_EXTRACT:
					file_hash = self.extract_file(directory_entry, extenstion_type)
					self.add_database_entry(directory_entry, extenstion_type, file_hash)

			try:
				sub_directory = directory_entry.as_directory()
				inode = directory_entry.info.meta.addr

				if inode not in stack:
					self.parse_directory(sub_directory, stack)

			except IOError:
				pass

		stack.pop(-1)

	# Extract file and save to output directory 
	def extract_file(self, directory_entry, extenstion_type):
		try:
			fileData = directory_entry.read_random(0, directory_entry.info.meta.size)

			fileHash = hashlib.md5(fileData).hexdigest()

			extractFile = open(self._output_folder + directory_entry.info.name.name + self.FILE_MIMETYPES_DICTIONARY[extenstion_type],'w')
			extractFile.write(fileData)
			extractFile.close()
			print "[+] Extracted " + directory_entry.info.name.name + " to " + self._output_folder + directory_entry.info.name.name

		except Exception as e:
			print '[-]' + e.message
			print '[-] ' + directory_entry.info.name.name + " Could not be extracted."
			return None
		return fileHash

	# Add the fileentry to the database
	def add_database_entry(self, directory_entry, mimetype, file_hash):
		try:
			self.cursor.execute('INSERT INTO {tn} (filename, image, mimetype, md5, size, creation_time, modification_time) VALUES ("{fn}", {im}, "{mt}", "{md}", {size}, {crtime}, {mdtime})'.format(tn=self.file_table_name, fn=directory_entry.info.name.name + self.FILE_MIMETYPES_DICTIONARY[mimetype], im=self.image_count, mt=mimetype, md=file_hash, size=directory_entry.info.meta.size, crtime=directory_entry.info.meta.crtime, mdtime=directory_entry.info.meta.mtime))
		except Exception as e:
			print '[-]' + e.message
			print '[-] ' + directory_entry.info.name.name + " failed to be added to the database."
		self.database_connection.commit()
		return

def main():

	args_parser = argparse.ArgumentParser(description=("Extracts PDFs and Image files in a disk image."))

	args_parser.add_argument("images", nargs="+", metavar="IMAGE", action="store", type=str, default=None, help=("Storage media images or devices."))

	args_parser.add_argument("-o", dest="output", metavar="OUTPUT_FOLDER", action="store", type=str, default=None, help="Path to output directory")

	args_parser.add_argument("-r", dest="report", metavar="REPORT_FILE", action="store", type=str, default=None, help="Report output file")

	options = args_parser.parse_args()

	if not options.images:
		print 'No file image(s) provided.'
		args_parser.print_help()
		print '' 
		return False

	database = DB()
	database_connection = database.database_connect()

	for count, image_file in enumerate(options.images):
		print '[*] Extracting from image: ' + image_file

		fls = Fls(image_file, count + 1)

		fls.connect_database(database_connection)

		fls.parse_options(options)

		directory = fls.open_image()

		fls.parse_directory(directory, [])

	database.export_database(options.report)

	return True


if __name__ == '__main__':
	if not main():
		sys.exit(1)
	else:
		sys.exit(0)
