import sys
import imaplib
import getpass
import email
import datetime
import re
from email import parser
from random import randint
import hashlib;
import os
import tldextract
from postGreyImpl import *

conn = connectToDatabase();

def markMailAsDeleted(M):
	print "Mail moving to Trash";
	M.store("1:*",'+X-GM-LABELS', '\\Trash')
	
def emptyTrash(M):
	print "Empty Trash Folder";
	M.select("[Gmail]/Trash")  # select all trash
	M.store("1:*", '+FLAGS', '\\Deleted')  # Flag all Trash as Deleted
	M.expunge();
	
def deleteMarkedMails(M):
	print "Deleting mails";
	M.expunge();
	print "Delete operation is completed";

def downloaAttachmentsInEmail(m, emailid, outputdir):
	print "Processing attachment ....."
	resp, data = m.fetch(emailid, "(BODY.PEEK[])")
	email_body = data[0][1]
	mail = email.message_from_string(email_body)
	folder_name = "1";
	output_path = "";
	if mail.get_content_maintype() != 'multipart':
		return
	folder_name = str(randint(0,10000));
	output_path = outputdir + "/" + folder_name;
	while os.path.exists(output_path):
		folder_name = str(randint(0,10000));
		output_path = outputdir + "/" + folder_name;
	os.mkdir(output_path);
	md5sum = "";
	attachment_info = {};
	for part in mail.walk():
		if part.get_content_maintype() != 'multipart' and part.get('Content-Disposition') is not None:	
			try:
				print "Downloading attachment.....";
				md5sum = hashlib.md5(part.get_payload(decode=True)).hexdigest()
				attachment_info["name"] = part.get_filename();
				attachment_info["identifier"] = md5sum;
				attachment_info["folder"] = folder_name;
				print "Output Dir " + output_path
				open(output_path + '/' + part.get_filename(), 'wb').write(part.get_payload(decode=True))
				return attachment_info;
			except:
				pass;
	return folder_name;
	
def getTLds(url):
	domain_parts = tldextract.extract(url);
	tld = domain_parts.domain+'.'+domain_parts.suffix;
	return tld;
	
def fetchLinksFromEmailBody(body):
	msg2=str(body).replace('=\n','\n').replace('=\r\n','\r\n').replace('=\r','\r').replace('\r\n','').replace('\n','').replace('\r','')
	url_info = [];
	links = re.findall('<a href=3D"(.*?)" target.*?>(.*?)<',msg2);
	if len(links) == 0:
		links = re.findall('<a href=3D"(.*?)">(.*?)<',msg2);
	for link in links:
		try:
			mail_link = link[0].strip().split(" ")[0].replace('"', "");
			#print mail_link;
			if mail_link.startswith("mailto"):
				continue;
			url_info.append(mail_link);
		except:
			pass;
	return url_info;

