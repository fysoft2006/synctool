#
#    synctool.nodeset.py        WJ111
#
#   synctool Copyright 2013 Walter de Jong <walter@heiho.net>
#
#   synctool COMES WITH NO WARRANTY. synctool IS FREE SOFTWARE.
#   synctool is distributed under terms described in the GNU General Public
#   License.
#

'''The nodeset helps making a set of nodes from command-line arguments
It is used by synctool-master, dsh, dcp, dsh-ping

usage:
  first make an instance of NodeSet
  then add nodes, groups, excluded nodes/groups
  call synctool.config.read_config()
  call nodeset.addresses(), which will return a list of addresses
  use the address list to contact the nodes
  use nodeset.get_nodename_from_address() to get a nodename
'''

import synctool.config
import synctool.lib
from synctool.lib import verbose, stderr
import synctool.param


class NodeSet(object):
    '''class representing a set of nodes'''

    def __init__(self):
        self.nodelist = set()
        self.grouplist = set()
        self.exclude_nodes = set()
        self.exclude_groups = set()
        self.namemap = {}

    def add_node(self, nodelist):
        '''add a node to the nodeset'''

        self.nodelist = set(nodelist.split(','))

    def add_group(self, grouplist):
        '''add a group to the nodeset'''

        self.grouplist = set(grouplist.split(','))

    def exclude_node(self, nodelist):
        '''remove a node from the nodeset'''

        self.exclude_nodes = set(nodelist.split(','))

    def exclude_group(self, grouplist):
        '''remove a group from the nodeset'''

        self.exclude_groups = set(grouplist.split(','))

    def addresses(self):
        '''return list of addresses of relevant nodes'''

        # by default, work on default_nodeset
        if not self.nodelist and not self.grouplist:
            if not synctool.param.DEFAULT_NODESET:
                return []

            self.nodelist = synctool.param.DEFAULT_NODESET

        # check if the nodes exist at all
        # the user may have given bogus names
        all_nodes = set(synctool.config.get_all_nodes())
        unknown = (self.nodelist | self.exclude_nodes) - all_nodes
        for node in unknown:
            stderr("no such node '%s'" % node)
            return None

        # check if the groups exist at all
        unknown = ((self.grouplist | self.exclude_groups) -
                   synctool.param.ALL_GROUPS)
        for group in unknown:
            stderr("no such group '%s'" % group)
            return None

        self.nodelist |= synctool.config.get_nodes_in_groups(self.grouplist)

        self.exclude_nodes |= synctool.config.get_nodes_in_groups(
                                self.exclude_groups)

        # remove excluded nodes from nodelist
        self.nodelist -= self.exclude_nodes

        if not self.nodelist:
            return []

        addrs = []

        ignored_nodes = self.nodelist & synctool.param.IGNORE_GROUPS

        if synctool.lib.VERBOSE:
            for node in ignored_nodes:
                verbose('node %s is ignored' % node)

        self.nodelist -= ignored_nodes

        for node in self.nodelist:
            # ignoring a group results in also ignoring the node
            my_groups = set(synctool.config.get_groups(node))
            my_groups &= synctool.param.IGNORE_GROUPS
            if len(my_groups) > 0:
                verbose('node %s is ignored due to an ignored group' % node)
                ignored_nodes.add(node)
                continue

            addr = synctool.config.get_node_ipaddress(node)
            self.namemap[addr] = node

            if not addr in addrs:    # make sure we do not have duplicates
                addrs.append(addr)

        # print message about ignored nodes
        if (len(ignored_nodes) > 0 and not synctool.lib.QUIET and
            not synctool.lib.UNIX_CMD):
            if synctool.param.TERSE:
                synctool.lib.terse(synctool.lib.TERSE_WARNING,
                                   'ignored nodes')
            else:
                ignored_str = ('warning: ignored nodes: ' +
                               ','.join(list(ignored_nodes)))
                if len(ignored_str) < 80:
                    print ignored_str
                else:
                    print 'warning: some nodes are ignored'

        return addrs

    def get_nodename_from_address(self, addr):
        '''map the address back to a nodename'''

        if self.namemap.has_key(addr):
            return self.namemap[addr]

        return addr

# EOB
