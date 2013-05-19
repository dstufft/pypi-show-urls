# Copyright 2013 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import itertools
import sys
import urlparse
import xmlrpclib

import html5lib
import requests

from pkg_resources import safe_name
from setuptools.package_index import distros_for_url


def installable(project, url):
    normalized = safe_name(project).lower()
    return bool([dist for dist in distros_for_url(url) if
                        safe_name(dist.project_name).lower() == normalized])


def version_for_url(project, url):
    normalized = safe_name(project).lower()
    return [dist for dist in distros_for_url(url) if
                safe_name(dist.project_name).lower() == normalized][0].version


def process_page(html, package, url, verbose):
    if verbose:
        print("")
        print("  Candidates from %s" % url)
        print("  ----------------" + ("-" * len(url)))

    installable_ = set()
    for link in html.findall(".//a"):
        if "href" in link.attrib:
            try:
                absolute_link = urlparse.urljoin(url, link.attrib["href"])
            except Exception:
                continue

            if installable(package, absolute_link):
                if verbose:
                    print("    " + absolute_link)
                installable_.add((url, absolute_link))

    if not verbose:
        print("  %s Candiates from %s" % (len(installable_), url))

    return installable_


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")

    group = parser.add_argument_group('type')
    group.add_argument("-p", "--packages",
                                    dest="is_packages", action="store_true")
    group.add_argument("-u", "--users", dest="is_users", action="store_true")

    parser.add_argument("items", nargs="+")

    args = parser.parse_args()

    if args.is_packages and args.is_users:
        return "Must specify only one of -u and -p"

    if not args.is_packages and not args.is_users:
        return "Must specify one of -u or -p"

    if args.is_packages:
        # A list of packages to look for
        packages = args.items

    if args.is_users:
        # a list of users
        users = args.items
        xmlrpc = xmlrpclib.ServerProxy("https://pypi.python.org/pypi")
        packages = []
        for user in users:
            packages.extend([x[1] for x in xmlrpc.user_packages(user)
                                                        if x[1] is not None])

    # Should we run in verbose mode
    verbose = args.verbose

    session = requests.session()
    session.verify = False

    for package in packages:
        print("")
        print("Download candidates for %s" % package)
        print("========================" + ("=" * len(package)))

        # Grab the page from PyPI
        url = "https://pypi.python.org/simple/%s/" % package
        resp = session.get(url)
        if resp.status_code == 404:
            continue
        resp.raise_for_status()

        html = html5lib.parse(resp.content, namespaceHTMLElements=False)

        spider = set()
        installable_ = set()

        for link in itertools.chain(
                            html.findall(".//a[@rel='download']"),
                            html.findall(".//a[@rel='homepage']")):
            if "href" in link.attrib:
                try:
                    absolute_link = urlparse.urljoin(url, link.attrib["href"])
                except Exception:
                    continue

                if not installable(package, absolute_link):
                    parsed = urlparse.urlparse(absolute_link)
                    if parsed.scheme.lower() in ["http", "https"]:
                        spider.add(absolute_link)

        # Find installable links from the PyPI page
        installable_ |= process_page(html, package, url, verbose)

        # Find installable links from pages we spider
        for link in spider:
            try:
                resp = session.get(link)
                resp.raise_for_status()
            except Exception:
                continue

            html = html5lib.parse(resp.content, namespaceHTMLElements=False)
            installable_ |= process_page(html, package, link, verbose)

        # Find the ones only available externally
        internal = set()
        external = set()
        for candidate in installable_:
            version = version_for_url(package, candidate[1])
            if (candidate[0] == url and
                    urlparse.urlparse(candidate[1]).netloc
                        == "pypi.python.org"):
                internal.add(version)
            else:
                external.add(version)

        # Display information
        if verbose:
            print("")
            print("  Versions only available externally")
            print("  ----------------------------------")

            for version in (external - internal):
                print("    " + version)
        else:
            print("  %s versions only available externally" %
                                                    len((external - internal)))


if __name__ == "__main__":
    sys.exit(main())
