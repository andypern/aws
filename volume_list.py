import os
import sys
import re
import boto
import getopt
import boto.ec2
import datetime
from dateutil import parser


apikey =  os.environ.get("APIKEY", None)
apisecret = os.environ.get("APISECRET", None)


#####
#TODO
# * find unattached volumes, find date, delete if >30d && unatt'd (and log it)
# * put more things into functions
# * start associating cost with the unattached (so we know if its even worth notifying..)


#get opts

notify = 0

try:
        opts, args = getopt.getopt(sys.argv[1:], "n", ["notify"])
except getopt.GetoptError as err:
        # print help information and exit:
        print(err) # will print something like "option -a not recognized"
        print "wrong option"
        sys.exit(2)

for opt, arg in opts:
    if opt in ('-n', '--notify'):
        notify = 1
    else:
        notify = 0


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
        details['instance_type'] = instance.instance_type
        details['state'] = instance.state
        details['launch_time'] = instance.launch_time
        details['key_name'] = instance.key_name
        details['tags'] = instance.tags
        details['image_id'] = instance.image_id
        #details = util.convert_none_into_blank_values(details)
        return details
    
    def get_all_volumes(self):
      volumes = self.connection.get_all_volumes()
      return volumes

    def get_all_instances(self, myfilter):
      instances = self.connection.get_all_instances(filters=myfilter)
      return instances

    def get_instance_attribute(self, instance, myattribute):
        attr = self.connection.get_instance_attribute(
            instance_id=instance,
            attribute=myattribute)
        return attr


##end class

#
#more functions
#

def get_region_list():
    regions = boto.ec2.get_regions('ec2')
    return [r.name for r in regions]


def unattachedvolumes(vol):
    try:
        print "%s was unattached : owned by %s create_time: %s " % (vol, vol.tags['user'], vol.create_time)
    except KeyError:
        print "%s was unattached, no owner create_time: %s" % (vol, vol.create_time)

        



def check_dot(instance,vol):
        #
        #this block is an example of how to go from instance -> blockdevicemapping -> volume_id
        # we'll use it for volumes that don't have the 'dot=true|false' tag set.

    #get inst_attributes
    myattribute='blockDeviceMapping'
    inst_attributes = regconn.get_instance_attribute(
    instance.id,
    myattribute)
    inst_device_list =  inst_attributes['blockDeviceMapping'].values()
    for device in inst_device_list:
    #Most of the time there will be more than one device per instance
    # remember that this function was called from within a vol loop, so it will run 
    # once per volume..not once per instance.  So, we can either just do all
    # volumes related to this instance *now*, OR just do the volume from which this function
    # was called, by checking the device.volume_id == vol.id.  We'll go w/ the latter
    # since the alternative would require fetching the volume object by doing a lookup on the ID
        if device.volume_id == vol.id:
            vol.add_tag('dot', device.delete_on_termination)
            print "set %s on vol %s" % (device.delete_on_termination, vol.id)
            #
            #note: once this is done..it never needs to be done again for the
            #volume
            #

    #so, go check each volume to see if its tags line up? seems pricey..





##end functions

#get the current time, we'll use it later
nowtime = datetime.datetime.utcnow()
regionlist = get_region_list()

    
for region in regionlist:
    # we have to make sure to omit cn-north-1 and us-gov-west-1
    badRe = re.compile('cn-north-1|us-gov-west-1')
    if not badRe.match(region):
        print "working on %s" % (region)
        regconn = Ec2Handler(apikey, apisecret, region)
        
        #get all volumes
        vols = regconn.get_all_volumes()
        for vol in vols:
            #print dir(vol)

            if vol.attach_data.instance_id is None:
                unattachedvolumes(vol)
            else:
                volInst = vol.attach_data.instance_id
                #
                #if its attached, we'll want to first determine if it has any 'user' tags
                # also check to see if it has a dot tag (which means we've checked dot status)
                #
                try:
                    user = vol.tags['user']
                    dot = vol.tags['dot']

                    #this means there was a user key and a dot key. Likely *WE* set it
                    #but at some point we'll need to make sure they match the tag on the instance
                    #print "%s had user tag %s" % (vol, user)
                except KeyError:
                    #this means there was no user tag OR no dot tag. now we have to set one.
                    # we could do something like pull all the inst details into
                    # a dictionary, then systematically go through and check each 
                    # entry and see if it matched what we have in our volume list
                    #. that would save a bunch of API calls (one per volume).  Perhaps later..
                    #for now, lets try going after: 
                    # volInst => inst => inst.tags.user , then setting vol.tags.user=inst.tags.user
                    # this is at least one api call per instance (perhaps one per volume), plus another
                    # api call per volume.  
                    myfilter = {'instance-id': volInst}
                    inst = regconn.get_all_instances(myfilter)[0]
                    #now, another api call to get the instance details :\
                    #print inst.instances[0]
                    inst_details = regconn.get_instance_details(inst.instances[0])
                    try:
                        instUser = inst_details['key_name']
                        if instUser is None:
                            print "%s had no keypair..WTF" % (inst_details['instance_id'])
                        else:
                            #now do update the tag on the volume.
                            vol.add_tag('user', instUser)
                            print "set %s on instance %s" % (instUser, inst_details['instance_id'])
                    except KeyError:
                        #this means the instance didn't have a key, which is very rare
                        print "%s didn't have a key, skipping" % (volInst)
                    #
                    #check to see if this volume has 'delete on termination' set
                    #
                    #print dir(vol)
                    check_dot(inst.instances[0], vol)
				#
				#Now, set a the 'lastAttached' tag on the volume to equal the current time, but only if 
                # we haven't updated the time on this volume in more than 24 hours (to speed the script up some, 
                #as well as eliminate errors using too many api calls)
				#
                try:
                    lastAttached = vol.tags['lastAttached']
                    parsedAttached = parser.parse(lastAttached)
                    #if it does exist, compare with nowtime
                    tDelta = nowtime - parsedAttached
                    if datetime.timedelta.total_seconds(tDelta) > 86400:
                        vol.add_tag('lastAttached', nowtime)



                except KeyError:
                    #if it doesn't have the tag set, set it
                    vol.add_tag('lastAttached', nowtime)
                    print '%s had empty attached tag, set to %s' %(vol, nowtime) 
                

                #
                #now we can add all 'naughty' volumes to a list and print.
                #

                #print vol.tags['dot'] 



        
        #attachedvolumes(vol, region)
        #unattachedvolumes(vol)




