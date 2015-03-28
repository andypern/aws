import os
import datetime
import boto
from boto import ec2
from boto.ec2 import EC2Connection 
import boto.ec2
import re
from texttable import Texttable

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
user_list = [] 

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
        details['spot_instance_request_id'] = instance.spot_instance_request_id
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
	user_hash[reg]['totaltime'] = 0
	# we have to make sure to omit cn-north-1 and us-gov-west-1
	badRe = re.compile('cn-north-1|us-gov-west-1')
	if not badRe.match(reg):
	
		#instantiate object and connection:
		regconn = Ec2Handler(apikey, apisecret, reg)
		
		#get all instances from region
		reg_inst_list = regconn.fetch_all_instances()
		
	#now we have all instances, get details
		for instance in reg_inst_list:
			myInst = regconn.get_instance_details(instance)
		#only do stuff for running instances that are NOT spot's
			if myInst['state'] == "running" and myInst['spot_instance_request_id'] is None:
			#need try/except in case there is no user tag
				
				try:
					user = myInst['tags']['user']
					if not user in user_list:
					#add the user to the list
						user_list.append(user)
					#for first time users, instantiate an instance hour count
						user_hash[user]['totaltime'] = 0
					#and make an instance_list for each user
				
				#regardless of if user is in the list before, now we
				#need to start shoving stuff into the user_hash
				#create a hash element for this user
					inst_id = myInst['instance_id']
					user_hash[user][inst_id] = myInst
					
				#do date manipulation, but only on running instances
					datestring = user_hash[user][inst_id]['launch_time']
					datestring = datestring[:-1]
					lt_datetime = datetime.datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%S.%f')
					lt_delta = datetime.datetime.utcnow() - lt_datetime
				#stick lt_delta.days into user_hash for instance, also add to user_total and region_total
					
					user_hash[user][inst_id]['runtime'] = lt_delta.days
					user_hash[user]['totaltime'] += lt_delta.days
					user_hash[reg]['totaltime'] += lt_delta.days

					
				except Exception, err:
					print Exception, err
					print "no user tag on %s" % (myInst['instance_id'])

				
#
# now we have what we need , time to print.
#

#lets start by iterating through each user

for user in user_list:

#but we only care if the user's total time is > 7 days
	if user_hash[user]['totaltime'] > 6:
		print "Stats for %s" % (user)
		table = Texttable()
	#need to iterate through each instance..
		for k in  user_hash[user].keys():
			if not k == 'totaltime':
				mydict = user_hash[user][k]
				table.add_rows([['Name', 'Inst_id', 'inst_type', 'launch_time', 'days'], 
					[mydict['tags']['Name'], mydict['instance_id'], mydict['instance_type'],
					mydict['launch_time'], mydict['runtime']]])
				#table width: name = 25, id = 10, type = 10, ltime = 25, days = 4
		table.set_cols_width([25,10,10,25,4])
		print table.draw()
			
		print "total for %s: %s" % (user, user_hash[user]['totaltime'])





