import csv
import tldextract
import os
from dnstwist import *
from postGreyImpl import *
class UnicodeWriter:
	"""
	A CSV writer which will write rows to CSV file "f",
	which is encoded in the given encoding.
	"""
	def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
		# Redirect output to a queue
		self.queue = cStringIO.StringIO()
		self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
		self.stream = f
		self.encoder = codecs.getincrementalencoder(encoding)()		

	def writerow(self, row):
		try:
			self.writer.writerow([unicode(s).encode("utf-8") for s in row])
			# Fetch UTF-8 output from the queue ...
			data = self.queue.getvalue()
			data = data.decode("utf-8")
			# ... and reencode it into the target encoding
			data = self.encoder.encode(data)
			# write to the target stream
			self.stream.write(data)
			# empty queue
			self.queue.truncate(0)
		except:
			pass

	def writerows(self, rows):
		for row in rows:
			self.writerow(row)

 #In  Minute


suffix_list_file = open('suffix_list.txt','r')
suffix_list = suffix_list_file.readlines()
# print suffix_list
# exit()
conn = connectToDatabase();
#exit();
# domain_info_csv = csv.writer(open('domain_info_csv.csv','w'))
# domain_info_csv.writerow(['input_url',''])

def clear_domain(url):
	domain_parts = tldextract.extract(url)
	part_list = [str(domain_parts.domain), str(domain_parts.suffix)];
	return part_list;

def get_alias(domain,ext):
	alias_list = []
	alias_list = main(domain+'.'+ext)
	return alias_list

def get_extension_domain(domain):
	global suffix_list
	extension_domain_list = []
	# if ext=='com':
		# extension_domain_list.append(domain+'.'+ext)
	for suffix in suffix_list:
		extension_domain_list.append(domain+'.'+suffix)
	return extension_domain_list

def get_typo_list(domain,ext):
	final_list = [domain + "." + ext];
	alias = get_alias(domain,ext)
	final_list += alias
	# print 'aalias: ',alias
	# raw_input('')
	for a in alias:
		domain_parts = tldextract.extract(a)
		# print 'domain_parts: ',domain_parts
		final_list+=get_extension_domain(domain_parts.domain)
	return final_list
	# print final_list
	# exit()


def get_domain_info(input_domain, writer,clear_domain_):
	# print '5'
	domain_parts = tldextract.extract(input_domain)
	# print domain_parts
	# raw_input('domain_parts')
	input_domain = domain_parts.domain+'.'+domain_parts.suffix
	if len(domain_parts.subdomain)>0:
		input_domain = domain_parts.subdomain+'.'+domain_parts.domain+'.'+domain_parts.suffix

	# print input_domain
	# raw_input('input_domain')
	input_domain_ip_command = os.popen('dig '+input_domain+' +short')
	input_domain_ip = input_domain_ip_command.read()
	idi_list = input_domain_ip.split('\n')
	idi_list = [l.strip() for l in idi_list if len(l.strip())>0]
	if len(idi_list)>0:
		input_domain_ip = idi_list[0].strip()
	# print 'input_domain_ip: ',input_domain_ip
	# raw_input('')
	# lis = input_domain_ip.split('\n')
	# lis = [l.strip() for l in lis if len(l.strip())>0]
	# print lis
	# raw_input('')

	tld = domain_parts.domain+'.'+domain_parts.suffix
	tld_ip_command = os.popen('dig '+tld+' +short')
	tld_ip = tld_ip_command.read()
	lis = tld_ip.split('\n')
	lis = [l.strip() for l in lis if len(l.strip())>0]
	# print 'tld_ip: ',tld_ip
	# print 'lis: ',lis
	return_list = []
	for tt in lis:
		#print "List " + tt;
		ns_list_cmd = os.popen('dig '+tld+' ns +short')
		ns_list = ns_list_cmd.read().replace("\r", "").replace("\n", ",");
		# print 'ns_list: ',ns_list

		mx_list_cmd = os.popen('dig '+tld+' mx +short')
		mx_list = mx_list_cmd.read();#.replace("\r", " ").replace("\n", " ");
		lines = mx_list.split("\n");
		mx_list = "";
		for line in lines:
			cols = line.split(" ");
			if len(cols) > 1:
				mx_list += cols[1] + ","
			else:
				mx_list += cols[0];
		# print 'mx_list: ',mx_list

		asn_command = os.popen("whois -h asn.shadowserver.org ' origin "+tt + "'")
		asn_info = asn_command.read()
		asn_info_list = asn_info.split('|')
		# print 'asn_info_list: ',asn_info_list

		asn_number = asn_info_list[0].strip()
		ip_range = asn_info_list[1].strip()
		asn_name = asn_info_list[2].strip().replace("\r", " ").replace("\n", " ");
		country = asn_info_list[3].strip()
		isp_domain = asn_info_list[4].strip()
		isp_name = asn_info_list[5].strip()

		# print 'input_domain: ',input_domain
		# print 'input_domain_ip: ',input_domain_ip
		# print 'tld: ',tld
		# print 'tld_ip: ',tt
		# print 'ns_list: ',ns_list
		# print 'mx_list: ',mx_list
		# print 'asn_number: ',asn_number
		# print 'ip_range: ',ip_range
		# print 'asn_name: ',asn_name
		# print 'country: ',country
		# print 'isp_domain: ',isp_domain
		# print 'isp_name: ',isp_name
		# raw_input('')
		# return []
		return_list.append([input_domain, input_domain_ip, tld, tt, ns_list, mx_list, asn_number, ip_range, asn_name, country, isp_domain, isp_name,clear_domain_]);
		# print 'return_list',return_list
	# print type(return_list)
	return return_list
	#writer.writerow([input_domain, input_domain_ip, tld, tld_ip, ns_list, mx_list, asn_number, ip_range, asn_name, country, isp_domain, isp_name]);
	#insertExploitInDb(input_domain, input_domain_ip, tld, tld_ip, ns_list, mx_list, asn_number, ip_range, asn_name, country, isp_domain, isp_name)


