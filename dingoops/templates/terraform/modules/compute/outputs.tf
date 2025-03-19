output "k8s_master_ips" {
  value = concat(openstack_compute_instance_v2.k8s_master.*, openstack_compute_instance_v2.k8s_node.*)
}
