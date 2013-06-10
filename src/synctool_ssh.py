#! /usr/bin/env python
#
#	synctool-ssh	WJ109
#
#   synctool by Walter de Jong <walter@heiho.net> (c) 2003-2013
#
#   synctool COMES WITH NO WARRANTY. synctool IS FREE SOFTWARE.
#   synctool is distributed under terms described in the GNU General Public
#   License.
#

import os
import sys
import string
import getopt
import shlex
import errno

import synctool.aggr
import synctool.config
import synctool.lib
from synctool.lib import verbose,stderr,unix_out
import synctool.nodeset
import synctool.param
import synctool.unbuffered

NODESET = synctool.nodeset.NodeSet()

OPT_AGGREGATE = False
MASTER_OPTS = None
SSH_OPTIONS = None


def run_dsh(remote_cmd_arr):
	'''run remote command to a set of nodes using ssh (param ssh_cmd)'''

	nodes = NODESET.addresses()
	if not nodes:
		print 'no valid nodes specified'
		sys.exit(1)

	ssh_cmd_arr = shlex.split(synctool.param.SSH_CMD)

	if SSH_OPTIONS:
		ssh_cmd_arr.extend(shlex.split(SSH_OPTIONS))

	synctool.lib.run_parallel(master_ssh, worker_ssh,
		(nodes, ssh_cmd_arr, remote_cmd_arr), len(nodes))


def master_ssh(rank, args):
	(nodes, ssh_cmd_arr, remote_cmd_arr) = args

	node = nodes[rank]
	cmd_str = string.join(remote_cmd_arr)

	if node == synctool.param.NODENAME:
		verbose('running %s' % cmd_str)
		unix_out(cmd_str)
	else:
		verbose('running %s to %s %s' % (os.path.basename(ssh_cmd_arr[0]),
			NODESET.get_nodename_from_address(node), cmd_str))

		if SSH_OPTIONS:
			unix_out('%s %s %s %s' % (string.join(ssh_cmd_arr), SSH_OPTIONS,
				node, cmd_str))
		else:
			unix_out('%s %s %s' % (string.join(ssh_cmd_arr), node, cmd_str))


def worker_ssh(rank, args):
	if synctool.lib.DRY_RUN:		# got here for nothing
		return

	(nodes, ssh_cmd_arr, remote_cmd_arr) = args

	node = nodes[rank]
	nodename = NODESET.get_nodename_from_address(node)

	if nodename == synctool.param.NODENAME:
		# is this node the local node? Then do not use ssh
		ssh_cmd_arr = []
	else:
		ssh_cmd_arr.append(node)

	ssh_cmd_arr.extend(remote_cmd_arr)

	# execute ssh+remote command and show output with the nodename
	synctool.lib.run_with_nodename(ssh_cmd_arr, nodename)


def check_cmd_config():
	'''check whether the commands as given in synctool.conf actually exist'''

	(ok, synctool.param.SSH_CMD) = synctool.config.check_cmd_config(
									'ssh_cmd', synctool.param.SSH_CMD)
	if not ok:
		sys.exit(-1)


def usage():
	print ('usage: %s [options] <remote command>' %
		os.path.basename(sys.argv[0]))
	print 'options:'
	print '  -h, --help                     Display this information'
	print '  -c, --conf=dir/file            Use this config file'
	print ('                                 (default: %s)' %
		synctool.param.DEFAULT_CONF)
	print '''  -n, --node=nodelist            Execute only on these nodes
  -g, --group=grouplist          Execute only on these groups of nodes
  -x, --exclude=nodelist         Exclude these nodes from the selected group
  -X, --exclude-group=grouplist  Exclude these groups from the selection
  -a, --aggregate                Condense output
  -o, --options=options          Set additional ssh options
  -p, --numproc=num              Number of concurrent procs

  -N, --no-nodename              Do not prepend nodename to output
  -v, --verbose                  Be verbose
      --unix                     Output actions as unix shell commands
      --dry-run                  Do not run the remote command
      --version                  Print current version number

A nodelist or grouplist is a comma-separated list

synctool-ssh by Walter de Jong <walter@heiho.net> (c) 2009-2013'''


