#!/bin/bash

ovs_repo=$1
ovs_branch=$2
repo_action=$3
net_dev=$4
controller_cidr=$5
controller_ip=$6
hosts_file=$7
https_proxy=$8 # optional

echo "
{
    \"type\": \"OvnMultihostEngine\",
    \"controller\": {
        \"type\": \"OvnSandboxControllerEngine\",
        \"deployment_name\": \"ovn-controller-node\",
        \"ovs_repo\": \"$ovs_repo\",
        \"ovs_branch\": \"$ovs_branch\",
        \"repo_action\": \"$repo_action\",
        \"ovs_user\": \"root\",
        \"net_dev\": \"$net_dev\","

if test X$https_proxy != X; then
echo "
        \"https_proxy\": \"$https_proxy\","
fi
echo "
        \"controller_cidr\": \"$controller_cidr\",
        \"provider\": {
            \"type\": \"OvsSandboxProvider\",
            \"credentials\": [
                {
                    \"host\": \"$controller_ip\",
                    \"user\": \"root\"}
            ]
        }
    },
    \"nodes\": [
"
i=0
n=`cat $hosts_file | wc -l`
for node in `cat $hosts_file`; do
    ((i=i+1))
    echo "
        {
            \"type\": \"OvnSandboxFarmEngine\",
            \"deployment_name\": \"ovn-farm-node-$i\",
            \"ovs_repo\": \"$ovs_repo\",
            \"ovs_branch\": \"$ovs_branch\",
            \"repo_action\": \"$repo_action\",
            \"ovs_user\" : \"root\","
    if test X$https_proxy != X; then
    echo "
            \"https_proxy\": \"$https_proxy\","
    fi
    echo "
            \"provider\": {
                \"type\": \"OvsSandboxProvider\",
                \"credentials\": [
                    {
                        \"host\": \"$node\",
                        \"user\": \"root\"}
                ]
            }"
    if test X$n != X$i; then
        echo "
        },"
    else
        echo "
        }"
    fi
done

echo "
    ]
}"


