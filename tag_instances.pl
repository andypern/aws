#!/usr/bin/perl -w

#
#Deprecated: this uses the ec2-cli , which is slow...and painful. 
#

use strict;
use Data::Dumper;
#region list

my %fat_hash;

my @AMAZON_REGIONS=("us-east-1", "us-west-1", "us-west-2", "eu-west-1", "ap-northeast-1", "ap-southeast-1", "ap-southeast-2", "sa-east-1");

# for each region, get the key list

foreach my $region(@AMAZON_REGIONS){
	chomp($region);
	print "working on region $region\n";
	$fat_hash{$region}{'instance_count'} = 0;
	my @keylist = `ec2-describe-keypairs |awk {'print \$2'}`;
	#for each key, enumerate instance IDs
	foreach my $key(@keylist){
		chomp ($key);
		unless($fat_hash{$key}{'instance_count'}){
			$fat_hash{$key}{'instance_count'} = 0;
		}
		$fat_hash{$region}{$key}{'instance_count'} = 0;
		#print "ec2-describe-instances -region $region -F key-name=$key\n";
		my @instances = `ec2-describe-instances -region $region -F key-name=$key|grep ^INSTANCE|awk {'print \$2'}`;
		#for each instance, set the tag for 'user=key'
		foreach my $instance(@instances){
			chomp($instance);
			print "ec2-create-tags $instance --region $region --tag user=$key\n";
			system("ec2-create-tags $instance --region $region --tag user=$key");
			$fat_hash{$AMAZON_REGIONS}{'instance_count'} += 1;
			$fat_hash{$key}{'instance_count'} += 1;
			$fat_hash{$region}{$key}{'instance_count'} += 1;
		}
	}
}

#print Dumper(%fat_hash);