def get_options():
	global NODESET, REMOTE_CMD, MASTER_OPTS, OPT_AGGREGATE, SSH_OPTIONS

	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)

	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hc:vn:g:x:X:ao:Nqp:',
			['help', 'conf=', 'verbose', 'node=', 'group=', 'exclude=',
			'exclude-group=', 'aggregate', 'options=', 'no-nodename',
			'unix', 'dry-run', 'quiet', 'numproc='])
	except getopt.error, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)

	except getopt.GetoptError, (reason):
		print '%s: %s' % (os.path.basename(sys.argv[0]), reason)
#		usage()
		sys.exit(1)

	except:
		usage()
		sys.exit(1)

	# first read the config file
	for opt, arg in opts:
		if opt in ('-h', '--help', '-?'):
			usage()
			sys.exit(1)

		if opt in ('-c', '--conf'):
			synctool.param.CONF_FILE = arg
			continue

		if opt == '--version':
			print synctool.param.VERSION
			sys.exit(0)

	synctool.config.read_config()
	check_cmd_config()

	# then process the other options
	MASTER_OPTS = [ sys.argv[0] ]

	for opt, arg in opts:
		if opt:
			MASTER_OPTS.append(opt)
		if arg:
			MASTER_OPTS.append(arg)

		if opt in ('-h', '--help', '-?', '-c', '--conf', '--version'):
			continue

		if opt in ('-v', '--verbose'):
			synctool.lib.VERBOSE = True
			continue

		if opt in ('-n', '--node'):
			NODESET.add_node(arg)
			continue

		if opt in ('-g', '--group'):
			NODESET.add_group(arg)
			continue

		if opt in ('-x', '--exclude'):
			NODESET.exclude_node(arg)
			continue

		if opt in ('-X', '--exclude-group'):
			NODESET.exclude_group(arg)
			continue

		if opt in ('-p', '--numproc'):
			try:
				synctool.param.NUM_PROC = int(arg)
			except ValueError:
				print ("%s: option '%s' requires a numeric value" %
					(os.path.basename(sys.argv[0]), opt))
				sys.exit(1)

			if synctool.param.NUM_PROC < 1:
				print ('%s: invalid value for numproc' %
					os.path.basename(sys.argv[0]))
				sys.exit(1)

			continue

		if opt in ('-a', '--aggregate'):
			OPT_AGGREGATE = True
			continue

		if opt in ('-o', '--options'):
			SSH_OPTIONS = arg
			continue

		if opt in ('-N', '--no-nodename'):
			synctool.lib.OPT_NODENAME = False
			continue

		if opt == '--unix':
			synctool.lib.UNIX_CMD = True
			continue

		if opt == '--dry-run':
			synctool.lib.DRY_RUN = True
			continue

		if opt in ('-q', '--quiet'):
			# silently ignore this option
			continue

	if not args:
		print '%s: missing remote command' % os.path.basename(sys.argv[0])
		sys.exit(1)

	if args != None:
		MASTER_OPTS.extend(args)

	return args


def main():
	synctool.param.init()

	sys.stdout = synctool.unbuffered.Unbuffered(sys.stdout)
	sys.stderr = synctool.unbuffered.Unbuffered(sys.stderr)

	cmd_args = get_options()

	if OPT_AGGREGATE:
		synctool.aggr.run(MASTER_OPTS)
		sys.exit(0)

	synctool.config.init_mynodename()

	run_dsh(cmd_args)


if __name__ == '__main__':
	try:
		main()
	except IOError, ioerr:
		if ioerr.errno == errno.EPIPE:		# Broken pipe
			pass
		else:
			print ioerr

	except KeyboardInterrupt:		# user pressed Ctrl-C
		pass

# EOB