def process_mailbox(M):
	global deleteMail;
	rv, data = M.search(None, "ALL")
	print data;
	if rv != 'OK':
		print "No messages found!"
		return

	c = 1
	for num in data[0].split():
		print "Processing Mail with ID " + num; 
		rv, data = M.fetch(num, '(RFC822)')
		if rv != 'OK':
			print "ERROR getting message", num
			return
		attachment_info = downloaAttachmentsInEmail(M, num, "E:/mail");
		attachment_name = "";
		attachment_identifier = "";
		attachment_folder = "";
		try:
			attachment_name = attachment_info["name"];
		except:
			pass;
		try:
			attachment_identifier = attachment_info["identifier"];
		except:
			pass;
		try:
			attachment_folder = attachment_info["folder"];
		except:
			pass;			
			
		msg = email.message_from_string(data[0][1])
		parser1 = parser.HeaderParser()
		h = parser1.parsestr(msg.as_string())
		#for key in h.keys():
		#	print key;
		#for key in h.keys():
		#	print key + " " + h[key];
		#print h.keys();
		From_Name = "";
		From_Address = "";
		Delivered_To = "";
		Received = "";
		X_Received = "";
		Return_Path = "";
		Received = "";
		Received_SPF = "";
		Authentication_Results = "";
		Received = "";
		DKIM_Signature = "";
		MIME_Version = "";
		X_Received = "";
		Received = "";
		Received_By = "";
		In_Reply_To = "";
		References = "";
		Date = "";
		Message_ID = "";
		Subject = "";
		From = "";
		From_Name = "";
		From_Address = "";
		From_Domain = "";
		To = "";
		To_Name = "";
		To_Address = "";
		To_Domain = "";
		Cc = "";
		Cc_Domain = "";
		Content_Type = "";
		Bcc = "";
		Bcc_Domain = "";
		In_Reply_To = "";
		Boundry = "";
		Reply_To = "";
		Message_Body = msg;
		Link_Text = "";
		url_info = fetchLinksFromEmailBody(Message_Body);
		try:	
			Message_ID = h["Message-ID"];
		except:
			pass;
		#print "Fetching TLDs";
		if ifMailExist(Message_ID) != 0:
			print "Mail present in database";
			continue;
		print "New Mail Found";
		#exit();
		try:
			In_Reply_To = h["In-Reply-To"];
		except:
			pass;
		try:
			Bcc = h["Bcc"];
		except:
			pass;
		try:
			Delivered_To = h["Delivered-To"]
		except:
			pass;
		try:
			Received = h["Received"];
		except:
			pass;
		try:
			X_Received = h["X-Received"];
		except:
			pass;
		try:
			Return_Path = h["Return-Path"];
		except:
			pass;
		try:
			Received = h["Received"];
		except:
			pass;
		try:
			Received_SPF = h["Received-SPF"];
		except:
			pass;
		try:
			Authentication_Results  = h["Authentication-Results"];
		except:
			pass;
		try:
			Received = h["Received"];
		except:
			pass;
		
		try:
			DKIM_Signature = h["DKIM-Signature"];
		except:
			pass;
		try:	
			MIME_Version = h["MIME-Version"];
		except:
			pass;
		try:
			X_Received = X_Received + "\n" + h["X-Received"];
		except:
			pass;
		try:
			Received =	h["Received"];
		except:
			pass;
		try:
			In_Reply_To = h["In-Reply-To"];
		except:
			pass;
		try:
			References = h["References"];
		except:
			pass;
		try:
			Date = h["Date"];
		except:
			pass;
			
		try:	
			Message_ID = h["Message-ID"];
		except:
			pass;
		try:
			Subject = h["Subject"];
		except:
			pass;
		try:
			From = h["From"];
			
		except:
			pass;
		try:
			From_Name = h["From"].split("<")[0];
			From_Address = h["From"].split("<")[1].replace(">", "");
			From_Domain = From_Address.split("@")[1];
		except:
			pass;
		try:
			To = h["To"];
		except:
			pass;
		try:
			To_Name = h["To"].split("<")[0];
			index = 0;
			if len(h["To"].split("<")) > 1:
				index = 1;
			To_Address = h["To"].split("<")[index].replace(">", "");
			To_Domain = To_Address.split("@")[1];
			
			
		except:
			pass;	
		try:
			Cc = h["Cc"];
			Cc_Domain = Cc.split("@")[1];
		except:
			pass;
		try:
			Bcc = h["Bcc"];
			Bcc_Domain = Bcc.split("@")[1];
		except:
			pass;	
		try:
			Content_Type = h["Content-Type"];
			Boundry = Content_Type.split("boundary=")[1];
		except:
			pass;
		try:
			Received_By = h["Received"];
		except:
			pass;
		try:
			Reply_To = h["Reply To"];
		except:
			pass;
		try:
			Reply_To = h["Reply"];
		except:
			pass;
		if ifMailExist(Message_ID) == 0:
			print "New Mail Found";
			Message_Body = unicode(str(Message_Body), errors='replace')
			udata=Message_Body.decode("utf-8")
			Message_Body=udata.encode("ascii","ignore")
			Subject = unicode(str(Subject), errors='replace')
			Subject = Subject.decode("utf-8")
			Subject=Subject.encode("ascii","ignore")
			insertMailInDb(Delivered_To,Received,X_Received,Return_Path,Received_SPF,Authentication_Results,MIME_Version,Received_By,Date,Message_ID,Subject,From_Name,From_Address,From_Domain,To_Name,To_Address,To_Domain,Cc,Cc_Domain,Content_Type,Bcc,Bcc_Domain,In_Reply_To,Boundry,Reply_To,Message_Body,Link_Text,attachment_name,attachment_identifier,attachment_folder);
			#print Message_Body;
			#print "Fetchin TLDs";
			for url in url_info:
				Link_Text += str(url.replace('target=3D"_blank"', "")) + "\n";
				tld = getTLds(url);
				insertURLTld(Message_ID, url, tld);
		else:
			print "Message already exists";
		#print "From " + From + " " + Message_ID;
	#exit();
	if deleteMail == "Y":
		markMailAsDeleted(M);
		emptyTrash(M);

	
input_email = "";
password = "";
deleteMail = "Y";
input_folders = "";
f = open("mail_config.txt", "rb");
content = f.read();
lines = content.split("\n");
for line in lines:
	if len(line.split("=")) < 2:
		continue;
	param = line.split("=")[0];
	value = line.split("=")[1].replace("\n", "").replace("\r", "").strip();
	if param == "deleteMail":
		deleteMail = value;
	elif param == "Folder":
		input_folders = value;
	elif param == "email":
		input_email = value;
	elif param == "password":
		password = value;
	
	
M = imaplib.IMAP4_SSL('imap.gmail.com')

#M = imaplib.IMAP4_SSL('imap-mail.outlook.com')

try:
	M.login(input_email, password)
	print "Login Successful";
	rv, mailboxes = M.list()
	if rv == 'OK':
		print "Mailboxes:"
		print mailboxes
	folder_arr = input_folders.split(',');
	folder_arr = filter(None, folder_arr) ;
	print folder_arr;
	if len(folder_arr) == 0:
		print "No Folders are provided. Accessing All Mails";
		folder_arr = ["[Gmail]/All Mail"];
	for folder in folder_arr:
		rv, data = M.select(folder)
		print "Processing Folder " + folder;
		process_mailbox(M);
	M.logout()
except imaplib.IMAP4.error:
	raise;
	print "LOGIN FAILED!!! "			
