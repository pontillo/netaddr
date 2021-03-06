#!/usr/bin/env python
#-----------------------------------------------------------------------------
#   Copyright (c) 2008-2016, David P. D. Moss. All rights reserved.
#
#   Released under the BSD license. See the LICENSE file for details.
#-----------------------------------------------------------------------------
#
#   DISCLAIMER
#
#   netaddr is not sponsored nor endorsed by the IEEE.
#
#   Use of data from the IEEE (Institute of Electrical and Electronics
#   Engineers) is subject to copyright. See the following URL for
#   details :-
#
#       - http://www.ieee.org/web/publications/rights/legal.html
#
#   IEEE data files included with netaddr are not modified in any way but are
#   parsed and made available to end users through an API. There is no
#   guarantee that referenced files are not out of date.
#
#   See README file and source code for URLs to latest copies of the relevant
#   files.
#
#-----------------------------------------------------------------------------
"""
Provides access to public OUI and IAB registration data published by the IEEE.

More details can be found at the following URLs :-

    - IEEE Home Page - http://www.ieee.org/
    - Registration Authority Home Page - http://standards.ieee.org/regauth/
"""

import os.path as _path
import csv as _csv

from netaddr.core import Subscriber, Publisher


#: Path to local copy of IEEE OUI Registry data file.
OUI_REGISTRY = _path.join(_path.dirname(__file__), 'oui.txt')
#: Path to netaddr OUI index file.
OUI_METADATA = _path.join(_path.dirname(__file__), 'oui.idx')

#: OUI index lookup dictionary.
OUI_INDEX = {}

#: Path to local copy of IEEE IAB Registry data file.
IAB_REGISTRY = _path.join(_path.dirname(__file__), 'iab.txt')

#: Path to netaddr IAB index file.
IAB_METADATA = _path.join(_path.dirname(__file__), 'iab.idx')

#: IAB index lookup dictionary.
IAB_INDEX = {}


class FileIndexer(Subscriber):
    """
    A concrete Subscriber that receives OUI record offset information that is
    written to an index data file as a set of comma separated records.
    """
    def __init__(self, index_file):
        """
        Constructor.

        :param index_file: a file-like object or name of index file where
            index records will be written.
        """
        if hasattr(index_file, 'readline') and hasattr(index_file, 'tell'):
            self.fh = index_file
        else:
            self.fh = open(index_file, 'w')

        self.writer = _csv.writer(self.fh, lineterminator="\n")

    def update(self, data):
        """
        Receives and writes index data to a CSV data file.

        :param data: record containing offset record information.
        """
        self.writer.writerow(data)


class OUIIndexParser(Publisher):
    """
    A concrete Publisher that parses OUI (Organisationally Unique Identifier)
    records from IEEE text-based registration files

    It notifies registered Subscribers as each record is encountered, passing
    on the record's position relative to the start of the file (offset) and
    the size of the record (in bytes).

    The file processed by this parser is available online from this URL :-

        - http://standards.ieee.org/regauth/oui/oui.txt

    This is a sample of the record structure expected::

        00-CA-FE   (hex)        ACME CORPORATION
        00CAFE     (base 16)        ACME CORPORATION
                        1 MAIN STREET
                        SPRINGFIELD
                        UNITED STATES
    """
    def __init__(self, ieee_file):
        """
        Constructor.

        :param ieee_file: a file-like object or name of file containing OUI
            records. When using a file-like object always open it in binary
            mode otherwise offsets will probably misbehave.
        """
        super(OUIIndexParser, self).__init__()

        if hasattr(ieee_file, 'readline') and hasattr(ieee_file, 'tell'):
            self.fh = ieee_file
        else:
            self.fh = open(ieee_file)

    def parse(self):
        """
        Starts the parsing process which detects records and notifies
        registered subscribers as it finds each OUI record.
        """
        skip_header = True
        record = None
        size = 0

        while True:
            line = self.fh.readline() # unbuffered to obtain correct offsets

            if not line:
                break   # EOF, we're done

            if skip_header and '(hex)' in line:
                skip_header = False

            if skip_header:
                #   ignoring header section
                continue

            if '(hex)' in line:
                #   record start
                if record is not None:
                    #   a complete record.
                    record.append(size)
                    self.notify(record)

                size = len(line)
                offset = (self.fh.tell() - len(line))
                oui = line.split()[0]
                index = int(oui.replace('-', ''), 16)
                record = [index, offset]
            else:
                #   within record
                size += len(line)

        #   process final record on loop exit
        record.append(size)
        self.notify(record)


