#!/usr/bin/env python
#
# dnstwist
#
# Generate and resolve domain variations to detect typo squatting,
# phishing and corporate espionage.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'Marcin Ulikowski'
__version__ = '1.02b'
__email__ = 'marcin@ulikowski.pl'

import re
import sys
import socket
import signal
import time
import argparse
import threading
from random import randint
from os import path
import smtplib

try:
	import queue
except ImportError:
	import Queue as queue

try:
	import dns.resolver
	MODULE_DNSPYTHON = True
except ImportError:
	MODULE_DNSPYTHON = False
	pass

try:
	import GeoIP
	MODULE_GEOIP = True
except ImportError:
	MODULE_GEOIP = False
	pass

try:
	import whois
	MODULE_WHOIS = True
except ImportError:
	MODULE_WHOIS = False
	pass

try:
	import ssdeep
	MODULE_SSDEEP = True
except ImportError:
	MODULE_SSDEEP = False

try:
	import requests
	MODULE_REQUESTS = True
except ImportError:
	MODULE_REQUESTS = False
	pass

DIR = path.abspath(path.dirname(sys.argv[0]))
DIR_DB = 'database'
FILE_GEOIP = path.join(DIR, DIR_DB, 'GeoIP.dat')
FILE_TLD = path.join(DIR, DIR_DB, 'effective_tld_names.dat')

DB_GEOIP = path.exists(FILE_GEOIP)
DB_TLD = path.exists(FILE_TLD)

REQUEST_TIMEOUT_DNS = 5
REQUEST_TIMEOUT_HTTP = 5
REQUEST_TIMEOUT_SMTP = 5
THREAD_COUNT_DEFAULT = 10

if sys.platform != 'win32' and sys.stdout.isatty():
	FG_RND = '\x1b[3%dm' % randint(1, 8)
	FG_RED = '\x1b[31m'
	FG_YEL = '\x1b[33m'
	FG_GRE = '\x1b[32m'
	FG_MAG = '\x1b[35m'
	FG_CYA = '\x1b[36m'
	FG_BLU = '\x1b[34m'
	FG_RST = '\x1b[39m'
	ST_BRI = '\x1b[1m'
	ST_RST = '\x1b[0m'
else:
	FG_RND = ''
	FG_RED = ''
	FG_YEL = ''
	FG_GRE = ''
	FG_MAG = ''
	FG_CYA = ''
	FG_BLU = ''
	FG_RST = ''
	ST_BRI = ''
	ST_RST = ''


def p_out(data):
	global args
	if not args.csv:
		sys.stdout.write(data)
		sys.stdout.flush()


def p_err(data):
	global args
	if not args.csv:
		sys.stderr.write(data)
		sys.stderr.flush()


def p_csv(data):
	global args
	if args.csv:
		sys.stdout.write(data)


def bye(code):
	sys.stdout.write(FG_RST + ST_RST)
	sys.exit(code)


def sigint_handler(signal, frame):
	sys.stdout.write('\nStopping threads... ')
	sys.stdout.flush()
	for worker in threads:
		worker.stop()
	time.sleep(1)
	sys.stdout.write('Done\n')
	bye(0)


class UrlParser():

	def __init__(self, url):
		if '://' not in url:
			self.url = 'http://' + url
		else:
			self.url = url
		self.scheme = ''
		self.authority = ''
		self.domain = ''
		self.path = ''
		self.query = ''

		self.__parse()

	def __parse(self):
		re_rfc3986_enhanced = re.compile(
		r'''
		^
		(?:(?P<scheme>[^:/?#\s]+):)?
		(?://(?P<authority>[^/?#\s]*))?
		(?P<path>[^?#\s]*)
		(?:\?(?P<query>[^#\s]*))?
		(?:\#(?P<fragment>[^\s]*))?
		$
		''', re.MULTILINE | re.VERBOSE
		)

		m_uri = re_rfc3986_enhanced.match(self.url)

		if m_uri:
			if m_uri.group('scheme'):
				if m_uri.group('scheme').startswith('http'):
					self.scheme = m_uri.group('scheme')
				else:
					self.scheme = 'http'
			if m_uri.group('authority'):
				self.authority = m_uri.group('authority')
				self.domain = self.authority.split(':')[0].lower()
			if m_uri.group('path'):
				self.path = m_uri.group('path')
			if m_uri.group('query'):
				if len(m_uri.group('query')):
					self.query = '?' + m_uri.group('query')

	def get_full_uri(self):
		return self.scheme + '://' + self.domain + self.path + self.query


