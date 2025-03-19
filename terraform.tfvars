
            cluster_name = "test-cluster"
            ssh_user = "ubuntu"
            admin_network_id = "net-123"
            bus_network_id = "net-123"
            use_existing_network = true
            subnet_cidr =  "10.0.0.0/24"
            router_id =  "router-123"
            floatingip_pool =  "physnet2"
            external_net = "a88e60f1-6bd1-4846-8b96-cbd309c1ebd4"
            admin_subnet_id = "subnet-123"
            bus_subnet_id = "subnet-123"
              k8s_masters = k8s_masters = {
  "master-1" = {
    az = "nova"
    flavor = "m1.large"
    floating_ip = true
    etcd = true
  }
}
  k8s_nodes = k8s_nodes = {
  "node-1" = {
    az = "nova"
    flavor = "m1.medium"
    floating_ip = false
    etcd = false
  }
  "node-2" = {
    az = "nova"
    flavor = "m1.medium"
    floating_ip = false
    etcd = false
  }
}
