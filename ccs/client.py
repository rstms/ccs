#!/usr/bin/env python3

import requests
import os
from pathlib import Path

from .error import CloudSigmaClientError,ParameterError,ResourceNotFound

class CloudSigmaClient(object):
    def __init__(self, region=None, username=None, password=None):

        region = region or os.getenv('CLOUDSIGMA_REGION')
        username = username or os.getenv('CLOUDSIGMA_USERNAME')
        password = password or os.getenv('CLOUDSIGMA_PASSWORD')

        # use hack to pass credentials directly to pycloudsigma module
        # See github issue:
        #   https://github.com/cloudsigma/pycloudsigma/issues/7
        # Initialization workaround adapted from:
        #   http://blog.sourcepole.ch/2016/11/22/manually-initializing-the-pycloudsigma-module/
        # now import (and initialize) the cloudsigma module

        # allow pycloudsigma to read a null config file
        os.putenv('CLOUDSIGMA_CONFIG','/dev/null')
        import cloudsigma
        # monkeypatch the config values into the module config
        cloudsigma.conf.config.__setitem__('api_endpoint', f'https://{region}.cloudsigma.com/api/2.0/')
        cloudsigma.conf.config.__setitem__('ws_endpoint', f'wss://direct.{region}.cloudsigma.com/websocket')
        cloudsigma.conf.config.__setitem__('username', username)
        cloudsigma.conf.config.__setitem__('password', password)

        # save config values for local image upload
        self.username = username
        self.password = password
        self.upload_endpoint = f'https://direct.{region}.cloudsigma.com/api/2.0/drives/upload/'

        self.config = cloudsigma.conf.config
        self.server = cloudsigma.resource.Server()
        self.drive = cloudsigma.resource.Drive()
        self.vlan = cloudsigma.resource.VLAN()
        self.ip = cloudsigma.resource.IP()
        self.subscription = cloudsigma.resource.Subscriptions()
        self.capabilities = cloudsigma.resource.Capabilites()

    def _get_name(self, uuid, _type):
        if _type == 'server':
            server = self.find_server(uuid)
            name = server.get('name')
        elif _type == 'drive':
            drive = self.find_drive(uuid)
            name = drive.get('name')
        elif _type == 'vlan':
            vlan = self.find_vlan(uuid)
            name = vlan['meta'].get('name')
        elif _type == 'ip':
            ip = self.find_ip(uuid)
            name = ip['meta'].get('name')
        elif _type == 'subscription':
            name = None
        else:
            raise ParameterError('unknown resource type {_type}')
        return name or f'<unnamed_{_type}>'

    def _format_resource(self, resource, item):
        data = dict(uuid=item['uuid'])
        if resource == self.server:
            label = 'server' 
            name = self._get_name(item['uuid'], 'server')
            drives = [self._get_name(drive['drive']['uuid'], 'drive') for drive in item['drives']]
            count = item['smp']
            speed = int(item['cpu'])/ count
            detail = f"status={item['status']} cpu={count}x{speed/1000}Ghz memory={self.format_memory_value(item['mem'])} drives={drives}"
        elif resource == self.drive:
            label = 'drive' 
            name = self._get_name(item['uuid'], 'drive')
            mounted = item['mounted_on']
            if len(mounted):
                mounted = f"mounted={[self._get_name(server['uuid'], 'server') for server in mounted]}"
            else:
                mounted = '<unmounted>'
            detail = f"size={self.format_memory_value(item['size'])} media={item['media']} type={item['storage_type']} {mounted}"
        elif resource == self.vlan:
            label = 'vlan'
            name = self._get_name(item['uuid'], 'vlan')
            detail = f"'{item['meta'].get('description')}'"
        elif resource == self.ip:
            label = 'ip'
            name = self._get_name(item['uuid'], 'ip')
            detail = f"[{self._get_name(item['server']['uuid'], 'server') if item['server'] else 'free'}] '{item['meta'].get('description')}'"
        elif resource == self.subscription:
            label = 'subscription'
            name = self._get_name(item['uuid'], 'subscription')
            detail = ''
        else:
            label = 'unknown'
            detail = ''

        return f"{label} {item['uuid']} '{name}' {detail}"

    def _list_resources(self, resource, detail=False, uuid=False, human=False):
        if detail or uuid or human:
            resources = resource.list_detail()
        else:
            resources = resource.list()
        if uuid:
            resources = [i['uuid'] for i in resources]
        elif human:
            resources = [self._format_resource(resource, item) for item in resources]
        return resources

    def list_all(self, detail=False, uuid=False, human=False):
        resources = {}
        all_resources = dict(
            servers=self.server,
            drives=self.drive,
            vlans=self.vlan,
            ips=self.ip
        )
        for label, resource in all_resources.items():
            resources[label] = self._list_resources(resource, detail, uuid, human)
        return resources

    def list_servers(self, detail=False, uuid=False, human=False):
        return self._list_resources(self.server, detail, uuid, human)

    def list_drives(self, detail=False, uuid=False, human=False):
        return self._list_resources(self.drive, detail, uuid, human)

    def list_vlans(self, detail=False, uuid=False, human=False):
        return self._list_resources(self.vlan, detail, uuid, human)

    def list_ips(self, detail=False, uuid=False, human=False):
        return self._list_resources(self.ip, detail, uuid, human)

    def list_subscriptions(self, detail=False, uuid=False, human=False):
        return self._list_resources(self.subscription)

    def list_capabilities(self, detail=False, uuid=False, human=False):
        return self._list_resources(self.capabilities)

    def _find_resource(self, resources, _type, name):
        for resource in resources:
            if name in [resource.get('name'), resource.get('uuid')]:
                return resource
        raise ResourceNotFound(f'unknown {_type} {name}')

    def find_server(self, name):
        return self._find_resource(self.list_servers(True), 'server', name)

    def find_drive(self, name):
        return self._find_resource(self.list_drives(True), 'drive', name)

    def find_vlan(self, name):
        return self._find_resource(self.list_vlans(True), 'vlan', name)

    def find_ip(self, name=None):
        return self._find_resource(self.list_ips(True), 'ip', name)

    def find_subscription(self, name=None):
        return self._find_resource(self.list_subscriptions(True), 'subscription', name)

    def open_tty(self, name):
        return self.server.open_console(self.find_server(name)['uuid'])

    def close_tty(self, name):
        return self.server.close_console(self.find_server(name)['uuid'])

    def open_vnc(self, name):
        return self.server.open_vnc(self.find_server(name)['uuid'])

    def close_vnc(self, name):
        return self.server.close_vnc(self.find_server(name)['uuid'])

    def convert_memory_value(self, value):
        if value[-1] in ('t', 'T'):
            value = float(value[:-1]) * 1024 ** 4
        if value[-1] in ('g', 'G'):
            value = float(value[:-1]) * 1024 ** 3
        elif value[-1] in ('m', 'M'):
            value = float(value[:-1]) * 1024 ** 2
        elif value[-1] in ('k', 'K'):
            value = float(value[:-1]) * 1024
        else:
            value = int(value)
        return int(value)

    def format_memory_value(self, value):
        value = float(value)
        if value >= 1024 ** 4:
            value /= 1024 ** 4
            suffix = 'T'
        elif value >= 1024 ** 3:
            value /= 1024 ** 3
            suffix = 'G'
        elif value >= 1024 ** 2:
            value /= 1024 ** 2
            suffix = 'M'
        elif value >= 1024:
            value /= 1024
            suffix = 'K'
        else:
            suffix = ''
        number = "%.1f" % (value)
        if number[-2:] == '.0':
            number = number[:-2]
        return number + suffix

    def map_storage_type(self, storage_type):
        if storage_type == 'ssd':
            return 'dssd'
        elif storage_type == 'magnetic':
            return 'zadara'

        raise ParameterError(f'unknown storage_type {storage_type}')

    def create_drive(self, name, size, media, multimount, storage_type):
        return self.drive.create(dict(
            name=name,
            size=self.convert_memory_value(size),
            media=media,
            storage_type=self.map_storage_type(storage_type),
            allow_multimount=multimount
        ))

    def modify_drive(self, name, rename=None, media=None, multimount=None, storage_type=None):
        drive = self.find_drive(name)
        if rename:
            drive['name'] = rename
        if media:
            drive['media'] = media
        if multimount:
            drive['allow_multimount'] = multimount=='enable'
        if storage_type:
            drive['storage_type'] = storage_type
        return self.drive.update(drive['uuid'], drive)

    def resize_drive(self, drive, size):
        drive['size'] = self.convert_memory_value(size)
        return self.drive.resize(drive['uuid'], drive)

    def create_server(self, name, cpu_count, cpu_speed, memory, password, attach_drive, create_drive, boot_cdrom, smp):
        """create a server, attaching or creating a drive, attaching a boot iso"""

        parameters = dict(
            name=name,
            cpu=cpu_count * cpu_speed,
            smp=cpu_count,
            mem=self.convert_memory_value(memory),
            vnc_password=password,
            cpus_instead_of_cores=bool(smp=='cpu')
        )
        server = self.server.create(parameters)

        server.setdefault('drives', [])
        if boot_cdrom:
            cdrom = self.find_drive(boot_cdrom)
            if cdrom:
                if cdrom['media'] == 'cdrom':
                    server['drives'].append(dict(
                        boot_order=2,
                        dev_channel='0:0',
                        device='ide', 
                        drive=cdrom['uuid']
                    ))
                else:
                    raise ParameterError(f'failed boot cdrom attach; {boot_cdrom} media must be cdrom')
            else:
                raise ResourceNotFound(f'failed boot cdrom attach; {boot_cdrom} not found')

        if attach_drive:
            drive = self.find_drive(attach_drive)
            if drive['media'] != 'disk':
                raise ParameterError(f'failed drive attach; {attach_drive} must be a disk drive')
            elif drive['status'] != 'unmounted':
                raise ParameterError(f'failed drive attach; {attach_drive} must be unmounted')
        elif create_drive:
            drive = self.create_drive(f'{name}-system', create_drive, 'disk', False, 'ssd')
        else:
            drive = None
            
        if drive: 
            server['drives'].append(dict(
                boot_order=1,
                dev_channel='0:0',
                device='virtio',
                drive=drive['uuid']
            ))

        # default nic creation is a single public DHCP
        server['nics']  = [{
            'ip_v4_conf': {
                'conf': 'dhcp',
                'ip': None
            },
            'model': 'virtio',
            'vlan': None
        }]
    
        return self.server.update(server['uuid'], server)


    def upload_drive_image(self, input_file):
        """upload an image, creating a new drive, and return UUID"""
        s = requests.Session()
        s.auth = (self.config.get('username'), self.config.get('password'))
        s.headers.update({'Content-Type': 'application/octet-stream'})
        r = s.post(self.upload_endpoint, data=input_file)
        return r.text.strip()
