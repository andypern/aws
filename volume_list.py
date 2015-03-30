import os
import re
import boto
import boto.ec2

apikey =  os.environ.get("APIKEY", None)
apisecret = os.environ.get("APISECRET", None)


#####
#TODO
# * find unattached volumes, find date, delete if >30d && unatt'd (and log it)
# * find att'd vol's, tag them w/ instance.key_name  (user=xyz)

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
    print "%s was unattached .." % (vol)



##end functions


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
                #
                try:
                    user = vol.tags['user']
                    #this means there was a user key. Likely *WE* set it
                    #but at some point we'll need to make sure they match the tag on the instance
                    print "%s had user tag %s" % (vol, user)
                except KeyError:
                    #this means there was no user key. now we have to set one.
                    # we could do something like pull all the inst details into
                    # a dictionary, then systematically go through and check each 
                    # entry and see if it matched what we have in our volume list
                    #. that would save a bunch of API calls (one per volume).  Perhaps later..
                    #for now, lets try going after: 
                    # volInst => inst => inst.tags.user , then setting vol.tags.user=inst.tags.user
                    # this is at least one api call per instance (perhaps one per volume), plus another
                    # api call per volume.  Luckily, we only have to do this once
                    myfilter = {'instance-id': volInst}
                    inst = regconn.get_all_instances(myfilter)[0]
                    #now, another api call to get the instance details :\
                    print inst.instances[0]
                    inst_details = regconn.get_instance_details(inst.instances[0])
                    try:
                        instUser = inst_details['key_name']
                        if instUser is None:
                            print "%s had no keypair..WTF" % (inst_details['instance_id'])
                        else:
                            #now do update the tag on the volume.
                            vol.add_tag('user', instUser)
                    except KeyError:
                        #this means the instance didn't have a key, which is very rare
                        print "%s didn't have a key, skipping" % (volInst)



        #
        #this block is an example of how to go from instance -> blockdevicemapping -> volume_id
        # its unnecessary since we can get the instance_id directly from the volume.
        #
        # #
        # #now that we have all instances for the region, lets check them.
        # #
        # for instance in reg_inst_list:
        #     #get inst_attributes
        #     myattribute='blockDeviceMapping'
        #     inst_attributes = regconn.get_instance_attribute(
        #         instance.id,
        #         myattribute)
        #     inst_device_list =  inst_attributes['blockDeviceMapping'].values()
        #     for device in inst_device_list:
        #         #now we got the volume_id
        #         volid = device.volume_id
        #         #so, go check each volume to see if its tags line up? seems pricey..




        
        #attachedvolumes(vol, region)
        #unattachedvolumes(vol)