def process_domain(domain, writer):
	part_list = clear_domain(domain);
	clear_domain_name = part_list[0];
	ext = part_list[1];
	clear_domain_ = clear_domain_name+'.'+ext
	# print domain,clear_domain_name,ext
	list_of_typo_domains = get_typo_list(clear_domain_name,ext)
	# list_of_typo_domains = ['www.yahoo.com','abc.ttttt.com']
	# print list_of_typo_domains
	# raw_input('')
	# print '2',list_of_typo_domains
	# print list_of_typo_domains;
	# exit();
	#list_of_typo_domains = [domain]
	for dd in list_of_typo_domains:
		try:
			#dd = '4ever-watertite.com';
			print 'processing....',dd,
			
			#clear_domain_ = "sk";
			return_list = get_domain_info(dd, writer,clear_domain_)
			# print 'return_list: ',return_list
			# raw_input('')
			for row in return_list:
				#print '-------------------Inserting Info';
				insertDomainInfo(row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11], row[12])
			print 'Success'; 
		except Exception as e:
			print 'Failed [',e , ']'
			#raise;
			# print '4'
			#failed_domain.write(dd)
			insertFailedDomain(dd, clear_domain_);
		
		# domain_info_csv.writerow(row)


# from ftplib import FTP
# ftp = FTP('ftp://silentroot.com/')
# ftp.login('anu','freelancer')
# exit()

from ftplib import FTP
config_file = open("config.txt", "rb")
config_list  =config_file.readlines()

port=21
ip=config_list[5].split('=')[1].strip()
passftp=config_list[6].split('=')[1].strip()
userftp=config_list[7].split('=')[1].strip()
filename = config_list[8].split('=')[1].strip()
# print ip,passftp,userftp,filename


ftp = FTP(ip)
ftp.login(userftp,passftp)
# print "File List:"
files = ftp.dir()
# print files

ftp.retrbinary("RETR " + filename ,open(filename, 'wb').write)
print 'file downloaded from ftp: ',filename
ftp.quit()
# exit()

# filename = 'dd.txt'
domain_file = open(filename,'r')
domain_list = domain_file.readlines()
# print domain_list
# raw_input('domain_list')
# exit()
writer = csv.writer(open('output.csv', "wb"));
failed_domain = open('failed_domain.txt','wb')
#domain_list = ["4ever-watertite.com" , "4facebuddha.com.my", ".."]
for dd in domain_list:
	try:
		#dd = "4113.com";
		print 'process: ',dd
		process_domain(dd, writer)
		#break;
	except Exception as e:
		#print 'error in progressing......',dd
		#print e
		#raise;
		pass;

