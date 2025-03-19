import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess
from celery_api.workers import create_infrastructure
from api.model.cluster import ClusterObject, NodeConfigObject, NetworkConfigObject

class TestCreateInfrastructure(unittest.TestCase):
  def setUp(self):
    self.cluster = ClusterObject(
      id="test-123",
      name="test-cluster",
      node_count=3,
      node_config=[
        NodeConfigObject(role="master", type="vm", flavor_id="m1.large",count=1, image="ubuntu-20.04"),
        NodeConfigObject(role="worker", type="vm", flavor_id="m1.medium",count=2,image="ubuntu-20.04")
      ],
      network_config=NetworkConfigObject(
        network_id="net-123",
        pod_cidr="10.0.0.0/24",
        router_id="router-123",
        admin_subnet_id="subnet-123"
      )
    )


  def test_Testcreate_infrastructure_success(self):
    
    result = create_infrastructure(self.cluster)
    
    self.assertTrue(result)

  @patch('subprocess.run')
  def test_create_infrastructure_failure(self, mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'terraform')
    
    result = create_infrastructure(self.cluster)
    
    self.assertFalse(result)

if __name__ == '__main__':
  unittest.main()