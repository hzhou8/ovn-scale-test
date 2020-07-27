#!/bin/bash

ovs_repo=$1
ovs_branch=$2
ovs_repo_action=$3
ovn_repo=$4
ovn_branch=$5
ovn_repo_action=$6
net_dev=$7
controller_cidr=$8
controller_ip=$9
hosts_file=${10}
https_proxy=${11} # optional

echo "
{
    \"type\": \"OvnMultihostEngine\",
    \"controller\": {
        \"type\": \"OvnSandboxControllerEngine\",
        \"deployment_name\": \"ovn-controller-node\",
        \"ovs_repo\": \"$ovs_repo\",
        \"ovs_branch\": \"$ovs_branch\",
        \"ovs_repo_action\": \"$ovs_repo_action\",
        \"ovn_repo\": \"$ovn_repo\",
        \"ovn_branch\": \"$ovn_branch\",
        \"ovn_repo_action\": \"$ovn_repo_action\",
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
            \"ovs_repo_action\": \"$ovs_repo_action\",
            \"ovn_repo\": \"$ovn_repo\",
            \"ovn_branch\": \"$ovn_branch\",
            \"ovn_repo_action\": \"$ovn_repo_action\",
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


