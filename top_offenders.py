import os
import boto
from boto import ec2
from boto.ec2 import EC2Connection 
import boto.ec2
import re
import pexpect

#
#purpose of this script is to find AWS instances which meet the following criteria:
#
# 1) on demand (not spot)
# 2) Launch-time is > 7-days old (eg: instance has been running 24x7 for a long time)
#  
# Things to collect:
# user, hours per inst, hours per user, *maybe* find cost?
#
# in the future, build it to also look for special tags "longrunning = yes"?
#

apikey =  os.environ.get("APIKEY", None)
apisecret = os.environ.get("APISECRET", None)


#
#build a dict class to get some anonymous hash going on
#

class Ddict(dict):
    def __init__(self, default=None):
        self.default = default

    def __getitem__(self, key):
        if not self.has_key(key):
            self[key] = self.default()
        return dict.__getitem__(self, key)

user_hash = Ddict( dict )    

class Ec2Handler(object):
    def __init__(self, apikey, apisecret, region):
        self.region = region
        self.connection = boto.ec2.connect_to_region(
            region_name=self.region,
            aws_access_key_id=apikey,
            aws_secret_access_key=apisecret
        )

    def fetch_all_instances(self):
        reservations = self.connection.get_all_instances()
        instance_list = []
        for r in reservations:
            for i in r.instances:
                instance_list.append(i)
        return instance_list
  
    def get_instance_details(self, instance):
        details = {}
        details['instance_id'] = instance.id
        details['region'] = instance.region.name
        details['zone'] = instance.placement
        details['instance_type'] = instance.instance_type
        details['private_ip_address'] = instance.private_ip_address
        details['ip_address'] = instance.ip_address
        details['ec2_dns'] = instance.dns_name
        details['ec2_private_dns'] = instance.private_dns_name
        details['state'] = instance.state
        details['launch_time'] = instance.launch_time
        details['key_name'] = instance.key_name
        details['tags'] = instance.tags
        details['image_id'] = instance.image_id
        #details = util.convert_none_into_blank_values(details)
        return details
	
    def create_instance_tags(self, instance, tagkey, tagval):
    	tagset = self.connection.create_tags([instance], {tagkey: tagval})
    	print "Instance: %s :  %s tag to %s" % (instance, tagkey, tagval)
  
  	

def get_region_list():
    regions = boto.ec2.get_regions('ec2')
    return [r.name for r in regions]

regionlist = get_region_list()

for reg in regionlist:
	# we have to make sure to omit cn-north-1 and us-gov-west-1
	badRe = re.compile('cn-north-1|us-gov-west-1')
	if not badRe.match(reg):
	
		#instantiate object and connection:
		regconn = Ec2Handler(apikey, apisecret, reg)
		
		#get all instances from region
		print "fetching %s" % (reg)
		reg_inst_list = regconn.fetch_all_instances()
		
		#now we have all instances, get details
		for instance in reg_inst_list:
			myInst = regconn.get_instance_details(instance)
			#build hash for each user?
			






