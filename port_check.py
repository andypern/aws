import socket;
#
#quick example of how to check to see if a port is open
#
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
result = sock.connect_ex(('54.186.129.140',22))
if result == 0:
   print "Port is open"
else:
   print "Port is not open"
sock.close()
