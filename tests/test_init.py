from unittest import TestCase

from howitz import create_app


class TestCreateApp(TestCase):

    def test_create_app_should_succeed(self):
        try:
            create_app()
        except Exception as e:
            self.fail('Raised an exception: {e}')
            raise
