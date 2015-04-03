#
#this is just an example of how to use tucker's scripts to create a cluster
#
/launch-se-cluster.sh --cluster testcluster --mapr-version 3.0.2 --config-file ./3node.lst --region us-west-1 --key-file ~/.ssh/some-key.pem  --image ami-72ce4642 --image-su ec2-user --instance-type m1.large
