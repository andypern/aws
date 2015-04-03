import pexpect

#
#quick test to see if ssh allows password auth
#
#host = 'cardinal1'
host = '54.220.67.140'
account_name = 'root'
ssh_new_key = "Are you sure you want to continue connecting"
ssh_opts = 'PubkeyAuthentication=no -i ConnectTimeout=4'

cmd_connect = "ssh -p22 -o %s %s@%s uname" % (ssh_opts, account_name, host)

try:
	p = pexpect.spawn(cmd_connect)

	i = p.expect([ssh_new_key, 'asswor'])

	if i == 0:
		p.send('yes\r')
		i = p.expect([ssh_newkey, 'assword:'])

	if i == 1:
		print "%s expected password" % (host)
except Exception, exp:
	print "password SSH not allowed, or timeout occurred, either way..this host is not accessible from the world"

