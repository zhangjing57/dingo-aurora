import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import subprocess
import time
from celery_api.workers import create_infrastructure, create_cluster, ClusterTFVarsObject
from api.model.cluster import ClusterObject, NodeConfigObject, NetworkConfigObject


class TestCreateCluster(unittest.TestCase):
  def setUp(self):
    # Setup test data
    self.cluster_tf_dict = {
      'id': 'test-123',
      'cluster_name': 'dsy-cluster',
      'image': 'ubuntu-2204-dsy',
      'k8s_masters': {'master1': {'flavor': '1', 'etcd': True, 'floating_ip': True,'user': 'root', 'password': 'daz3502'}},
      'k8s_nodes': {'worker1': {'flavor': '1','floating_ip': False,'etcd': False,'user': 'root', 'password': 'daz3502'}, 'worker2': {'flavor': '1','floating_ip': True,'etcd': False,'user': 'root', 'password': 'daz3502'}},
      'admin_subnet_id': 'c8b2c4df-7745-4028-acbd-333bc450a5be',
      'admin_network_id': '4700f790-0a34-4ca2-a53d-f1438568f8ff',
      'bus_network_id': 'f0f21356-858d-4c1e-b58b-71238bc3c23c',
      'bus_subnet_id': '438b7357-6a9a-4d93-993d-f73ce2a5d803',
      'auth_type': 'key', 
      'ssh_user': 'root', 
      'password': 'daz3502',
      'use_existing_network': True,
      'external_net': 'a88e60f1-6bd1-4846-8b96-cbd309c1ebd4',
      'floatingip_pool': 'physnet2',
      "number_of_etcd": 0,

      "number_of_k8s_masters": 0,

      "number_of_k8s_masters_no_etcd": 0,

      "number_of_k8s_masters_no_floating_ip": 0,

      "number_of_k8s_masters_no_floating_ip_no_etcd": 0,
      "number_of_k8s_nodes": 0,

      "number_of_k8s_nodes_no_floating_ip": 0
    }
    
    self.cluster_dict = {
      'id': 'test-123',
      'name': 'dsy-cluster',
      'node_config': [
        {'role': 'master', 'type': 'vm', 'flavor': '1', 'count': 1, 
         'image': 'ubuntu-2204-dsy', 'auth_type': 'password', 'user': 'root', 'password': 'daz3502'},
        {'role': 'worker', 'type': 'vm', 'flavor': '1', 'count': 2, 
         'image': 'ubuntu-2204-dsy', 'auth_type': 'password', 'user': 'root', 'password': 'daz3502'},
      ],
      'network_config': {
        'admin_network_id': '4700f790-0a34-4ca2-a53d-f1438568f8ff',
        'svc_cidr': '10.0.0.0/24',
        'router_id': 'router-123',
        'admin_subnet_id': 'c8b2c4df-7745-4028-acbd-333bc450a5be',
        'bus_network_id': 'f0f21356-858d-4c1e-b58b-71238bc3c23c',
        'bus_subnet_id': '438b7357-6a9a-4d93-993d-f73ce2a5d803'
      }
    }


  def test_create_cluster_success(self):

                #调用celery_app项目下的work.py中的create_cluster方法
    # Test execution
    create_cluster(self.cluster_tf_dict, self.cluster_dict)
  

  @patch('celery_api.workers.current_task')
  @patch('celery_api.workers.create_infrastructure')
  @patch('celery_api.workers.deploy_kubernetes')
  @patch('celery_api.workers.subprocess.run')
  @patch('celery_api.workers.Session')
  def test_create_cluster_terraform_failure(self, mock_session, mock_run, mock_deploy_k8s, 
                       mock_create_infra, mock_current_task):
    # Setup mocks to simulate Terraform failure
    mock_current_task.id = "task-123"
    mock_create_infra.return_value = False
    
    # Test execution and verify exception
    with self.assertRaises(Exception) as context:
      create_cluster(self.cluster_tf_dict, self.cluster_dict)
    
    self.assertIn("Terraform infrastructure creation failed", str(context.exception))
    mock_create_infra.assert_called_once()
    mock_deploy_k8s.assert_not_called()

  @patch('celery_api.workers.current_task')
  @patch('celery_api.workers.create_infrastructure')
  @patch('celery_api.workers.deploy_kubernetes')
  @patch('celery_api.workers.subprocess.run')
  @patch('celery_api.workers.Session')
  def test_create_cluster_inventory_generation_failure(self, mock_session, mock_run, mock_deploy_k8s, 
                             mock_create_infra, mock_current_task):
    # Setup mocks
    mock_current_task.id = "task-123"
    mock_create_infra.return_value = True
    
    # Mock inventory generation failure
    mock_run.side_effect = [
      MagicMock(returncode=0),  # cp command succeeds
      MagicMock(returncode=1)   # host --list command fails
    ]
    
    # Test execution and verify exception
    with self.assertRaises(Exception) as context:
      create_cluster(self.cluster_tf_dict, self.cluster_dict)
    
    self.assertIn("Error generating Ansible inventory", str(context.exception))
    mock_create_infra.assert_called_once()
    mock_deploy_k8s.assert_not_called()

  @patch('celery_api.workers.current_task')
  @patch('celery_api.workers.create_infrastructure')
  @patch('celery_api.workers.deploy_kubernetes')
  @patch('celery_api.workers.time.sleep')
  @patch('celery_api.workers.subprocess.run')
  @patch('celery_api.workers.Session')
  def test_create_cluster_connectivity_failure(self, mock_session, mock_run, mock_sleep, 
                         mock_deploy_k8s, mock_create_infra, mock_current_task):
    # Setup mocks
    mock_current_task.id = "task-123"
    mock_create_infra.return_value = True
    
    # Create mock returns for all subprocess.run calls
    # First two calls succeed (cp and inventory generation)
    # Then we have 13 failed ansible ping attempts (initial + 12 retries)
    mock_returns = [
      MagicMock(returncode=0),  # cp command succeeds
      MagicMock(returncode=0),  # host --list command succeeds
    ]
    for _ in range(13):  # All ping attempts fail
      mock_returns.append(MagicMock(returncode=1))
      
    mock_run.side_effect = mock_returns
    
    # Test execution and verify exception
    with self.assertRaises(Exception) as context:
      create_cluster(self.cluster_tf_dict, self.cluster_dict)
    
    self.assertIn("Failed to connect to all nodes", str(context.exception))
    mock_create_infra.assert_called_once()
    mock_deploy_k8s.assert_not_called()
    # Verify sleep was called for retries
    self.assertGreaterEqual(mock_sleep.call_count, 12)

  @patch('celery_api.workers.current_task')
  @patch('celery_api.workers.create_infrastructure')
  @patch('celery_api.workers.deploy_kubernetes')
  @patch('celery_api.workers.get_cluster_kubeconfig')
  @patch('celery_api.workers.subprocess.run')
  @patch('celery_api.workers.Session')
  def test_create_cluster_kubernetes_deployment_failure(self, mock_session, mock_run, mock_get_kubeconfig, 
                            mock_deploy_k8s, mock_create_infra, mock_current_task):
    # Setup mocks
    mock_current_task.id = "task-123"
    mock_create_infra.return_value = True
    mock_deploy_k8s.return_value = False
    
    # Mock successful subprocess calls for ping
    mock_run.return_value = MagicMock(returncode=0, stdout="inventory_content")
    
    # Test execution and verify exception
    with self.assertRaises(Exception) as context:
      create_cluster(self.cluster_tf_dict, self.cluster_dict)
    
    self.assertIn("Ansible kubernetes deployment failed", str(context.exception))
    mock_create_infra.assert_called_once()
    mock_deploy_k8s.assert_called_once()
    mock_get_kubeconfig.assert_not_called()

  @patch('celery_api.workers.current_task')
  @patch('celery_api.workers.create_infrastructure')
  @patch('celery_api.workers.deploy_kubernetes')
  @patch('celery_api.workers.get_cluster_kubeconfig')
  @patch('celery_api.workers.subprocess.run')
  @patch('celery_api.workers.Session')
  @patch('celery_api.workers.time')
  def test_create_cluster_timeout(self, mock_time, mock_session, mock_run, mock_get_kubeconfig, 
                  mock_deploy_k8s, mock_create_infra, mock_current_task):
    # Setup mocks
    mock_current_task.id = "task-123"
    mock_create_infra.return_value = True
    
    # Mock time to simulate timeout
    mock_time.time.side_effect = [0, 1800 + 1]  # Start time and then time after timeout
    
    # Set up run to return failure for ping
    mock_run.side_effect = [
      MagicMock(returncode=0),  # cp command succeeds
      MagicMock(returncode=0),  # host --list command succeeds
      MagicMock(returncode=1)   # ansible ping fails
    ]
    
    # Test execution and verify timeout exception
    with self.assertRaises(Exception) as context:
      create_cluster(self.cluster_tf_dict, self.cluster_dict)
    
    self.assertIn("Operation timed out", str(context.exception))
    mock_create_infra.assert_called_once()
