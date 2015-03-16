#!/usr/bin/perl -w

use strict;
#region list

my @AMAZON_REGIONS=("us-east-1", "us-west-1", "us-west-2", "eu-west-1", "ap-northeast-1", "ap-southeast-1", "ap-southeast-2", "sa-east-1");

# for each region, get the key list

foreach my $region(@AMAZON_REGIONS){
	chomp($region);
	print "working on region $region\n";
	my @keylist = `ec2-describe-keypairs |awk {'print \$2'}`;
	#for each key, enumerate instance IDs
	foreach my $key(@keylist){
		chomp ($key);
		#print "ec2-describe-instances -region $region -F key-name=$key\n";
		my @instances = `ec2-describe-instances -region $region -F key-name=$key|grep ^INSTANCE|awk {'print \$2'}`;
		#for each instance, set the tag for 'user=key'
		foreach my $instance(@instances){
			chomp($instance);
			print "working on $instance\n";
			print "ec2-create-tags $instance --region $region --tag user=$key\n";
			system("ec2-create-tags $instance --region $region --tag user=$key");
		}
	}
}
