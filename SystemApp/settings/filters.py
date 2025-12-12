import os
import psutil
import logging


#Custom filter to exclude web-crawler 404 requests
class RequestsFilter(logging.Filter):
    def filter(self, record):
        request_paths = [
            #WordPress / CMS
            'wp-includes/', 'wp-admin/', 'wp-content/', 'wp-login.php',
            'xmlrpc.php', 'wp-config.php', 'wordpress/', 'feed/',
            'robots.txt', 'sitemap.xml', 'llms.txt', '/sellers.json',
            
            #PHPUnit exploit attempts
            '/vendor/phpunit/', '/phpunit/', '/lib/phpunit/',
            '/laravel/vendor/phpunit/', '/tests/vendor/phpunit/',
            '/test/vendor/phpunit/', '/testing/vendor/phpunit/',
            '/cms/vendor/phpunit/', '/crm/vendor/phpunit/',
            '/panel/vendor/phpunit/', '/public/vendor/phpunit/',
            '/apps/vendor/phpunit/', '/app/vendor/phpunit/',
            '/workspace/drupal/vendor/phpunit/', 'ads.txt', 'app-ads.txt'
            
            #Sensitive files / configs
            '.env', '/env', '/version', '/stats', '/index.php', '/index.html' '/public/index.php', '/security.txt', 
            '/.well-known/security.txt', '/config.json', '/server', '/about', '/debug/default/view', '/_all_dbs',
            
            #DNS over HTTPS
            '/dns-query', '/query', '/resolve',
            
            #VPN / RDP / Exchange probes
            '/dana-', '/dana-na/', '/dana-cached/', '/owa/', '/ecp/',
            '/RDWeb', '/Remote', '/wsman', 'sslvpnLogin', 
            'auth.html', 'auth1.html', '/api/sonicos/',
            
            #Misc scanning
            '/containers/json', '/login', '/hello.world',
            '/alive.php', '/developmentserver/metadatauploader',
            '/teorema505', '/aaa9', '/aab9', '/ab2g', '/ab2h',
            '/favicon', '/wiki', 
        ]

        if hasattr(record, 'getMessage'):
            message = record.getMessage().lower()

            if 'not found' in message or '404' in message:
                return not any(path.lower() in message for path in request_paths)
            
            if 'disallowedhost' in message or 'disallowed host' in message:
                return False 

        return True


#Custom filter for Django-Q2
class DjangoQFilter(logging.Filter):
    def __init__(self, memory_threshold=90):
        super().__init__()
        self.logger = logging.getLogger('django-q')
        self.memory_threshold = memory_threshold

    def _check_memory(self):
        usage, limit = None, None
        try:
            #cgroups v2 (for newer Docker versions)
            if os.path.exists('/sys/fs/cgroup/memory.current'):
                with open('/sys/fs/cgroup/memory.current') as f:
                    usage = int(f.read().strip())
                with open('/sys/fs/cgroup/memory.max') as f:
                    limit_raw = f.read().strip()
                    limit = int(limit_raw) if limit_raw.isdigit() else None
                    #Filter out unrealistic limits
                    limit = limit if limit < 9223372036854775807 else None 

            #cgroups v1 (for older Docker versions)
            elif os.path.exists('/sys/fs/cgroup/memory/memory.usage_in_bytes'):
                with open('/sys/fs/cgroup/memory/memory.usage_in_bytes') as f:
                    usage = int(f.read().strip())
                with open('/sys/fs/cgroup/memory/memory.limit_in_bytes') as f:
                    limit_raw = f.read().strip()
                    limit = int(limit_raw) if limit_raw.isdigit() else None 
            
            #fallback to psutil
            if usage is None or limit is None:
                memory_info = psutil.virtual_memory()
                usage = memory_info.used
                limit = memory_info.total

        except Exception as exc:
            self.logger.debug(f'Memory check failed: {exc}')

        return usage, limit
    
    def _get_memory_percentage(self, usage, limit):
        '''Calculate memory percentage with safety checks'''
        if not usage or not limit or limit <= 0:
            return None
        return (usage / limit) * 100

    def _format_bytes(self, bytes_value):
        '''Format bytes into human readable format'''
        if not bytes_value:
            return 'Unknown'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024:
                return f'{bytes_value:.1f} {unit}'
            bytes_value /= 1024
        return f'{bytes_value:.1f} TB'


    def filter(self, record):
        db_error_patterns = [
            'name or service not known',
            'failed to pull task from broker',
            'could not create task from schedule',
            'temporary failure in name resolution',
            'reincarnated pusher',
        ]
    
        if hasattr(record, 'getMessage'):
            message = record.getMessage().lower()
            
            if any(pattern in message for pattern in db_error_patterns):
                usage, limit = self._check_memory()
                memory_percentage = self._get_memory_percentage(usage, limit)

                if memory_percentage and memory_percentage >= self.memory_threshold:
                    self.logger.critical(
                        'MEMORY PRESSURE DETECTED: Unable to connect to database for scheduled tasks likely due to OOM conditions.\n'
                        f'Current memory usage: {memory_percentage:.2f}% ({self._format_bytes(usage)}/{self._format_bytes(limit)})\n'
                        'Retrying...'
                    )
                else:
                    self.logger.warning('Unable to connect to database for scheduled tasks due to connection issues. Retrying...')
                
                return False   

        return True


#Simpler Django-Q2 filter (unused)
class DjangoQFilter_simple(logging.Filter):
    def __init__(self):
        super().__init__()
        #Instantiate django-q logger
        self.logger = logging.getLogger('django-q')

    def filter(self, record):        
        db_error_patterns = [
                'name or service not known',
                'failed to pull task from broker',
                'temporary failure in name resolution', 
                'reincarnated pusher',
            ]
        
        if hasattr(record, 'getMessage'):
            message = record.getMessage().lower()
            
            if any(pattern in message for pattern in db_error_patterns):
                self.logger.warning('Unable to connect to database for scheduled tasks due to connection issues. Retrying...')
                return False   
                                            
        return True