class IABIndexParser(Publisher):
    """
    A concrete Publisher that parses IAB (Individual Address Block) records
    from IEEE text-based registration files

    It notifies registered Subscribers as each record is encountered, passing
    on the record's position relative to the start of the file (offset) and
    the size of the record (in bytes).

    The file processed by this parser is available online from this URL :-

        - http://standards.ieee.org/regauth/oui/iab.txt

    This is a sample of the record structure expected::

        00-50-C2   (hex)        ACME CORPORATION
        ABC000-ABCFFF     (base 16)        ACME CORPORATION
                        1 MAIN STREET
                        SPRINGFIELD
                        UNITED STATES
    """
    def __init__(self, ieee_file):
        """
        Constructor.

        :param ieee_file: a file-like object or name of file containing IAB
            records. When using a file-like object always open it in binary
            mode otherwise offsets will probably misbehave.
        """
        super(IABIndexParser, self).__init__()

        if hasattr(ieee_file, 'readline') and hasattr(ieee_file, 'tell'):
            self.fh = ieee_file
        else:
            self.fh = open(ieee_file)

    def parse(self):
        """
        Starts the parsing process which detects records and notifies
        registered subscribers as it finds each IAB record.
        """
        skip_header = True
        record = None
        size = 0
        while True:
            line = self.fh.readline()   # unbuffered

            if not line:
                break   # EOF, we're done

            if skip_header and '(hex)' in line:
                skip_header = False

            if skip_header:
                #   ignoring header section
                continue

            if '(hex)' in line:
                #   record start
                if record is not None:
                    record.append(size)
                    self.notify(record)

                offset = (self.fh.tell() - len(line))
                iab_prefix = line.split()[0]
                index = iab_prefix
                record = [index, offset]
                size = len(line)
            elif '(base 16)' in line:
                #   within record
                size += len(line)
                prefix = record[0].replace('-', '')
                suffix = line.split()[0]
                suffix = suffix.split('-')[0]
                record[0] = (int(prefix + suffix, 16)) >> 12
            else:
                #   within record
                size += len(line)

        #   process final record on loop exit
        record.append(size)
        self.notify(record)


def create_oui_index(registry_path, out):
    """Create the OUI index file.

    :param registry_path: The filename to read OUI entries from.
    :param out: A filename (or file-like object) to write the index to.
    """
    oui_parser = OUIIndexParser(registry_path)
    oui_parser.attach(FileIndexer(out))
    oui_parser.parse()


def create_iab_index(registry_path, out):
    """Create the IAB index file.

    :param registry_path: The filename to read OUI entries from.
    :param out: A filename (or file-like object) to write the index to.
    """
    iab_parser = IABIndexParser(registry_path)
    iab_parser.attach(FileIndexer(out))
    iab_parser.parse()


def populate_index(fp, into=None):
    """Given the specified file-like object, populates the given index.

    :param fp: An open file-like object (such as for OUI or IAB entries).
    :param into: If specified, loads the index into the specified dictionary.

    :returns: the populated index object.
    """
    if into is None:
        into = {}
    for row in _csv.reader(fp):
        (key, offset, size) = [int(_) for _ in row]
        into.setdefault(key, [])
        into[key].append((offset, size))
    return into


def load_index_file(filename, into=None):
    """Load OUI or IAB index into the specified object.

    :param filename: The index filename to read.
    :param into: If specified, loads the index into the specified dictionary.

    :returns: the populated index object.
    """
    if into is None:
        into = {}
    fp = open(filename)
    try:
        into = populate_index(fp, into)
    finally:
        fp.close()
    return into

if __name__ == '__main__':
    #   Generate indices when module is executed as a script.
    create_oui_index(OUI_REGISTRY, OUI_METADATA)
    create_iab_index(IAB_REGISTRY, IAB_METADATA)
else:
    #   On module load read indices in memory to enable lookups.
    load_index_file(OUI_METADATA, into=OUI_INDEX)
    load_index_file(IAB_METADATA, into=IAB_INDEX)
