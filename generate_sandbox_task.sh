#!/bin/bash
num=$1
amount=$2
netdev=$3

echo "
{
    \"version\": 2,
    \"title\": \"Create sandbox\",
    \"tags\": [\"ovn\", \"sandbox\"],

      \"subtasks\": [
"

i=0
for id in `seq 1 $num`; do
    echo "
          {
              \"title\": \"Create sandbox on farm $id\",
              \"group\": \"ovn\",
              \"description\": \"\",
              \"tags\": [\"ovn\", \"sandbox\"],
              \"run_in_parallel\": false,

              \"workloads\": [
                  {
                      \"name\": \"OvnSandbox.create_sandbox\",
                      \"args\": {
                          \"sandbox_create_args\": {
                              \"farm\": \"ovn-farm-node-$id\",
                              \"amount\": $amount,
                              \"batch\": 10,
                              \"start_cidr\": \"192.168.$id.0/16\",
                              \"net_dev\": \"$netdev\",

                              \"tag\": \"TOR$id\"
                          }
                      },
                      \"runner\": {
                          \"type\": \"constant\",
                          \"concurrency\": 4,
                          \"times\": 1,
                          \"max_cpu_count\": 4
                      },
                      \"context\": {
                         \"ovn_multihost\" : {
                              \"controller\": \"ovn-controller-node\"
                          }
                      }
                  }
              ]"
    if test X$num != X$i; then
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
