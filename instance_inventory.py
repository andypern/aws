from pprint import pprint
import boto
from boto import ec2
from boto.ec2 import EC2Connection 
import boto.ec2
import re


api_key = 'XXXXXXX'
api_secret = 'XXXXXXX'



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
        #details = util.convert_none_into_blank_values(details)
        return details
	
    def create_instance_tags(self, instance, tagkey, tagval):
    	tagset = self.connection.create_tags([instance], {tagkey: tagval})
  

def get_region_list():
    regions = boto.ec2.get_regions('ec2')
    return [r.name for r in regions]

def check_tags(instance):
#look at instance tags, make sure there is a 'user' tag
# and that it matches the key_name
	try:
		user = instance.tags['user']
		key_name = instance.key_name
	#check to make sure it matches the key_name
		if not user == key_name:
			#print "%s tag nomatch %s key" % (instance.tags['user'], instance.key_name)
			regconn.create_instance_tags(instance, "user", key_name)	
	except KeyError:
	#if we don't find a tag, we make one..and match the key_name
		#print "no tag for %s" % (instance.key_name)
		print instance.id
		regconn.create_instance_tags(instance.id, "user", instance.key_name)

regionlist = get_region_list()
print regionlist



for reg in regionlist:
	# we have to make sure to omit cn-north-1 and us-gov-west-1
	badRe = re.compile('cn-north-1|us-gov-west-1')
	if not badRe.match(reg):
		#instantiate object and connection:
		regconn = Ec2Handler(api_key, api_secret, reg)
		#get all instances from region
		print "fetching %s" % (reg)
		reg_inst_list = regconn.fetch_all_instances()
		#now we have all instances, get details 
		for instance in reg_inst_list:
			myInstDetails = regconn.get_instance_details(instance)
			#check and fix tags
			check_tags(instance)
			
			#print myInstDetails


