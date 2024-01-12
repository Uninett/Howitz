from unittest import TestCase

from howitz import create_app


class TestCreateApp(TestCase):

    def test_create_app_should_succeed(self):
        test_config = {
            'zino': {
                'connections': {
                    'default': {
                        'server': '127.0.0.1'}
                }
            }
        }
        try:
            create_app(test_config)
        except Exception as e:
            self.fail('Raised an exception: {e}')
            raise
