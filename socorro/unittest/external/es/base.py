# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch
import mock
import os
from elasticsearch.helpers import bulk

from configman import ConfigurationManager

from socorro.middleware.middleware_app import MiddlewareApp
from socorro.unittest.testbase import TestCase


DEFAULT_VALUES = {
    'elasticsearch.elasticsearch_class': (
        'socorro.external.es.connection_context.ConnectionContext'
    ),
    'resource.elasticsearch.elasticsearch_default_index': (
        'socorro_integration_test'
    ),
    'resource.elasticsearch.elasticsearch_index': (
        'socorro_integration_test_reports'
    ),
    'resource.elasticsearch.elasticsearch_timeout': 5,
}


CRON_JOB_EXTA_VALUES = {
    'resource.elasticsearch.backoff_delays': [1],
    'resource.postgresql.database_name': 'socorro_integration_test',
}


SUPERSEARCH_FIELDS = {
    'signature': {
        'name': 'signature',
        'in_database_name': 'signature',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': True,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'multi_field',
            'fields': {
                'signature': {
                    'type': 'string'
                },
                'full': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    },
    'product': {
        'name': 'product',
        'in_database_name': 'product',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': True,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'multi_field',
            'fields': {
                'product': {
                    'type': 'string'
                },
                'full': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    },
    'version': {
        'name': 'version',
        'in_database_name': 'version',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string',
            'analyzer': 'keyword'
        },
    },
    'platform': {
        'name': 'platform',
        'in_database_name': 'os_name',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': True,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'multi_field',
            'fields': {
                'os_name': {
                    'type': 'string'
                },
                'full': {
                    'type': 'string',
                    'index': 'not_analyzed'
                }
            }
        },
    },
    'release_channel': {
        'name': 'release_channel',
        'in_database_name': 'release_channel',
        'data_validation_type': 'enum',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string'
        },
    },
    'date': {
        'name': 'date',
        'in_database_name': 'date_processed',
        'data_validation_type': 'datetime',
        'query_type': 'date',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'date',
            'format': 'yyyy-MM-dd\'T\'HH:mm:ssZZ||yyyy-MM-dd\'T\'HH:mm:ss.SSSSSSZZ'
        },
    },
    'address': {
        'name': 'address',
        'in_database_name': 'address',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string'
        },
    },
    'build_id': {
        'name': 'build_id',
        'in_database_name': 'build',
        'data_validation_type': 'int',
        'query_type': 'number',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'long'
        },
    },
    'reason': {
        'name': 'reason',
        'in_database_name': 'reason',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string'
        },
    },
    'email': {
        'name': 'email',
        'in_database_name': 'email',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': ['crashstats.view_pii'],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string',
            'analyzer': 'keyword'
        },
    },
    'url': {
        'name': 'url',
        'in_database_name': 'url',
        'data_validation_type': 'str',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_choices': None,
        'permissions_needed': ['crashstats.view_pii'],
        'default_value': None,
        'has_full_version': False,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
        'storage_mapping': {
            'type': 'string',
            'analyzer': 'keyword'
        },
    },
    'uuid': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'uuid',
        'is_exposed': False,
        'is_mandatory': False,
        'is_returned': False,
        'name': 'uuid',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'process_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': [
            'any', 'browser', 'plugin', 'content', 'all'
        ],
        'has_full_version': False,
        'in_database_name': 'process_type',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'process_type',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'user_comments': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': True,
        'in_database_name': 'user_comments',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'user_comments',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                },
                'user_comments': {
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'accessibility': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'Accessibility',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'accessibility',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'b2g_os_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'B2G_OS_Version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'b2g_os_version',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'bios_manufacturer': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'BIOS_Manufacturer',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'bios_manufacturer',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'vendor': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'Vendor',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'vendor',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'useragent_locale': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'useragent_locale',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'useragent_locale',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'analyzer': 'keyword',
            'type': 'string'
        }
    },
    'is_garbage_collecting': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'IsGarbageCollecting',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'is_garbage_collecting',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'type': 'boolean'
        }
    },
    'available_virtual_memory': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'AvailableVirtualMemory',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'available_virtual_memory',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'install_age': {
        'data_validation_type': 'int',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'install_age',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'install_age',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'number',
        'storage_mapping': {
            'type': 'long'
        }
    },
    'plugin_filename': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': True,
        'in_database_name': 'PluginFilename',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_filename',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'PluginFilename': {
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'plugin_name': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': True,
        'in_database_name': 'PluginName',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_name',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'PluginName': {
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'plugin_version': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': True,
        'in_database_name': 'PluginVersion',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'plugin_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'fields': {
                'PluginVersion': {
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'android_model': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': True,
        'in_database_name': 'Android_Model',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'android_model',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'Android_Model': {
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'dump': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'dump',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'dump',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'index': 'not_analyzed',
            'type': 'string'
        }
    },
    'cpu_info': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': True,
        'in_database_name': 'cpu_info',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'cpu_info',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'fields': {
                'cpu_info': {
                    'analyzer': 'standard',
                    'index': 'analyzed',
                    'type': 'string'
                },
                'full': {
                    'index': 'not_analyzed',
                    'type': 'string'
                }
            },
            'type': 'multi_field'
        }
    },
    'dom_ipc_enabled': {
        'data_validation_type': 'bool',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'DOMIPCEnabled',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'dom_ipc_enabled',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'bool',
        'storage_mapping': {
            'null_value': False,
            'type': 'boolean'
        }
    },
    'app_notes': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'app_notes',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'app_notes',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'hang_type': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': [
            'any', 'crash', 'hang', 'all'
        ],
        'has_full_version': False,
        'in_database_name': 'hang_type',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'hang_type',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'short'
        }
    },
    'exploitability': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': [
            'high', 'normal', 'low', 'none', 'unknown', 'error'
        ],
        'has_full_version': False,
        'in_database_name': 'exploitability',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'exploitability',
        'namespace': 'processed_crash',
        'permissions_needed': [
            'crashstats.view_exploitability'
        ],
        'query_type': 'enum',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'platform_version': {
        'data_validation_type': 'str',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'os_version',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'platform_version',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'query_type': 'string',
        'storage_mapping': {
            'type': 'string'
        }
    },
    'fake_field': {
        'data_validation_type': 'enum',
        'default_value': None,
        'form_field_choices': None,
        'has_full_version': False,
        'in_database_name': 'fake_field',
        'is_exposed': True,
        'is_mandatory': False,
        'is_returned': True,
        'name': 'fake_field',
        'namespace': 'raw_crash',
        'permissions_needed': [],
        'query_type': 'enum',
    },
}


