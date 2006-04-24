#!/usr/bin/env python
#
# This script is a replacement for `emerge search`.
# It searches an index file generated by eupdatedb
# from the portage tree.
#
# Author: David Peter <davidpeter@web.de>
#

from getopt import *
import sys

sys.path.insert(0, "/usr/lib/portage/pym")
sys.path.insert(0, "/usr/lib/esearch")

from output import bold, red, green, darkgreen, turquoise, nocolor
from os.path import exists
import re

from common import needdbversion

esearchdbdir =  "/var/cache/edb/"

def usage():
    print "esearch (0.7.1) - Replacement for 'emerge search' with search-index"
    print ""
    print bold("Usage:"), "esearch [", darkgreen("options"), "] pattern"
    print bold("Options:")
    print darkgreen("  --help") + ", " + darkgreen("-h")
    print "    Print help message"
    print ""
    print darkgreen("  --searchdesc") + ", " + darkgreen("-S")
    print "    Search package descriptions as well"
    print ""
    print darkgreen("  --fullname") + ", " + darkgreen("-F")
    print "    Search packages full name (includes category)"
    print ""
    print darkgreen("  --instonly") + ", " + darkgreen("-I")
    print "    Find only packages which are installed"
    print ""
    print darkgreen("  --compact") + ", " + darkgreen("-c")
    print "    More compact output format"
    print ""
    print darkgreen("  --verbose") + ", " + darkgreen("-v")
    print "    Give a lot of additional information (slow!)"
    print ""
    print darkgreen("  --ebuild") + ", " + darkgreen("-e")
    print "    View ebuilds of found packages"
    print ""
    print darkgreen("  --own=") + "format" + ", " + darkgreen("-o"), "format"
    print "    Use your own output format, see manpage for details of format"
    print ""
    print darkgreen("  --directory=") + "dir" + ", " + darkgreen("-d"), "dir"
    print "    Use dir as directory to load esearch index from"
    print ""
    print darkgreen("  --nocolor") + ", " + darkgreen("-n")
    print "    Don't use ANSI codes for colored output"

    sys.exit(0)

def error(msg, fatal = True):
    print red(" * Error:"), msg
    print
    if fatal:
        sys.exit(1)

def searchEbuilds(path, portdir = True, searchdef = ""):
    global ebuilds, output, defebuild
    pv = ""
    pkgs = []
    nr = len(ebuilds) + 1

    if portdir:
        rep = darkgreen("Portage")
    else:
        rep = red("Overlay")

    if isdir(path):
        list = listdir(path)

        for file in list:
            if file[-7:] == ".ebuild":
                pv = file[:-7]
                pkgs.append(pkgsplit(pv))
                pkgs[-1].append(path + "/" + file)
                if searchdef != "" and pv == searchdef:
                    defebuild = (searchdef, pkgs[-1][3])
        pkgs.sort(pkgcmp)
        for pkg in pkgs:
            rev = ""
            if pkg[2] != "r0":
                rev = "-" + pkg[2]
            output.append(" " + rep + " [" + bold(str(nr)) + "] " + pkg[0] + "-" + pkg[1] + rev + "\n")
            ebuilds.append(pkg[3])
            nr += 1

NORMAL =  1
COMPACT = 2
VERBOSE = 3
EBUILDS = 4
OWN =     5

outputm =    NORMAL
searchdesc = False
fullname =   False
pattern =    False
instonly =   False

try:
    opts = getopt(sys.argv[1:], "hSFIcveo:d:n", ["help", "searchdesc", "fullname", "instonly", "compact", "verbose", "ebuild", "own=", "directory=", "nocolor"])
except GetoptError, errmsg:
    error(str(errmsg) + " (see " + darkgreen("--help") + " for all options)")

for a in opts[0]:
    arg = a[0]

    if arg in ("-S", "--searchdesc"):
        searchdesc = True
    elif arg in ("-F", "--fullname"):
        fullname = True
    elif arg in ("-I", "--instonly"):
        instonly = True
    elif arg in ("-c", "--compact"):
        outputm = COMPACT
    elif arg in ("-v", "--verbose"):
        import string
        from portage import portdb, best, settings
        from output import blue
        from common import version
        outputm = VERBOSE
    elif arg in ("-e", "--ebuilds"):
        from os import listdir, getenv, system
        from os.path import isdir
        from portage import settings, pkgcmp, pkgsplit

        portdir = settings["PORTDIR"]
        overlay = settings["PORTDIR_OVERLAY"]
        outputm = EBUILDS
        ebuilds = []
        defebuild = (0, 0)
    elif arg in ("-o", "--own"):
        outputm = OWN
        outputf = a[1]
    elif arg in ("-d", "--directory"):
        esearchdbdir = a[1]
        if not exists(esearchdbdir):
            error("directory '" + darkgreen(esearchdbdir) + "' does not exist.")
    elif arg in ("-n", "--nocolor"):
        nocolor()

if fullname and searchdesc:
    error("Please use either " + darkgreen("--fullname") + " or " + darkgreen("--searchdesc"))

if len(opts[1]) == 0:
    usage()

def outofdateerror():
    error("The version of the esearch index is out of date, please run " + green("eupdatedb"))


try:
    sys.path.append(esearchdbdir)
    from esearchdb import db
    try:
        from esearchdb import dbversion
        if dbversion < needdbversion:
            outofdateerror()
    except ImportError:
        outofdateerror()
except ImportError:
    error("Could not find esearch-index. Please run " + green("eupdatedb") + " as root first")


patterns = opts[1]
regexlist = []

