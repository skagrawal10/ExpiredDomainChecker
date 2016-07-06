import poplib
import re;
from email import parser

def getPopupserver(email):
	if "@gmail" in email:
		print "Gmail Detected";
		return "pop.gmail.com";
	elif "@yahoo" in email:
		print "Yahoo Detected";
		return "pop.mail.yahoo.com";
	elif "@hotmail" in email or "@live" in email:
		print "Hotmail Detected";
		return "pop3.live.com";

def yahoo_login(email,pwd):
	pop_server = getPopupserver(email);
	#print 'enter' + " Username " + email + " Password " + pwd + " " + pop_server;
	pop_conn = poplib.POP3_SSL(pop_server);
	#pop_conn.set_debuglevel(2)
	user_email = email;
	pop_conn.user(user_email)
	pop_conn.pass_(pwd)
	link = ""
	#print 'enter 1' + " Username " + email + " Password " + pwd + " " + pop_server;
	#Get messages from server:
	#messages = [pop_conn.retr(i) for i in range(1, len(pop_conn.list()[1]) + 1)]
	messages = [pop_conn.retr(i) for i in range(1, len(pop_conn.list()[1]) + 1)]
	#headers = parser.Parser().parsestr(messages[0].as_string())
	#for h in headers.items():
	#	print h
	#exit();
	#print messages
	# Concat message pieces:
	messages = ["\n".join(mssg[1]) for mssg in messages]
	#Parse message intom an email object:
	messages = [parser.Parser().parsestr(mssg) for mssg in messages]
	for message in messages:
		sender = message['from'];
		print sender;
		#if sender == "CNET Membership <membership@noreply.cnet.com>":
		parser1 = parser.HeaderParser()
		h = parser1.parsestr(message.as_string())
		for key in h.keys():
			print "Key " + key ;#+ " " + h[key];
		#print h.keys()
		#break;
		sender = message['from'];
		# msg = message['message'];
		#print "Message";
		#print message;
		#break;
		if sender == "CNET Membership <membership@noreply.cnet.com>":
			msg2=str(message).replace('=\n','\n').replace('=\r\n','\r\n').replace('=\r','\r').replace('\r\n','').replace('\n','').replace('\r','')
			# print "Mesage 2 " + msg2;
			link = re.findall('Hi '+user_email.replace('.','\.')+'.*?To complete your Download\.com registration\, please click here.*?<a href=3D"(.*?)" title',msg2)[0]
			print 'link: ',link
			break;
		#print message['subject']
		#print message['sender']
		#print message
	    #break
	pop_conn.quit()
	return link

	 
yahoo_login('testpythonheader@gmail.com','hackgoogle')