class ElasticsearchTestCase(TestCase):
    """Base class for Elastic Search related unit tests. """

    def __init__(self, *args, **kwargs):
        super(ElasticsearchTestCase, self).__init__(*args, **kwargs)

        self.config = self.get_mware_config()
        es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )
        with es_context() as conn:
            self.connection = conn
            self.index_client = elasticsearch.client.IndicesClient(
                self.connection
            )

    def get_tuned_config(self, sources, extra_values=None):
        if not isinstance(sources, (list, tuple)):
            sources = [sources]

        mock_logging = mock.Mock()

        config_definitions = []
        for source in sources:
            conf = source.get_required_config()
            conf.add_option('logger', default=mock_logging)
            config_definitions.append(conf)

        values_source = DEFAULT_VALUES.copy()
        values_source.update({'logger': mock_logging})
        if extra_values:
            values_source.update(extra_values)

        config_manager = ConfigurationManager(
            config_definitions,
            app_name='testapp',
            app_version='1.0',
            app_description='Elasticsearch integration tests',
            values_source_list=[os.environ, values_source],
            argv_source=[],
        )

        return config_manager.get_config()

    def get_mware_config(self):
        return self.get_tuned_config(MiddlewareApp)

    def index_super_search_fields(self, fields=None):
        if fields is None:
            fields = SUPERSEARCH_FIELDS

        es_index = self.config.elasticsearch.elasticsearch_default_index

        actions = []
        for name, field in fields.iteritems():
            action = {
                '_index': es_index,
                '_type': 'supersearch_fields',
                '_id': name,
                '_source': field,
            }
            actions.append(action)

        bulk(
            client=self.connection,
            actions=actions,
        )
        self.index_client.refresh(index=[es_index])
