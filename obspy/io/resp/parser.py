#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
readRESP.py
script to read RESP (rdseed -R) files into inventory.Response objects.

:copyright:
    Lloyd Carothers IRIS/PASSCAL, 2016
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
'''
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from future.builtins import *  # NOQA

import io
import re

from obspy.io.xseed import (parser, blockette, fields)

DEBUG = False


def read_resp(data):
    # List of blockettes which is a list of fields
    blockettelist = list()
    # List of fields
    blockettefieldlist = list()
    last_blockette_id = None
    for line in data.splitlines():
        # print(line, end='')
        m = re.match(r"^B(\d+)F(\d+)(?:-(\d+))?(.*)", line)
        if m:
            g = m.groups()
            blockette_number = g[0]
            if blockette_number != last_blockette_id:
                # A new blockette starting
                if len(blockettefieldlist) > 0:
                    # print("new blockette")
                    blockettelist.append(blockettefieldlist)
                    blockettefieldlist = list()
                last_blockette_id = blockette_number
            if not g[2]:
                # Single field per line
                value = re.search(r":\s*(\S*)", g[3]).groups()[0]
                # print( (blockette_number, g[1], value) )
                blockettefieldlist.append((blockette_number, g[1], value))
            else:
                # Multiple fields per line
                first_field = int(g[1])
                last_field = int(g[2])
                fields = g[3].split()
                values = fields[-(last_field - first_field + 1):]
                for i, value in enumerate(values):
                    # print( (blockette_number, first_field + i, value) )
                    blockettefieldlist.append(
                        (blockette_number, first_field + i, value))
        elif re.match(r"^#.*\+", line):
            # Comment line with a + in it means blockette is
            # finished start a new one
            if len(blockettefieldlist) > 0:
                # print("new blockette")
                blockettelist.append(blockettefieldlist)
                blockettefieldlist = list()
            # print()
    # Add last blockette
    if len(blockettefieldlist) > 0:
        blockettelist.append(blockettefieldlist)
    return blockettelist


def record_type_from_blocketteid(bid):
    for voltype in parser.HEADER_INFO:
        if bid in parser.HEADER_INFO[voltype]['blockettes']:
            return voltype


def make_xseed(resp_blockettelist):
    seedparser = parser.Parser()
    seedparser.temp = {'volume': [], 'abbreviations': [], 'stations': []}
    # Make an empty blockette10
    seedparser.temp['volume'].append(blockette.Blockette010(
        debug=DEBUG, strict=False, compact=False, record_type='V'))
    # Make unit lookup blockette34
    b34s = ('034  44  4M/S~velocity in meters per second~',
            '034  25  5V~emf in volts~',
            '034  32  7COUNTS~digital counts~'
            )
    abbv_lookup = {'M/S': '4', 'V': '5', 'COUNTS': '7'}

    for b34 in b34s:
        data = io.BytesIO(b34.encode('utf-8'))
        b34_obj = blockette.Blockette034(debug=DEBUG,
                                         record_type='A')
        b34_obj.parse_seed(data, expected_length=len(b34))
        seedparser.temp['abbreviations'].append(b34_obj)
    seedparser.temp['stations'].append([])
    root_attribute = seedparser.temp['stations'][-1]

    for RESPblockettefieldlist in resp_blockettelist:
        # Create a new blockette using the first field
        RESPblockette_id, RESPfield, resp_value = RESPblockettefieldlist[0]
        class_name = 'Blockette%03d' % int(RESPblockette_id)
        blockette_class = getattr(blockette, class_name)
        record_type = record_type_from_blocketteid(blockette_class.id)
        blockette_obj = blockette_class(debug=DEBUG,
                                        strict=False,
                                        compact=False,
                                        record_type=record_type)
        blockette_fields = (blockette_obj.default_fields +
                            blockette_obj.get_fields())
        unrolled_blockette_fields = list()
        for bf in blockette_fields:
            if isinstance(bf, fields.Loop):
                for df in bf.data_fields:
                    unrolled_blockette_fields.append(df)
            else:
                unrolled_blockette_fields.append(bf)
        blockette_fields = unrolled_blockette_fields
        # List of fields with fields used removed,
        # so unused can be set to default after
        unused_fields = blockette_fields[:]

        for RESPblockette_id, RESPfield, resp_value in RESPblockettefieldlist:
            for bfield in blockette_fields:
                if bfield.id == int(RESPfield):
                    if isinstance(bfield, fields.VariableString):
                        # Variable string needs terminator '~'
                        resp_value += '~'
                    # print(RESPvalue)
                    # Lookup if abbv
                    resp_value = abbv_lookup.get(resp_value, resp_value)
                    data_resp_value = io.BytesIO(resp_value.encode('utf-8'))
                    if (hasattr(bfield, 'length') and
                            bfield.length < len(resp_value)):
                        # RESP does not use the same length for floats
                        # as SEED does
                        bfield.length = len(resp_value)
                    bfield.parse_seed(blockette_obj, data_resp_value)
                    if bfield in unused_fields:
                        unused_fields.remove(bfield)
                    break
        for bfield in unused_fields:
            # Set unused fields to default
            bfield.parse_seed(blockette_obj, None)

        # This is not correct for more than rdseed -R, although it will parse
        # Also will not separate stations blockettes by station
        if record_type == 'S':
            root_attribute.append(blockette_obj)
        elif record_type == 'V':
            seedparser.temp['volume'].append(blockette_obj)
        elif record_type == 'A':
            seedparser.temp['abbreviations'].append(blockette_obj)

        seedparser.blockettes.setdefault(blockette_obj.id,
                                         []).append(blockette_obj)

    seedparser._update_internal_seed_structure()
    return seedparser

if __name__ == '__main__':
    pass
