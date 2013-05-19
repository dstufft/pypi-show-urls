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

import lxml.html
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
    print("")

    if verbose:
        print("  Candidates from %s" % url)
        print("  ----------------" + ("-" * len(url)))

    installable_ = set()
    for link in html.xpath("//a"):
        try:
            link.make_links_absolute(url)
        except ValueError:
            continue

        if "href" in link.attrib and installable(package, link.attrib["href"]):
            if verbose:
                print("    " + link.attrib["href"])
            installable_.add((url, link.attrib["href"]))

    if not verbose:
        print("  %s Candiates from %s" % (len(installable_), url))

    return installable_


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("packages", nargs="+")

    args = parser.parse_args()

    # A list of packages to look for
    packages = args.packages

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
        resp.raise_for_status()

        html = lxml.html.document_fromstring(resp.content)

        spider = set()
        installable_ = set()

        for link in itertools.chain(
                            html.find_rel_links("download"),
                            html.find_rel_links("homepage")):
            try:
                link.make_links_absolute(url)
            except ValueError:
                continue

            if "href" in link.attrib and not \
                                    installable(package, link.attrib["href"]):
                parsed = urlparse.urlparse(link.attrib["href"])
                if parsed.scheme.lower() in ["http", "https"]:
                    spider.add(link.attrib["href"])

        # Find installable links from the PyPI page
        installable_ |= process_page(html, package, url, verbose)

        # Find installable links from pages we spider
        for link in spider:
            try:
                resp = session.get(link)
                resp.raise_for_status()
            except Exception:
                continue

            html = lxml.html.document_fromstring(resp.content)
            installable_ |= process_page(html, package, link, verbose)

        # Find the ones only available externally
        internal = set()
        external = set()
        for candidate in installable_:
            version = version_for_url(package, candidate[1])
            if candidate[0] == url:
                internal.add(version)
            else:
                external.add(version)

        # Display information
        print("")

        if verbose:
            print("  Versions only available externally")
            print("  ----------------------------------")

            for version in (external - internal):
                print("    " + version)
        else:
            print("  %s versions only available externally" %
                                                    len((external - internal)))


if __name__ == "__main__":
    sys.exit(main())
