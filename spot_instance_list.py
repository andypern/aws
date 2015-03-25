import re
import boto
import boto.ec2

apikey = 'XXXX'
apisecret = 'XXX'

def get_region_list():
    regions = boto.ec2.get_regions('ec2')
    return [r.name for r in regions]


regionlist = get_region_list()

for reg in regionlist:
	# we have to make sure to omit cn-north-1 and us-gov-west-1
	badRe = re.compile('cn-north-1|us-gov-west-1')
	if not badRe.match(reg):
		spotconn = boto.ec2.connect_to_region(
            region_name=reg,
            aws_access_key_id=apikey,
            aws_secret_access_key=apisecret
        )
		reqs = spotconn.get_all_spot_instance_requests()

		for sir in reqs:
			print "ID: %s Inst_ID: %s Price: %s Type: %s State: %s " % (sir.id, sir.instance_id, sir.price, sir.type, sir.status)



