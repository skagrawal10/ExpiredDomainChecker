import psycopg2


def connectToDatabase():
	global conn;
	db = "";
	user = "";
	password = "";
	host = "";
	port = "";
	f = open("mail_config.txt", "rb");
	content = f.read();
	lines = content.split("\n");
	for line in lines:
		if len(line.split("=")) < 2:
			continue;
		param = line.split("=")[0];
		value = line.split("=")[1].replace("\n", "").replace("\r", "").strip();
		if param == "host":
			host = value;
		elif param == "username":
			user = value;
		elif param == "dbpassword":
			password = value;
		elif param == "database":
			db = value;
		elif param == "port":
			port = value;
	try:
		print host;
		print db;
		print user;
		print password;
		print port;
		conn = psycopg2.connect(database=db, password=password, user=user,host="localhost", port=port)
		cur = conn.cursor()
		cur.execute("SET client_encoding = 'UTF8'");
		conn.commit();
		 
		print "Connect to database";
		return conn;
	except:
		raise;
		print "I am unable to connect to the database"	
		return None;
		
def executeQuery(query):
	global conn;
	try:
		cur = conn.cursor()
		cur.execute(query);
		conn.commit()
		print "Records created successfully";
		return True;
	except:
		raise;
		return False;
		
def ifMailExist(Message_ID):
	global conn;
	sql = "SELECT count(*) from mail_extractor where message_id = %s";
	cur = conn.cursor();
	cur.execute(sql, [Message_ID]);
	rows = cur.fetchall()
	count = rows[0][0];
	return int(count);
	
def insertMailInDb(Delivered_To,Received,X_Received,Return_Path,Received_SPF,Authentication_Results,MIME_Version,Received_By,Date,Message_ID,Subject,From_Name,From_Address,From_Domain,To_Name,To_Address,To_Domain,Cc,Cc_Domain,Content_Type,Bcc,Bcc_Domain,In_Reply_To,Boundry,Reply_To,Message_Body,Link_Text,attachment_name,attachment_identifier,attachment_folder):
	global conn;
	sql = "INSERT INTO mail_extractor VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)";
	cur = conn.cursor()
	args = Delivered_To,Received,X_Received,Return_Path,Received_SPF,Authentication_Results,MIME_Version,Received_By,Date,Message_ID,Subject,From_Name,From_Address,From_Domain,To_Name,To_Address,To_Domain,Cc,Cc_Domain,Content_Type,Bcc,Bcc_Domain,In_Reply_To,Boundry,Reply_To,Message_Body,Link_Text,attachment_name,attachment_identifier,attachment_folder;
	cur.execute(sql, [Delivered_To,Received,X_Received,Return_Path,Received_SPF,Authentication_Results,MIME_Version,Received_By,Date,Message_ID,Subject,From_Name,From_Address,From_Domain,To_Name,To_Address,To_Domain,Cc,Cc_Domain,Content_Type,Bcc,Bcc_Domain,In_Reply_To,Boundry,Reply_To,str(Message_Body),str(Link_Text),attachment_name,attachment_identifier,attachment_folder]);
	conn.commit();
	
def insertURLTld(message_id, url, tld):
	global conn;
	sql = "INSERT INTO mail_url_info(message_id, url, tld) values(%s, %s, %s)";
	cur = conn.cursor();
	cur.execute(sql, [message_id, url, tld]);
	conn.commit();


	
def insertExploitInDb(EDB, CVE, OSVDBID, VERIFIED, AUTHOR, PUBLISHED, TYPE, title, platform):
	global conn;
	print TYPE;
	if PUBLISHED == "":
		PUBLISHED = "2015-12-03";
	query = "INSERT INTO EXPLOIT_DETAIL VALUES('" + EDB + "','" + CVE + "','" + OSVDBID + "','" + VERIFIED + "','" + AUTHOR+ "','" + PUBLISHED + "','" + TYPE + "','" + title + "','" + platform + "')";
	#print query;
	executeQuery(query);
	

'''	
conn = connectToDatabase("exploitdb", "postgres", "mathura", "localhost", "5432");
insertExploit(conn, "1", "2", "3", "0", "4", "2015-12-03", "6");
'''