class DomainFuzz():

	def __init__(self, domain):
		if not self.__validate_domain(domain):
			raise Exception('Invalid domain name')
		self.domain, self.tld = self.__domain_tld(domain)
		self.domains = []

	def __domain_tld(self, domain):
		domain = domain.rsplit('.', 2)

		if len(domain) == 2:
			return domain[0], domain[1]

		if DB_TLD:
			cc_tld = {}
			re_tld = re.compile('^[a-z]{2,4}\.[a-z]{2}$', re.IGNORECASE)

			for line in open(FILE_TLD):
				line = line[:-1]
				if re_tld.match(line):
					sld, tld = line.split('.')
					if not tld in cc_tld:
						cc_tld[tld] = []
					cc_tld[tld].append(sld)

			sld_tld = cc_tld.get(domain[2])
			if sld_tld:
				if domain[1] in sld_tld:
					return domain[0], domain[1] + '.' + domain[2]

		return domain[0] + '.' + domain[1], domain[2]

	def __validate_domain(self, domain):
		if len(domain) > 255:
			return False
		if domain[-1] == '.':
			domain = domain[:-1]
		allowed = re.compile('\A([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}\Z', re.IGNORECASE)
		return allowed.match(domain)

	def __filter_domains(self):
		seen = set()
		filtered = []

		for d in self.domains:
			if self.__validate_domain(d['domain']) and d['domain'] not in seen:
				seen.add(d['domain'])
				filtered.append(d)

		self.domains = filtered

	def __bitsquatting(self):
		result = []
		masks = [1, 2, 4, 8, 16, 32, 64, 128]
		for i in range(0, len(self.domain)):
			c = self.domain[i]
			for j in range(0, len(masks)):
				b = chr(ord(c) ^ masks[j])
				o = ord(b)
				if (o >= 48 and o <= 57) or (o >= 97 and o <= 122) or o == 45:
					result.append(self.domain[:i] + b + self.domain[i+1:])

		return result

	def __homoglyph(self):
		glyphs = {
		'd': ['b', 'cl', 'dl', 'di'], 'm': ['n', 'nn', 'rn', 'rr'], 'l': ['1', 'i'],
		'o': ['0'], 'k': ['lk', 'ik', 'lc'], 'h': ['lh', 'ih'], 'w': ['vv'],
		'n': ['m', 'r'], 'b': ['d', 'lb', 'ib'], 'i': ['1', 'l'], 'g': ['q'], 'q': ['g']
		}
		result = []

		for ws in range(0, len(self.domain)):
			for i in range(0, (len(self.domain)-ws)+1):
				win = self.domain[i:i+ws]

				j = 0
				while j < ws:
					c = win[j]
					if c in glyphs:
						win_copy = win
						for g in glyphs[c]:
							win = win.replace(c, g)
							result.append(self.domain[:i] + win + self.domain[i+ws:])
							win = win_copy
					j += 1

		return list(set(result))

	def __hyphenation(self):
		result = []

		for i in range(1, len(self.domain)):
			if self.domain[i] not in ['-', '.'] and self.domain[i-1] not in ['-', '.']:
				result.append(self.domain[:i] + '-' + self.domain[i:])

		return result

	def __insertion(self):
		keys = {
		'1': '2q', '2': '3wq1', '3': '4ew2', '4': '5re3', '5': '6tr4', '6': '7yt5', '7': '8uy6', '8': '9iu7', '9': '0oi8', '0': 'po9',
		'q': '12wa', 'w': '3esaq2', 'e': '4rdsw3', 'r': '5tfde4', 't': '6ygfr5', 'y': '7uhgt6', 'u': '8ijhy7', 'i': '9okju8', 'o': '0plki9', 'p': 'lo0',
		'a': 'qwsz', 's': 'edxzaw', 'd': 'rfcxse', 'f': 'tgvcdr', 'g': 'yhbvft', 'h': 'ujnbgy', 'j': 'ikmnhu', 'k': 'olmji', 'l': 'kop',
		'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
		}
		result = []

		for i in range(1, len(self.domain)-1):
			if self.domain[i] in keys:
				for c in range(0, len(keys[self.domain[i]])):
					result.append(self.domain[:i] + keys[self.domain[i]][c] + self.domain[i] + self.domain[i+1:])
					result.append(self.domain[:i] + self.domain[i] + keys[self.domain[i]][c] + self.domain[i+1:])

		return result

	def __omission(self):
		result = []

		for i in range(0, len(self.domain)):
			result.append(self.domain[:i] + self.domain[i+1:])

		n = re.sub(r'(.)\1+', r'\1', self.domain)

		if n not in result and n != self.domain:
			result.append(n) 

		return list(set(result))

	def __repetition(self):
		result = []

		for i in range(0, len(self.domain)):
			if self.domain[i].isalpha():
				result.append(self.domain[:i] + self.domain[i] + self.domain[i] + self.domain[i+1:])

		return list(set(result))

	def __replacement(self):
		keys = {
		'1': '2q', '2': '3wq1', '3': '4ew2', '4': '5re3', '5': '6tr4', '6': '7yt5', '7': '8uy6', '8': '9iu7', '9': '0oi8', '0': 'po9',
		'q': '12wa', 'w': '3esaq2', 'e': '4rdsw3', 'r': '5tfde4', 't': '6ygfr5', 'y': '7uhgt6', 'u': '8ijhy7', 'i': '9okju8', 'o': '0plki9', 'p': 'lo0',
		'a': 'qwsz', 's': 'edxzaw', 'd': 'rfcxse', 'f': 'tgvcdr', 'g': 'yhbvft', 'h': 'ujnbgy', 'j': 'ikmnhu', 'k': 'olmji', 'l': 'kop',
		'z': 'asx', 'x': 'zsdc', 'c': 'xdfv', 'v': 'cfgb', 'b': 'vghn', 'n': 'bhjm', 'm': 'njk'
		}
		result = []

		for i in range(0, len(self.domain)):
			if self.domain[i] in keys:
				for c in range(0, len(keys[self.domain[i]])):
					result.append(self.domain[:i] + keys[self.domain[i]][c] + self.domain[i+1:])

		return result

	def __subdomain(self):
		result = []

		for i in range(1, len(self.domain)):
			if self.domain[i] not in ['-', '.'] and self.domain[i-1] not in ['-', '.']:
				result.append(self.domain[:i] + '.' + self.domain[i:])

		return result

	def __transposition(self):
		result = []

		for i in range(0, len(self.domain)-1):
			if self.domain[i+1] != self.domain[i]:
				result.append(self.domain[:i] + self.domain[i+1] + self.domain[i] + self.domain[i+2:])

		return result

	def generate(self):
		self.domains.append({ 'fuzzer': 'Original*', 'domain': self.domain + '.' + self.tld })

		for domain in self.__bitsquatting():
			self.domains.append({ 'fuzzer': 'Bitsquatting', 'domain': domain + '.' + self.tld })
		for domain in self.__homoglyph():
			self.domains.append({ 'fuzzer': 'Homoglyph', 'domain': domain + '.' + self.tld })
		for domain in self.__hyphenation():
			self.domains.append({ 'fuzzer': 'Hyphenation', 'domain': domain + '.' + self.tld })
		for domain in self.__insertion():
			self.domains.append({ 'fuzzer': 'Insertion', 'domain': domain + '.' + self.tld })
		for domain in self.__omission():
			self.domains.append({ 'fuzzer': 'Omission', 'domain': domain + '.' + self.tld })
		for domain in self.__repetition():
			self.domains.append({ 'fuzzer': 'Repetition', 'domain': domain + '.' + self.tld })
		for domain in self.__replacement():
			self.domains.append({ 'fuzzer': 'Replacement', 'domain': domain + '.' + self.tld })
		for domain in self.__subdomain():
			self.domains.append({ 'fuzzer': 'Subdomain', 'domain': domain + '.' + self.tld })
		for domain in self.__transposition():
			self.domains.append({ 'fuzzer': 'Transposition', 'domain': domain + '.' + self.tld })

		if not self.domain.startswith('www.'):
			self.domains.append({ 'fuzzer': 'Various', 'domain': 'ww' + self.domain + '.' + self.tld })
			self.domains.append({ 'fuzzer': 'Various', 'domain': 'www' + self.domain + '.' + self.tld })
			self.domains.append({ 'fuzzer': 'Various', 'domain': 'www-' + self.domain + '.' + self.tld })
		if '.' in self.tld:
			self.domains.append({ 'fuzzer': 'Various', 'domain': self.domain + '.' + self.tld.split('.')[-1] })
			self.domains.append({ 'fuzzer': 'Various', 'domain': self.domain + self.tld })
		if '.' not in self.tld:
			self.domains.append({ 'fuzzer': 'Various', 'domain': self.domain + self.tld + '.' + self.tld })
		if self.tld != 'com' and '.' not in self.tld:
			self.domains.append({ 'fuzzer': 'Various', 'domain': self.domain + '-' + self.tld + '.com' })

		self.__filter_domains()


