#! /usr/bin/env python3
"""
 Credits: This script is based on a python script from
          https://github.com/osic/stackalytics.git
          and was extended/adopted to fit my use case.
"""
import argparse
import csv
import sys
import json
from urllib import request, parse, error

import time
import pytz

from progressbar import Bar, ProgressBar, Percentage, RotatingMarker, ETA, FileTransferSpeed

# Base URL being accessed
BASE_URL = 'http://stackalytics.com/api/1.0/contribution'


def total_reviews(marks):
    """The API call above returns a set of "marks", representing code reviews
    for each of the possible scores (e.g., -2, -1, 0, 1, 2, etc.).
    This function simply adds them all together and returns total code reviews
    """
    total = 0
    for i in marks.values():
        total += i
    return total


def pull_contributions(project: str, releases: str, modules: str,
                       companies: str, outfile_name: str):

    results = []
    parms = {}
    row = []
    _release = None
    _module = None
    _company = None
    _current = 0

    # default parameter for OpenStack statistics
    parms['project_type'] = project.lower()

    # TODO: iter over the release/module/company
    split_releases = releases.split(",")
    split_modules = modules.split(",")
    split_companies = companies.split(",")

    total = len(split_releases) * len(split_modules) * len(split_companies)
    widgets = ['Retrieve Stackalytics data: ', Percentage(), ' ', Bar(marker='#', left='[', right=']'), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=total).start()

    for release in split_releases:
        parms['release'] = release.lower()
        _module = None
        # append row if needed
        if row and _release != release:
            results.append(row)
            row = []
            _release = ""

        for module in split_modules:
            if module.lower() == "all":
                parms['module'] = ""
            else:
                parms['module'] = module.lower()
            # append row if needed
            if row and _module != module:
                results.append(row)
                row = []
                _module = ""

            for company in split_companies:
                if company.lower() == "all":
                    parms['company'] = ""
                else:
                    parms['company'] = company.lower()

                # Encode the query string
                querystring = parse.urlencode(parms)

                #print("Query string: {0}".format(querystring), file=sys.stderr)

                # Make a GET request and read the response
                try:
                    u = request.urlopen(BASE_URL + '?' + querystring)
                    contribution = json.loads(u.read().decode(encoding='UTF-8'))['contribution']

                    if not _module:
                        row.extend([release])
                        row.extend([module])

                    row.extend([contribution['commit_count'],
                                contribution['drafted_blueprint_count'],
                                contribution['completed_blueprint_count'],
                                contribution['filed_bug_count'],
                                contribution['resolved_bug_count'],
                                total_reviews(contribution['marks']),
                                contribution['translations']
                               ])

                    # tmp vars
                    _release = release
                    _module = module
                    _company = company

                    # print ("row: {0}".format(row), file=sys.stderr)

                except error.HTTPError:
                    print("Couldn't retrieve data!", file=sys.stderr)
                except:
                    raise

                _current+=1
                pbar.update(_current)

    if row:
        # append last row if needed
        results.append(row)
        row = []

    pbar.finish()

    # Write output CSV file
    if outfile_name is None:
        outfile = sys.stdout
    else:
        outfile = open(outfile_name, 'w')

    if not outfile:
        raise FileNotFoundError("Couldn't open output file")

    print("\nWriting output file", file=sys.stderr)
    header = ['','']
    fieldnames = ['release','module']
    for company in companies.split(","):
        header.extend([company, '', '', '', '', '', ''])

        fieldnames.extend(['#commits',
                           '#dBP',
                           '#cBP',
                           '#fBugs',
                           '#rBugs',
                           '#reviews',
                           '#trans'
                           ])

    writer = csv.writer(outfile)
    writer.writerow(header)
    writer.writerow(fieldnames)
    writer.writerows(results)

    outfile.close()

def example0():
    pbar = ProgressBar(widgets=[Percentage(), Bar()], maxval=10).start()
    for i in range(10):
      # do something
      time.sleep(0.1)
      pbar.update(i + 1)
    pbar.finish()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Stackalytics data retriever")
    parser.add_argument('-p', '--project', dest='project', help='project name')
    parser.add_argument('-r', '--releases', dest='releases', help='OpenStack release names')
    parser.add_argument('-m', '--modules', dest='modules', help='OpenStack module names')
    parser.add_argument('-C', '--coremodules', action="store_true", help='Get OpenStack core (mature) modules')
    parser.add_argument('-E', '--extramodules', action="store_true", help='Get some less mature OpenStack modules')
    parser.add_argument('-c', '--companies', dest='companies', help='Company names')
    parser.add_argument('-o', '--output', dest='outfile_name',
                        help='Output CSV file name (defaults to stdout)')

    args = parser.parse_args()

    if not args.project:
        args.project = "openstack"
    if not args.releases:
        args.releases = "Pike,Ocata,Newton,Mitaka,Liberty,Kilo,Juno,Icehouse,Havana,Grizzly,All"
    if not args.companies:
        args.companies = "All,Red Hat,SUSE,Mirantis,Canonical,b1 systems gmbh"
    if args.coremodules:
        args.modules = "All,cinder-group,glance-group,keystone-group,neutron-group,nova-group,swift-group"
    elif args.extramodules:
        args.modules = "All,aodh,barbican-group,ceilometer-group,designate-group,gnocchi,heat-group,horizon-group,ironic-group,magnum-group,manila-group,mistral-group,monasca-group,murano-group,panko,rally-group,sahara-group,tempest,trove-group,openstackclient-group,oslo-group,security-group,documentation-group"
    elif not args.modules:
        args.modules = "All,cinder-group,glance-group,keystone-group,neutron-group,nova-group,swift-group,aodh,barbican-group,ceilometer-group,designate-group,gnocchi,heat-group,horizon-group,ironic-group,magnum-group,manila-group,mistral-group,monasca-group,murano-group,panko,rally-group,sahara-group,tempest,trove-group,openstackclient-group,oslo-group,security-group,documentation-group"

    pull_contributions(args.project, args.releases, args.modules, args.companies, args.outfile_name)
