#!/bin/bash
[ $# -eq 0 ] && {
    echo "Usage: $0 <version>"
    exit 1
}

version=$1
mkdir -p report/$version
cd report/$version
rally task list > rally_task_list
ps aux | grep ovn > ps.txt
ls ~/controller-sandbox/ -l | grep ovn.b > ovndb_disk_size
source /root/controller-sandbox/sandbox.rc
ovn-appctl -t ovn-northd coverage/show > northd_coverage_show
ovn-sbctl lflow-list | wc -l > lflow_count

sleep 5

for i in `seq 1 5`; do
    echo ""
    echo wait=hv:; time ovn-nbctl --wait=hv sync
    sleep 3
done > latency_idle_hv 2>&1

for i in `seq 1 5`; do
    echo ""
    echo wait=sb:; time ovn-nbctl --wait=sb sync
    sleep 3
done > latency_idle_sb 2>&1
