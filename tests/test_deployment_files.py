import os
import unittest
import yaml

class DeploymentFilesTestCase(unittest.TestCase):
    def test_dockerfile_healthcheck(self):
        path = os.path.join('docker', 'Dockerfile')
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = f.read()
        self.assertIn('HEALTHCHECK', data)
        self.assertIn('uvicorn', data)

    def test_compose_file(self):
        path = 'docker-compose.yml'
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            config = yaml.safe_load(f)
        self.assertIn('services', config)
        self.assertIn('mcp', config['services'])
        self.assertEqual(config['services']['mcp']['ports'], ['8000:8000'])

    def test_systemd_service(self):
        path = os.path.join('ops', 'mcp.service')
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            data = f.read()
        self.assertIn('ExecStart', data)

if __name__ == '__main__':
    unittest.main()
