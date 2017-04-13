from obspy.clients.fdsn import Client
'''
    from obspy import UTCDateTime
    starttime = UTCDateTime("2001-01-01")

    # to access metadata via Client from a single data center's station service
    from obspy.clients.fdsn import Client
    client = Client("IRIS")

    # or, access data via FederatorClient from multiple data centers
    from obspy.clients.fdsn import FederatorClient
    client = FederatorClient("IRIS")


    # the requests are submited in exactly the same manner
    inv = client.get_stations(network="IU", station="req_str*", starttime=starttime)
'''


'''
    service-options 	:: service specific options
    targetservice=<station|dataselect>
    format=<request|text>
    includeoverlaps=<true|false>

    active-options 	 	::
    [channel-options] [map-constraints] [time-constraints]
    channel-options 	::
    net=<network>
    sta=<station>
    loc=<location>
    cha=<channel>

    map-constraints 	::  ONE OF
        boundaries-rect 	::
            minlatitude=<degrees>
            maxlatitude=<degrees>
            minlongitude=<degrees>
            maxlongitude=<degrees>
        boundaries-circ 	::
            latitude=<degrees>
            longitude=<degrees>
            maxradius=<number>
            minradius=<number>

    time-constraints 	::
        starttime=<date>
        endtime=<date>
        startbefore=<date>
        startafter=<date>
        endbefore=<date>
        endafter=<date>
        updatedafter=<date>]

    passive-options 	::
        includerestricted=<true|false>
        includeavailability=<true|false>
        matchtimeseries=<true|false>
        longestonly=<true|false>
        quality=<D|R|Q|M|B>
        level=<net|sta|cha|resp>
        minimumlength=<number>
'''

from obspy.clients.fdsn.routers import parse_federated_response, FederatedResponse

# inv2x_set(inv) will be used to quickly decide what exists and what doesn't
def inv2channel_set(inv):
    'return a set containing string representations of an inv object'
    return {n.code + "." + s.code + "." +
            c.location_code + "." + c.code
            for n in inv for s in n for c in s}

def inv2station_set(inv):
    'return a set containing string representations of an inv object'
    return {n.code + "."+ s.code for n in inv for s in n}

def inv2network_set(inv):
    'return a set containing string representations of an inv object'
    return {n.code for n in inv}

def req2network_set(req):
    'return a set containing string representations of an request line'
    req_str = set()
    for line in req:
        (net, sta, loc, cha, startt, endt) = r.split()
        req_str.add(net)
    return req_str

def req2station_set(req):
    'return a set containing string representations of an request line'
    req_str = set()
    for line in req:
        (net, sta, loc, cha, startt, endt) = r.split()
        req_str.add(net + "." + sta)
    return req_str

def req2channel_set(req):
    'return a set containing string representations of an request line'
    req_str = set()
    for line in req:
        (net, sta, loc, cha, startt, endt) = r.split()
        req_str.add(net + "." + sta + "." + loc + "." + cha)
    return req_str

#converters used to make comparisons between inventory items and requests
INV_CONVERTER = {"channel":inv2channel_set, "station":inv2station_set, "network":inv2network_set}
REQ_CONVERTER = {"channel":req2channel_set, "station":req2station_set, "network":req2network_set}

def request_exists_in_inventory(inv, requests, level):
    'compare inventory to requests'
    # does not account for timespans, only for existence net-sta-loc-cha matches
    inv_set = INV_CONVERTER[level](inv)
    req_set = REQ_CONVERTER[level](requests)
    members = req_set.intersection(inv_set)
    non_members = req_set.difference(inv_set)
    return members, non_members

def initial_station_request(datac, **kwarg):
    '''request data from one datacenter. returns raw_data, success_lines, failed_lines'''

    #The datacenter name may not match the datacenter name as implemented by the fdsn Client
    remap = {"IRISDMC":"IRIS", "GEOFON":"GFZ", "SED":"ETH", "USPSC":"USP"}
    level = kwarg["level"]

    dc_id = datac.code

    if dc_id in remap:
        dc_id = remap[dc_id]
    client = Client(dc_id)

    #TODO large requests could be denied (code #413) and will need to be chunked.
    print(datac.request_text("STATIONSERVICE").count('\n'))
    #TODO vett datac.request_txt here by comparing to what we have. maybe do during 2nd round
    try:
        inv = client.get_stations_bulk(bulk=datac.request_text("STATIONSERVICE"))
    except: #except expression as identifier:
        lines_to_resubmit.extend(datac.request_lines) #unsuccessful attempt
        print(dc_id, "error!")
        return (None, lines_to_resubmit)
    else:
        successful, failed = request_exists_in_inventory(inv, datac.request_lines, level)
        successful_retrieves = datac.request_lines
        add_datacenter_reference(inv, datac.code, datac.services)
        inv_set = inv_converter[level](inv)
        return (inv, successful_retrieves, failed)


def fed_get_stations(**kwarg):
    '''This will be the original request for the federated station service'''
    LEVEL = kwarg["level"]

    all_inv = []
    lines_to_resubmit = []
    succesful_retrieves = []

    # send request to the FedCatalog
    url = 'https://service.iris.edu/irisws/fedcatalog/1/'
    kwarg["targetservice"] = "STATION"
    r = requests.get(url + "query", params=kwarg, verify=False)

    print "asking from..."
    print([p for p in r.iter_lines() if p.startswith("DATACENTER")])

    sfrp = parse_federated_response(r.text)

    for datac in sfrp:
        dc_id = datac.code

        if dc_id in remap:
            dc_id = remap[dc_id]
        client = Client(dc_id)

        #TODO large requests could be denied (code #413) and will need to be chunked.
        print(datac.request_text("STATIONSERVICE").count('\n'))
        #TODO vett datac.request_txt here by comparing to what we have. maybe do during 2nd round
        try:
            inv = client.get_stations_bulk(bulk=datac.request_text("STATIONSERVICE"))
        except: #except expression as identifier:
            lines_to_resubmit.extend(datac.request_lines) #unsuccessful attempt. Add all to resubmit queue
            print(dc_id, "error!")
        else:
            successful, failed = request_exists_in_inventory(inv, datac.request_lines, LEVEL)
            successful_retrieves = datac.request_lines
            add_datacenter_reference(inv, datac.code, datac.services)
            if not all_inv:
                all_inv = inv
                all_inv_set = inv_converter[LEVEL](inv)
            else:
                all_inv += inv
                all_inv_set = all_inv_set.union(inv_converter[LEVEL](inv))

    # now, perhaps we got lucky, and have all the data we requested?
    if not failed:
        return all_inf
    
    # okey-dokey. Time for round 2. # # #
    # resubmit the failed retrieves to the federator service

    # as data is retrieved, add to all_inv and remove it from the queue.

    return all_inv


# main function
if __name__ == '__main__':
    import doctest
    doctest.testmod(exclude_empty=True)

    import requests
    URL = 'https://service.iris.edu/irisws/fedcatalog/1/'
    R = requests.get(URL + "query", params={"net":"req_str*", "sta":"OK*", "cha":"*HZ"}, verify=False)

    FRP = StreamingFederatedResponseParser(R.iter_lines)
    for n in FRP:
        print(n.request_text("STATIONSERVICE"))
