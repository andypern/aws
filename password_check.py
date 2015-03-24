import pexpect

ssh_new_key = "Are you sure you want to continue connecting"

cmd_connect = "ssh -p22 %s@%s" % (account_name, host)

try:

    p = pexpect.spawn(cmd_connect)

    i = p.expect([ssh_new_key, 'asswor'])

    if i == 0:
        p.send('yes\r')
        i = p.expect([ssh_newkey, 'assword:'])

    if i == 1:
        p.send(account_pwd)

except Exception, exp:  
    print = "Could not connect to %s with account %s" % (host, account_name)
