#!/usr/bin/perl -w

use strict;
#region list

my @AMAZON_REGIONS=("us-east-1", "us-west-1", "us-west-2", "eu-west-1", "ap-northeast-1", "ap-southeast-1", "ap-southeast-2", "sa-east-1");

# for each region, get the key list

foreach my $region(@AMAZON_REGIONS){
	chomp($region);
	my @keylist = `ec2-describe-keypairs |awk {'print \$2'}`;
	#for each key, enumerate instance IDs
	foreach my $key(@keylist){
		print "working on $key\n";
		chomp ($key);
		#print "ec2-describe-instances -region $region -F key-name=$key\n";
		my @instances = `ec2-describe-instances -region $region -F key-name=$key|grep ^INSTANCE|awk {'print \$2'}`;
		#for each instance, set the tag for 'user=key'
		foreach my $instance(@instances){
			print "working on $instance\n";
			chomp($instance);
			print "ec2-create-tags $instance --tag user=$key\n";
			system("ec2-create-tags $instance --tag user=$key");
		}
	}
}
