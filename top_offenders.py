import os
import datetime
import boto
from boto import ec2
from boto.ec2 import EC2Connection 
import boto.ec2
import re
from texttable import Texttable

import requests
import json

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
					# also a per-user cost
						user_hash[user]['totalcost'] = 0

					#also, set their 'offender flag' to false
						user_hash[user]['offender'] = False

				
				#regardless of if user is in the list before, now we
				#need to start shoving stuff into the user_hash
				#create a hash element for this user
					inst_id = myInst['instance_id']
					user_hash[user][inst_id] = myInst

				
				###########
				#Pricing stuff
				# new: grab pricing info, if we don't already have it for this reg+inst
				# note: for now, we are assuming os=linux
				#	
				#to start with, check to see if we already have this inst-type
				# price for this region

				
					instType = user_hash[user][inst_id]['instance_type']
					

					try:
						# if we have done this already for this inst-type and region, skip
						# maybe in the future we'd increment the reg/inst-type count.
						#
						regInst = user_hash[reg][instType]
					except:
						#this means we havent done this one yet...


						#first we need to build our request string.
						priceRequestString = 'http://info.awsstream.com/instances.json?region=' + \
						str(reg) + '&model=' + str(instType) + \
						'&pricing=od&os=linux' \

						#perform the request, and get json object, note that we only want the first record
						
						#print priceRequestString

						priceResponse = requests.get(priceRequestString).json()[0]
						#print priceResponse

						#for now , we just care about the hourly price
						user_hash[reg][instType] = priceResponse['hourly']

						#print "found %s" % (user_hash[reg][instType])

				###########################
				#End pricing stuff
				#

				#do date manipulation, but only on running instances
					datestring = user_hash[user][inst_id]['launch_time']
					datestring = datestring[:-1]
					lt_datetime = datetime.datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%S.%f')
					lt_delta = datetime.datetime.utcnow() - lt_datetime
				#stick lt_delta.days into user_hash for instance, also add to user_total and region_total
					

					#store total_seconds, we can do math after that
					user_hash[user][inst_id]['seconds'] = lt_delta.total_seconds()
					#store days too, cuz its easy
					user_hash[user][inst_id]['days'] = lt_delta.days
					user_hash[user]['totaltime'] += lt_delta.total_seconds()
					user_hash[reg]['totaltime'] += lt_delta.total_seconds()

					########
					#cost section
					#
					#
					#now lets figure out how much this instance has cost since launch time

					user_hash[user][inst_id]['cost'] = round(user_hash[reg][instType] * (
						lt_delta.total_seconds() / 3600), 2)

					#and add it to the user's total cost

					user_hash[user]['totalcost'] += user_hash[user][inst_id]['cost']


					#flag the user if any of their instances is > 7days.
					if user_hash[user][inst_id]['days'] > 6:
						user_hash[user]['offender'] = True

				except Exception, err:
					print Exception, err
					print "no user tag on %s" % (myInst['instance_id'])

				
#
# now we have what we need , time to print.
#

#lets start by iterating through each user

for user in user_list:

#we'll only print out flagged users
	if user_hash[user]['offender']  is True:
		print "Stats for %s" % (user)
		table = Texttable()
	#need to iterate through each instance..
		for k in  user_hash[user].keys():
			if not k == 'totaltime' and not k == 'totalcost' and not k == 'offender':
				mydict = user_hash[user][k]
				totaldays = user_hash[user]['totaltime'] / 86400
				#note; right now we're printing out all instances
				#for each user that is an 'offender', but perhaps we should
				# only print out instances which meet the offending threshold.
				table.add_rows([['Name', 'Inst_id', 'inst_type', 'launch_time', 'days', 'cost'], 
					[mydict['tags']['Name'], mydict['instance_id'], mydict['instance_type'],
					mydict['launch_time'], mydict['days'], mydict['cost']]])
		#table width: name = 25, id = 10, type = 10, ltime = 25, days = 4, cost = 8
		table.set_cols_width([25,10,10,25,4, 8])
		print table.draw()

		print "total for %s: %s days, %s dollars" % (user, totaldays,
			user_hash[user]['totalcost'])