# Hacks for people who aren't regular expression gurus
for pattern in patterns:
    if pattern == "*":
        pattern = ".*"
    else:
        pattern = re.sub("\+\+", "\+\+", pattern)
    regexlist.append([re.compile(pattern, re.IGNORECASE), pattern, "", 0])

# Could also loop through all packages only once, and remember which
# regex from regexlist has matched this package, and then build the output
# => probably faster

i = 0
for regex, pattern, foo, foo in regexlist:
    count = 0
    output = []
    for pkg in db:
        found = False

        if instonly and not pkg[4]:
            continue

        if fullname and regex.search(pkg[1]):
            found = True
        elif not fullname and regex.search(pkg[0]):
            found = True
        elif searchdesc and regex.search(pkg[7]):
            found = True

        if found:
            if outputm in (NORMAL, VERBOSE):
                if not pkg[4]:
                    installed = "[ Not Installed ]"
                else:
                    installed = pkg[4]

                if pkg[2]:
                    masked = red(" [ Masked ]")
                else:
                    masked = ""

                output.append("%s  %s%s\n      %s %s\n      %s %s\n" % \
                        (green("*"), bold(pkg[1]), masked,
                        darkgreen("Latest version available:"), pkg[3],
                        darkgreen("Latest version installed:"), installed))

                if outputm == VERBOSE:
                    mpv = best(portdb.xmatch("match-all", pkg[1]))
                    try:
                        iuse_split = string.split(portdb.aux_get(pkg[1] + "-" +  pkg[3], ["IUSE"])[0], " ")
                    except KeyError, e:
                        print "Package %s is no longer in the portage tree." % pkg[1] + "-" + pkg[3]
                        continue
                    iuse_split.sort()
                    iuse = ""

                    for ebuild_iuse in iuse_split:
                        if not ebuild_iuse:
                            continue
                        if ebuild_iuse in settings["USE"]:
                            iuse += red("+" + ebuild_iuse) + " "
                        else:
                            iuse += blue("-" + ebuild_iuse) + " "

                    if iuse == "":
                        iuse = "-"

                    output.append("      %s         %s\n      %s       %s\n" % \
                            (darkgreen("Unstable version:"), version(mpv),
                             darkgreen("Use Flags (stable):"), iuse))

                output.append("      %s %s\n      %s    %s\n      %s %s\n      %s     %s\n\n" % \
                        (darkgreen("Size of downloaded files:"), pkg[5],
                         darkgreen("Homepage:"), pkg[6],
                         darkgreen("Description:"), pkg[7],
                         darkgreen("License:"), pkg[8]))

            elif outputm in (COMPACT, EBUILDS):
                prefix0 = " "
                prefix1 = " "

                if pkg[3] == pkg[4]:
                    color = darkgreen
                    prefix1 = "I"
                elif not pkg[4]:
                    color = darkgreen
                    prefix1 = "N"
                else:
                    color = turquoise
                    prefix1 = "U"

                if pkg[2]:
                    prefix0 = "M"

                output.append("[%s%s] %s (%s):  %s\n" % \
                        (red(prefix0), color(prefix1), bold(pkg[1]), color(pkg[3]), pkg[7]))

            elif outputm == OWN:
                # %c => category
                # %n => package name
                # %p => same as %c/%n
                # %m => masked
                # %va => latest version available
                # %vi => latest version installed
                # %s => size of downloaded files
                # %h => homepage
                # %d => description
                # %l => license

                o = outputf
                o = o.replace("%c", pkg[1].split("/")[0])
                o = o.replace("%n", pkg[0])
                o = o.replace("%p", pkg[1])

                masked = ""
                if pkg[2]:
                    masked = "masked"
                o = o.replace("%m", masked)
                o = o.replace("%va", pkg[3])

                installed = pkg[4]
                if not installed:
                    installed = ""
                o = o.replace("%vi", installed)
                o = o.replace("%s", pkg[5])
                o = o.replace("%h", pkg[6])
                o = o.replace("%d", pkg[7])
                o = o.replace("%l", pkg[8])

                o = o.replace("\\n", "\n")
                o = o.replace("\\t", "\t")
                output.append(o)

            if outputm == EBUILDS:
                if count == 0:
                    searchdef = pkg[0] + "-" + pkg[3]
                else:
                    searchdef = ""

                searchEbuilds("%s/%s/" % (portdir, pkg[1]), True, searchdef)
                if overlay:
                    searchEbuilds("%s/%s/" % (overlay, pkg[1]), False, searchdef)

                output.append("\n")

            count += 1

    regexlist[i][2] = "".join(output)
    regexlist[i][3] = count
    i += 1

for regex, pattern, output, count in regexlist:
    if outputm == NORMAL:
        print "[ Results for search key :", bold(pattern), "]"
        print "[ Applications found :", bold(str(count)), "]\n"

    try:
    	print output,
    except IOError:
    	pass

    if outputm == NORMAL:
        print ""

if outputm == EBUILDS and count != 0:
    if count > 1:
        defebuild = (0, 0)

    if len(ebuilds) == 1:
        nr = 1
    else:
        if defebuild[0] != 0:
            print bold("Show Ebuild"), " (" + darkgreen(defebuild[0]) + "): ",
        else:
            print bold("Show Ebuild: "),
        try:
            nr = sys.stdin.readline()
        except KeyboardInterrupt:
            sys.exit(1)
    try:
        editor = getenv("EDITOR")
        if editor:
            system(editor + " " + ebuilds[int(nr) - 1])
        else:
            print ""
            error("Please set EDITOR", False)
    except IndexError:
        print ""
        error("No such ebuild", False)
    except ValueError:
        if defebuild[0] != 0:
            system(editor + " " + defebuild[1])
        else:
            print ""
            error("Please enter a valid number", False)
