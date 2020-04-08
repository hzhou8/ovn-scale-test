# Copyright 2016 Ebay Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import netaddr
import random
import re

from rally_ovs.plugins.ovs.scenarios import ovn

from rally.task import scenario
from rally.task import atomic
from rally.task import validation

class OvnNorthbound(ovn.OvnScenario):
    """Benchmark scenarios for OVN northbound."""

    @scenario.configure()
    def create_routed_network(self, lswitch_create_args = None,
                              networks_per_router = None,
                              lport_create_args = None,
                              port_bind_args = None,
                              create_mgmt_port = True):
        self._create_routed_network(lswitch_create_args,
                                    networks_per_router,
                                    lport_create_args,
                                    port_bind_args,
                                    create_mgmt_port)

    @atomic.action_timer("ovn.create_or_update_network_policy_address_sets")
    def create_or_update_network_policy_address_sets(self, name, ipaddr,
                                                     create = True):
        if (create):
            self._create_address_set("%s_ingress_as" % name, ipaddr)
            self._create_address_set("%s_egress_as" % name, ipaddr)
        else:
            self._address_set_add_addrs("%s_ingress_as" % name, ipaddr)
            self._address_set_add_addrs("%s_egress_as" % name, ipaddr)

    @atomic.action_timer("ovn.create_port_group_acls")
    def create_port_group_acls(self, name):

        port_group_acl = {"name" : "@%s" % name}
        port_group = {"name" : name}
        """
        create two acl for each ingress/egress of the Network Policy (NP)
        to allow ingress and egress traffic selected by the NP
        """
        # ingress
        match = "%(direction)s == %(lport)s && ip4.src == $%(address_set)s"
        acl_create_args = { "match" : match,
                            "address_set" : "%s_ingress_as" % name,
                            "priority": 1010, "direction": "from-lport",
                            "type": "port-group" }
        self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                         atomic_action = False)
        acl_create_args = { "priority" : 1009,
                            "match" : "%(direction)s == %(lport)s && ip4",
                            "type": "port-group", "direction":"from-lport",
                            "action": "allow-related" }
        self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                         atomic_action = False)
        # egress
        match = "%(direction)s == %(lport)s && ip4.dst == $%(address_set)s"
        acl_create_args = { "match" : match,
                            "address_set" : "%s_egress_as" % name,
                            "priority": 1010, "type": "port-group" }
        self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                         atomic_action = False)
        acl_create_args = { "priority" : 1009,
                            "match" : "%(direction)s == %(lport)s && ip4",
                            "type": "port-group"," action": "allow-related" }
        self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                         atomic_action = False)

    def create_or_update_default_deny_port_group(self, port_list):
        # default_deny port_group
        if (self.context["iteration"] == 0):
            self._port_group_add("portGroupDefDeny", port_list, atomic_action = False)

            # create defualt acl for ingress and egress traffic: only allow ARP traffic
            port_group_acl = {"name" : "@portGroupDefDeny"}
            port_group = {"name" : "portGroupDefDeny"}

            # ingress
            acl_create_args = { "match" : "%(direction)s == %(lport)s && arp",
                                "priority": 1001, "direction": "from-lport",
                                "type": "port-group" }
            self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                             atomic_action = False)
            acl_create_args = { "match" : "%(direction)s == %(lport)s",
                                "direction": "from-lport", "action": "drop",
                                "type": "port-group" }
            self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                             atomic_action = False)

            # egress
            acl_create_args = { "match" : "%(direction)s == %(lport)s && arp",
                                "priority": 1001, "type": "port-group" }
            self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                             atomic_action = False)
            acl_create_args = { "match" : "%(direction)s == %(lport)s",
                                "action": "drop", "type": "port-group" }
            self._create_acl(port_group, [port_group_acl], acl_create_args, 1,
                             atomic_action = False)
        else:
            self._port_group_add_port("portGroupDefDeny", port_list,
                                      atomic_action = False)

    @atomic.action_timer("ovn.create_or_update_network_policy")
    def create_or_update_network_policy(self, name, port_list,
                                        ipaddr, create = True):
        self.create_or_update_default_deny_port_group(port_list)

        if (create):
            self._port_group_add(name, port_list, atomic_action = False)
        else:
            self._port_group_add_port(name, port_list, atomic_action = False)

        self.create_or_update_network_policy_address_sets(name, ipaddr, create)
        if (create):
            self.create_port_group_acls(name)

    def configure_routed_lport(self, lswitch, lport_create_args, port_bind_args,
                               ip_start_index = 0, address_set_size = 1,
                               network_policy_size = 1, create_acls = True):
        lports = self._create_switch_lports(lswitch, lport_create_args,
                                            lport_ip_shift = ip_start_index)

        if create_acls:
            network_cidr = lswitch.get("cidr", None)
            if network_cidr:
                ip_list = netaddr.IPNetwork(network_cidr.ip + ip_start_index).iter_hosts()
                ipaddr = str(next(ip_list))
            else:
                ipaddr = ""

            lport = lports[0]
            iteration = self.context["iteration"]
            network_policy_index = iteration / network_policy_size
            create_network_policy = (iteration % network_policy_size) == 0
            port_group_name = "networkPolicy%d" % network_policy_index
            self.create_or_update_network_policy(port_group_name, lport["name"],
						 ipaddr, create_network_policy)

        sandboxes = self.context["sandboxes"]
        sandbox = sandboxes[self.context["iteration"] % len(sandboxes)]
        self._bind_ports_and_wait(lports, [sandbox], port_bind_args)

    @scenario.configure()
    def create_routed_lport(self, lport_create_args = None,
                            port_bind_args = None,
                            create_acls = True,
                            address_set_size = 1,
                            network_policy_size = 1):
        lswitches = self.context["ovn-nb"]
        ip_offset = lport_create_args.get("ip_offset", 1) if lport_create_args else 1
        address_set_size = 1 if address_set_size == 0 else address_set_size

        iteration = self.context["iteration"]
        lswitch = lswitches[iteration % len(lswitches)]
        ip_start_index = iteration / len(lswitches) + ip_offset

        self.configure_routed_lport(lswitch, lport_create_args,
                                    port_bind_args, ip_start_index,
                                    address_set_size, network_policy_size,
                                    create_acls)

    @scenario.configure(context={})
    def cleanup_routed_lswitches(self):
        sandboxes = self.context.get("sandboxes", [])
        for sandbox in sandboxes:
            self._flush_ovs_internal_ports(sandbox)
        lswitches = self.context.get("ovn-nb", [])
        self._delete_lswitch(lswitches)
        self._delete_routers()
        for address_set in self._list_address_set():
            self._remove_address_set(address_set)

    @scenario.configure(context={})
    def create_and_list_lswitches(self, lswitch_create_args=None):
        self._create_lswitches(lswitch_create_args)
        self._list_lswitches()


    @scenario.configure(context={})
    def create_and_delete_lswitches(self, lswitch_create_args=None):
        lswitches = self._create_lswitches(lswitch_create_args or {})
        self._delete_lswitch(lswitches)


    @scenario.configure(context={})
    def cleanup_lswitches(self, lswitch_cleanup_args=None):
        lswitch_cleanup_args = lswitch_cleanup_args or {}
        prefix = lswitch_cleanup_args.get("prefix", "")

        lswitches = self.context.get("ovn-nb", [])
        matched_lswitches = []
        for lswitch in lswitches:
            if lswitch["name"].find(prefix) == 0:
                matched_lswitches.append(lswitch)

        self._delete_lswitch(matched_lswitches)


    @validation.number("lports_per_lswitch", minval=1, integer_only=True)
    @scenario.configure(context={})
    def create_and_list_lports(self,
                              lswitch_create_args=None,
                              lport_create_args=None,
                              lports_per_lswitch=None):

        lswitches = self._create_lswitches(lswitch_create_args)
        self._create_lports(lswitches, lport_create_args, lports_per_lswitch)

        self._list_lports(lswitches)


    @scenario.configure(context={})
    def create_and_delete_lports(self,
                              lswitch_create_args=None,
                              lport_create_args=None,
                              lports_per_lswitch=None):

        lswitches = self._create_lswitches(lswitch_create_args)
        lports = self._create_lports(lswitches, lport_create_args,
                                     lports_per_lswitch)
        self._delete_lport(lports)
        self._delete_lswitch(lswitches)



    def get_or_create_lswitch_and_lport(self,
                              lswitch_create_args=None,
                              lport_create_args=None,
                              lports_per_lswitch=None):

        lswitches = None
        if lswitch_create_args != None:
            lswitches = self._create_lswitches(lswitch_create_args)
            for lswitch in lswitches:
                lports = self._create_switch_lports(lswitch,
                                                    lport_create_args,
                                                    lports_per_lswitch)
                lswitch["lports"] = lports
        else:
            lswitches = self.context["ovn-nb"]

        return lswitches



    @validation.number("lports_per_lswitch", minval=1, integer_only=True)
    @validation.number("acls_per_port", minval=1, integer_only=True)
    @scenario.configure(context={})
    def create_and_list_acls(self,
                              lswitch_create_args=None,
                              lport_create_args=None,
                              lports_per_lswitch=None,
                              acl_create_args=None,
                              acls_per_port=None):
        lswitches = self.get_or_create_lswitch_and_lport(lswitch_create_args,
                                    lport_create_args, lports_per_lswitch)

        for lswitch in lswitches:
            self._create_acl(lswitch, lswitch["lports"],
                             acl_create_args, acls_per_port)

        self._list_acl(lswitches)



    @scenario.configure(context={})
    def cleanup_acls(self):

        lswitches = self.context["ovn-nb"]

        self._delete_all_acls_in_lswitches(lswitches)


    @validation.number("lports_per_lswitch", minval=1, integer_only=True)
    @validation.number("acls_per_port", minval=1, integer_only=True)
    @scenario.configure(context={})
    def create_and_delete_acls(self,
                              lswitch_create_args=None,
                              lport_create_args=None,
                              lports_per_lswitch=None,
                              acl_create_args=None,
                              acls_per_port=None):

        lswitches = self.get_or_create_lswitch_and_lport(lswitch_create_args,
                                    lport_create_args, lports_per_lswitch)


        for lswitch in lswitches:
            self._create_acl(lswitch, lswitch["lports"],
                             acl_create_args, acls_per_port)


        self._delete_all_acls_in_lswitches(lswitches)

    @scenario.configure(context={})
    def create_and_remove_address_set(self, name, address_list):
        self._create_address_set(name, address_list)
        self._remove_address_set(name)