class DomainDict(DomainFuzz):

	def __init__(self, domain):
		DomainFuzz.__init__(self, domain)

		self.dictionary = []

	def load_dict(self, file):
		if path.exists(file):
			for word in open(file):
				word = word.strip('\n')
				if word.isalpha() and word not in self.dictionary:
					self.dictionary.append(word)

	def __dictionary(self):
		result = []

		domain = self.domain.rsplit('.', 1)
		if len(domain) > 1:
			prefix = domain[0] + '.'
			name = domain[1]
		else:
			prefix = ''
			name = domain[0]

		for word in self.dictionary:
			result.append(prefix + name + '-' + word)
			result.append(prefix + name + word)
			result.append(prefix + word + '-' + name)
			result.append(prefix + word + name)

		return result

	def generate(self):
		for domain in self.__dictionary():
			self.domains.append({ 'fuzzer': 'Dictionary', 'domain': domain + '.' + self.tld })


class DomainThread(threading.Thread):

	def __init__(self, queue):
		threading.Thread.__init__(self)
		self.jobs = queue
		self.kill_received = False

		self.ssdeep_orig = ''
		self.domain_orig = ''

		self.uri_scheme = 'http'
		self.uri_path = ''
		self.uri_query = ''

		self.option_extdns = False
		self.option_geoip = False
		self.option_whois = False
		self.option_ssdeep = False
		self.option_banners = False
		self.option_mxcheck = False

	def __banner_http(self, ip, vhost):
		try:
			http = socket.socket()
			http.settimeout(1)
			http.connect((ip, 80))
			http.send('HEAD / HTTP/1.1\r\nHost: %s\r\nUser-agent: Mozilla/5.0\r\n\r\n' % str(vhost))
			response = http.recv(1024)
			http.close()
		except Exception:
			pass
		else:
			sep = '\r\n' if '\r\n' in response else '\n'
			headers = response.split(sep)
			for field in headers:
				if field.startswith('Server: '):
					return field[8:]
			banner = headers[0].split(' ')
			if len(banner) > 1:
				return 'HTTP %s' % banner[1]

	def __banner_smtp(self, mx):
		try:
			smtp = socket.socket()
			smtp.settimeout(1)
			smtp.connect((mx, 25))
			response = smtp.recv(1024)
			smtp.close()
		except Exception:
			pass
		else:
			sep = '\r\n' if '\r\n' in response else '\n'
			hello = response.split(sep)[0]
			if hello.startswith('220'):
				return hello[4:].strip()
			return hello[:40]

	def __mxcheck(self, mx, from_domain, to_domain):
		from_addr = 'randombob' + str(randint(1, 9)) + '@' + from_domain
		to_addr = 'randomalice' + str(randint(1, 9)) + '@' + to_domain
		try:
			smtp = smtplib.SMTP(mx, 25, timeout=REQUEST_TIMEOUT_SMTP)
			smtp.sendmail(from_addr, to_addr, 'And that\'s how the cookie crumbles')
			smtp.quit()
		except Exception:
			return False
		else:
			return True

	def stop(self):
		self.kill_received = True

	def run(self):
		while not self.kill_received:
			domain = self.jobs.get()

			if self.option_extdns:
				resolv = dns.resolver.Resolver()
				resolv.lifetime = REQUEST_TIMEOUT_DNS
				resolv.timeout = REQUEST_TIMEOUT_DNS

				try:
					ans = resolv.query(domain['domain'], 'SOA')
					domain['ns'] = str(sorted(ans)[0]).split(' ')[0][:-1].lower()
				except Exception:
					pass

				if 'ns' in domain:
					try:
						ans = resolv.query(domain['domain'], 'A')
						domain['a'] = str(sorted(ans)[0])
					except Exception:
						pass

					try:
						ans = resolv.query(domain['domain'], 'AAAA')
						domain['aaaa'] = str(sorted(ans)[0])
					except Exception:
						pass

					try:
						ans = resolv.query(domain['domain'], 'MX')
						mx = str(sorted(ans)[0].exchange)[:-1].lower()
						if mx: domain['mx'] = mx
					except Exception:
						pass
			else:
				try:
					ip = socket.getaddrinfo(domain['domain'], 80)
				except Exception:
					pass
				else:
					for j in ip:
						if '.' in j[4][0]:
							domain['a'] = j[4][0]
							break
					for j in ip:
						if ':' in j[4][0]:
							domain['aaaa'] = j[4][0]
							break

			if self.option_mxcheck:
				if 'mx' in domain:
					if domain['domain'] is not self.domain_orig: 
						if self.__mxcheck(domain['mx'], self.domain_orig, domain['domain']):
							domain['mx-spy'] = True

			if self.option_whois:
				if 'ns' in domain and 'a' in domain:
					try:
						whoisdb = whois.query(domain['domain'])
						domain['created'] = str(whoisdb.creation_date).replace(' ', 'T')
						domain['updated'] = str(whoisdb.last_updated).replace(' ', 'T')
					except Exception:
						pass

			if self.option_geoip:
				if 'a' in domain:
					gi = GeoIP.open(FILE_GEOIP, GeoIP.GEOIP_INDEX_CACHE | GeoIP.GEOIP_CHECK_CACHE)
					try:
						country = gi.country_name_by_addr(domain['a'])
					except Exception:
						pass
					else:
						if country:
							domain['country'] = country.split(',')[0]

			if self.option_banners:
				if 'a' in domain:
					banner = self.__banner_http(domain['a'], domain['domain'])
					if banner:
						domain['banner-http'] = banner
				if 'mx' in domain:
					banner = self.__banner_smtp(domain['mx'])
					if banner:
						domain['banner-smtp'] = banner

			if self.option_ssdeep:
				if 'a' in domain:
					try:
						req = requests.get(self.uri_scheme + '://' + domain['domain'] + self.uri_path + self.uri_query, timeout=REQUEST_TIMEOUT_HTTP, headers={'User-Agent': 'Mozilla/5.0 (dnstwist)'})
						#ssdeep_fuzz = ssdeep.hash(req.text.replace(' ', '').replace('\n', ''))
						ssdeep_fuzz = ssdeep.hash(req.text)
					except Exception:
						pass
					else:
						if req.status_code / 100 == 2:
							domain['ssdeep'] = ssdeep.compare(self.ssdeep_orig, ssdeep_fuzz)

			self.jobs.task_done()


def main(domain_name):
	
	try:
		dfuzz = DomainFuzz(domain_name)
	except Exception:
		p_err('ERROR: Invalid domain name: %s\n' % url.domain)
		bye(-1)

	dfuzz.generate()
	domains = dfuzz.domains

	
	domain_list = [];
	for domain in domains:
		domain_list.append(domain["domain"]);
	#print domain_list;
	#exit();
	return domain_list;


if __name__ == '__main__':
	#dfuzz = DomainFuzz("www.google.com");
	main("www.google.com")