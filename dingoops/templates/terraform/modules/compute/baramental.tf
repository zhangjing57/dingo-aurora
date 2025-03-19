data "openstack_images_image_v2" "vm_image" {
  count = var.image_uuid == "" ? 1 : 0
  most_recent = true
  name = var.image
}


data "cloudinit_config" "cloudinit" {
  part {
    content_type =  "text/cloud-config"
    content = templatefile("${path.module}/templates/cloudinit.yaml.tmpl", {
      extra_partitions = [],
      netplan_critical_dhcp_interface = ""
      bus_cidr = var.bus_cidr
    })
  }
}

data "openstack_networking_network_v2" "k8s_admin_network" {
  count = var.use_existing_network ? 1 : 0
  name  = var.admin_network_name
}

data "openstack_networking_network_v2" "bus_k8s_network" {
  count = var.use_existing_network ? 1 : 0
  name  = var.bus_network_name
}

resource "openstack_compute_keypair_v2" "k8s" {
  name       = "kubernetes-${var.cluster_name}"
  public_key = chomp(file(var.public_key_path))
}

locals {

# Image uuid
  image_to_use_node = var.image_uuid != "" ? var.image_uuid : data.openstack_images_image_v2.vm_image[0].id

# image_master uuidimage_gfs_uuid
  image_to_use_master = var.image_master_uuid != "" ? var.image_master_uuid : var.image_uuid != "" ? var.image_uuid : data.openstack_images_image_v2.image_master[0].id

  k8s_baremetals_settings = {
    for name, node in var.k8s_nodes :
      name => {
        "use_local_disk" = (node.root_volume_size_in_gb != null ? node.root_volume_size_in_gb : var.node_root_volume_size_in_gb) == 0,
        "image_id"       = node.image_id != null ? node.image_id : local.image_to_use_node,
        "volume_size"    = node.root_volume_size_in_gb != null ? node.root_volume_size_in_gb : var.node_root_volume_size_in_gb,
        "volume_type"    = node.volume_type != null ? node.volume_type : var.node_volume_type,
        "admin_network_id"     = node.network_id != null ? node.network_id : (var.use_existing_network ? data.openstack_networking_network_v2.k8s_admin_network[0].id : var.admin_network_id)
        "bus_network_id"     = node.network_id != null ? node.network_id : (var.use_existing_network ? data.openstack_networking_network_v2.bus_k8s_network[0].id : var.bus_network_id)
        #"server_group"   = node.server_group != null ? [openstack_compute_servergroup_v2.k8s_node_additional[node.server_group].id] : (var.node_server_group_policy != ""  ? [openstack_compute_servergroup_v2.k8s_node[0].id] : [])
      }
  }
}

resource "openstack_networking_port_v2" "k8s_admin_baremetals_port" {
  for_each              = var.k8s_baremetals : {}
  name                  = "${var.cluster_name}-k8s-${each.key}-admin"
  network_id            = var.use_existing_network ? data.openstack_networking_network_v2.k8s_admin_network[0].id : var.admin_network_id
  admin_state_up        = "true"
  dynamic "fixed_ip" {
    for_each = var.private_subnet_id == "" ? [] : [true]
    content {
      subnet_id = var.private_subnet_id
    }
  }

  lifecycle {
    ignore_changes = [ allowed_address_pairs ]
  }

  depends_on = [
    var.network_router_id
  ]
}

resource "openstack_networking_port_v2" "k8s_business_baremetals_port" {
  for_each              = var.k8s_baremetals : {}
  name                  = "${var.cluster_name}-k8s-${each.key}-business"
  network_id            = var.admin_network_id
  admin_state_up        = "true"
  dynamic "fixed_ip" {
    for_each = var.private_subnet_id == "" ? [] : [true]
    content {
      subnet_id = var.private_subnet_id
    }
  }

  lifecycle {
    ignore_changes = [ allowed_address_pairs ]
  }

  depends_on = [
    var.network_router_id
  ]
}

resource "openstack_networking_trunk_v2" "trunk_barementals" {
  name           = "${var.cluster_name}-${count.index + 1}-baremental"
  count          = var.number_of_k8s_masters
  admin_state_up = "true"
  port_id        = element(openstack_networking_port_v2.k8s_business_baremetals_port.*.id, count.index)

}

resource "openstack_compute_instance_v2" "k8s_barementals" {
  for_each          = var.k8s_masters
  name              = "${var.cluster_name}-k8s-${each.key}"
  availability_zone = each.value.az
  image_id          = local.k8s_masters_settings[each.key].use_local_disk ? local.k8s_masters_settings[each.key].image_id : null
  flavor_id         = each.value.flavor
  key_pair          = openstack_compute_keypair_v2.k8s.name

  dynamic "block_device" {
    for_each = !local.k8s_masters_settings[each.key].use_local_disk ? [local.k8s_masters_settings[each.key].image_id] : []
    content {
      uuid                  = block_device.value
      source_type           = "image"
      volume_size           = local.k8s_masters_settings[each.key].volume_size
      volume_type           = local.k8s_masters_settings[each.key].volume_type
      boot_index            = 0
      destination_type      = "volume"
      delete_on_termination = true
    }
  }

  network {
    port = element(openstack_networking_port_v2.k8s_admin_baremetals_port.*.id, count.index)
  }
  network {
    port = element(openstack_networking_port_v2.k8s_business_baremetals_port.*.id, count.index)
  }

  dynamic "scheduler_hints" {
    for_each = var.master_server_group_policy != "" ? [openstack_compute_servergroup_v2.k8s_master[0]] : []
    content {
      group = openstack_compute_servergroup_v2.k8s_master[0].id
    }
  }

  metadata = {
    ssh_user         = var.ssh_user
    kubespray_groups = "%{if each.value.etcd == true}etcd,%{endif}kube_control_plane,${var.supplementary_master_groups},k8s_cluster%{if each.value.floating_ip == false},no_floating%{endif}"
    depends_on       = var.network_router_id
    use_access_ip    = var.use_access_ip
  }

  provisioner "local-exec" {
    command = "%{if each.value.floating_ip}sed s/USER/${var.ssh_user}/ ${path.module}/ansible_bastion_template.txt | sed s/BASTION_ADDRESS/${element(concat(var.bastion_fips, [for key, value in var.k8s_masters_fips : value.address]), 0)}/ > ${var.group_vars_path}/no_floating.yml%{else}true%{endif}"
  }
}
## 配置k8snode节点相关





