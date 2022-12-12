import json
import os
import socket
import threading

import geoip2.database
import geoip2.errors


class GeoIP2:
    def __init__(self, path):
        self.reader_city = geoip2.database.Reader(os.path.join(path, 'GeoLite2-City.mmdb'))
        self.not_found_ips = set()

    def get_relevant_data(self, ip):
        try:
            response = self.reader_city.city(ip)
            return {
                'lat': response.location.latitude,
                'lon': response.location.longitude,
                'country': response.country.name,
            }
        except geoip2.errors.AddressNotFoundError:
            self.not_found_ips.add(ip)
            return None


class IPUtils:
    _hostname_cache_file = '.hostname_cache'

    def __init__(self, geoip_path=None):
        self._geo_lock = threading.Lock()
        self._hostname_lock = threading.Lock()
        self.geo_ips_known = {}
        self.hostname_ips_known = {}
        self.new_hostnames = 0
        if geoip_path:
            self.geoip2 = GeoIP2(geoip_path)

        if os.path.exists(self._hostname_cache_file):
            self.load_hostname_cache()

    def load_hostname_cache(self):
        with open(self._hostname_cache_file, 'r') as f:
            self.hostname_ips_known = json.load(f)

    def save_hostname_cache(self):
        with open(self._hostname_cache_file, 'w') as f:
            json.dump(self.hostname_ips_known, f)

    def get_relevant_geoip_data(self, ip):
        with self._geo_lock:
            if ip not in self.geo_ips_known:
                self.geo_ips_known[ip] = self.geoip2.get_relevant_data(ip)
            return self.geo_ips_known[ip]

    def get_hostname_from_ip(self, ip):
        with self._hostname_lock:
            if ip not in self.hostname_ips_known:
                try:
                    self.hostname_ips_known[ip] = socket.getnameinfo((ip, 0), 0)[0]
                except socket.herror:
                    self.hostname_ips_known[ip] = None
                self.new_hostnames += 1
            return self.hostname_ips_known[ip]
