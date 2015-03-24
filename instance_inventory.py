from pprint import pprint
import boto
from boto import ec2
from boto.ec2 import EC2Connection 
import boto.ec2
import re
import pexpect

#########
#
#
#TODO
# * fix hash so its readable by json parsers
# * get lifecycle type (spot/etc)
# * build more stats (per user, per inst-type, etc)
# * adjust ordering to collect stats before SSH
# * Volume tagging?
#####

api_key = 'XXXX'
api_secret = 'XXXX'


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

#make a big dict

phat_hash = Ddict( dict )
phat_hash['insecure_ssh'] = []
phat_hash['secure_ssh'] = []
phat_hash['user_tag_updates'] = []


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
			inst_user = instance.id + instance.key_name
			phat_hash['user_tag_updates'].append[key_name]
	except KeyError:
	#if we don't find a tag, we make one..and match the key_name
		print instance.id
		if instance.key_name is None:
			print "null key name!"
		else: 
			regconn.create_instance_tags(instance.id, "user", instance.key_name)
			inst_user = instance.id + instance.key_name
			phat_hash['user_tag_updates'].append[instance.key_name]

def check_ssh(instance, ip_address):
	inst_id = instance.id
	#use pexpect to see if password auth is enabled
	ssh_new_key = "Are you sure you want to continue connecting"
	ssh_opts = 'PubkeyAuthentication=no -i ConnectTimeout=2'
	account_name = 'root'
	cmd_connect = "ssh -p22 -o %s %s@%s uname" % (ssh_opts, account_name, ip_address)
	try:
		p = pexpect.spawn(cmd_connect)

		i = p.expect([ssh_new_key, 'asswor'])

		if i == 0:
			p.send('yes\r')
			i = p.expect([ssh_newkey, 'assword:'])

		if i == 1:
			#print "%s -> %s expected password" % (instance, ip_address)
			phat_hash['insecure_ssh'].append(inst_id)

	except Exception, exp:
		phat_hash['secure_ssh'].append(inst_id)





regionlist = get_region_list()




for reg in regionlist:
	# we have to make sure to omit cn-north-1 and us-gov-west-1
	badRe = re.compile('cn-north-1|us-gov-west-1')
	if not badRe.match(reg):
		phat_hash[reg]['inst_count'] = 0
		#instantiate object and connection:
		regconn = Ec2Handler(api_key, api_secret, reg)
		#get all instances from region
		print "fetching %s" % (reg)
		reg_inst_list = regconn.fetch_all_instances()
		#now we have all instances, get details 
		for instance in reg_inst_list:
			phat_hash['raw_inst'][instance] = regconn.get_instance_details(instance)
			phat_hash[reg]['inst_count'] += 1
			#check and fix tags
			check_tags(instance)
			#running inst w/ public IP's => check if SSH is secure
			if (instance.ip_address is not None) and (instance.state == "running"):
				check_ssh(instance, instance.ip_address)
		#print some stats per region
		#print "Region %s had %s tag_updates , %s insecure_ssh, and %s secure_ssh" % (reg, phat_hash[])


print phat_hash


