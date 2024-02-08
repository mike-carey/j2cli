import sys

# Patch basestring in for python 3 compat
try:
    basestring
except NameError:
    basestring = str

#region Parsers

def _parse_ini(data_string):
    """ INI data input format.

    data.ini:

    ```
    [nginx]
    hostname=localhost
    webroot=/var/www/project
    logs=/var/log/nginx/
    ```

    Usage:

        $ j2 config.j2 data.ini
        $ cat data.ini | j2 --format=ini config.j2
    """
    from io import StringIO

    # Override
    class MyConfigParser(ConfigParser.ConfigParser):
        def as_dict(self):
            """ Export as dict
            :rtype: dict
            """
            d = dict(self._sections)
            for k in d:
                d[k] = dict(self._defaults, **d[k])
                d[k].pop('__name__', None)
            return d

    # Parse
    ini = MyConfigParser()
    ini.readfp(ini_file_io(data_string))

    # Export
    return ini.as_dict()

def _parse_json(data_string):
    """ JSON data input format

    data.json:

    ```
    {
        "nginx":{
            "hostname": "localhost",
            "webroot": "/var/www/project",
            "logs": "/var/log/nginx/"
        }
    }
    ```

    Usage:

        $ j2 config.j2 data.json
        $ cat data.json | j2 --format=ini config.j2
    """
    return json.loads(data_string)

def _parse_yaml(data_string):
    """ YAML data input format.

    data.yaml:

    ```
    nginx:
      hostname: localhost
      webroot: /var/www/project
      logs: /var/log/nginx
    ```

    Usage:

        $ j2 config.j2 data.yml
        $ cat data.yml | j2 --format=yaml config.j2
    """
    # Loader
    try:
        # PyYAML 5.1 supports FullLoader
        Loader = yaml.FullLoader
    except AttributeError:
        # Have to use SafeLoader for older versions
        Loader = yaml.SafeLoader
    # Done
    return yaml.load(data_string, Loader=Loader)

def _parse_env(data_string):
    """ Data input from environment variables.

    Render directly from the current environment variable values:

        $ j2 config.j2

    Or alternatively, read the values from a dotenv file:

    ```
    NGINX_HOSTNAME=localhost
    NGINX_WEBROOT=/var/www/project
    NGINX_LOGS=/var/log/nginx/
    ```

    And render with:

        $ j2 config.j2 data.env
        $ env | j2 --format=env config.j2

    If you're going to pipe a dotenv file into `j2`, you'll need to use "-" as the second argument to explicitly:

        $ j2 config.j2 - < data.env
    """
    # Parse
    if isinstance(data_string, basestring):
        data = filter(
            lambda l: len(l) == 2 ,
            (
                list(map(
                    str.strip,
                    line.split('=', 1)
                ))
                for line in data_string.split("\n"))
        )
    else:
        data = data_string

    # Finish
    return data


FORMATS = {
    'ini':  _parse_ini,
    'json': _parse_json,
    'yaml': _parse_yaml,
    'env': _parse_env
}

#endregion



#region Imports

# JSON: simplejson | json
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
         del FORMATS['json']

# INI: Python 2 | Python 3
try:
    import ConfigParser
    from io import BytesIO as ini_file_io
except ImportError:
    import configparser as ConfigParser
    from io import StringIO as ini_file_io

# YAML
try:
    import yaml
except ImportError:
    del FORMATS['yaml']

#endregion

def merge(d1, d2):
    """"""
    merged = d1.copy()
    for k, v in d2.items():
        if k in d1 and isinstance(v, dict) and isinstance(d1[k], dict):
            merged[k] = merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def read_context_data(format, files, environ, import_env=None):
    """ Read context data into a dictionary
    :param format: Data format
    :type format: str
    :param files: Data file streams, or empty (for env)
    :type files: list(file)
    :param import_env: Variable name, if any, that will contain environment variables of the template.
    :type import_env: str|None
    :return: Dictionary with the context data
    :rtype: dict
    """

    # Special case: environment variables
    if format == 'env' and len(files) < 1:
        return _parse_env(environ)

    # Parse it
    if format not in FORMATS:
        raise ValueError('{0} format unavailable'.format(format))

    context = {}
    for file in files:
        # Read data string stream
        data_string = file.read()
        data = FORMATS[format](data_string)
        context = merge(context, dict(data))

    # Import environment
    if import_env is not None:
        if import_env == '':
            context.update(environ)
        else:
            context[import_env] = environ

    # Done
    return context
