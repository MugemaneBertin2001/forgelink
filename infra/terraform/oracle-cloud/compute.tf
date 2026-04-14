# ─── Get Ubuntu 22.04 ARM64 Image ────────────────────────────────────
data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = var.instance_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# ─── Availability Domain ─────────────────────────────────────────────
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# ─── Compute Instance ────────────────────────────────────────────────
resource "oci_core_instance" "forgelink" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = var.instance_name
  shape               = var.instance_shape

  shape_config {
    ocpus         = var.instance_ocpus
    memory_in_gbs = var.instance_memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_size_gb
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.forgelink.id
    display_name     = "${var.instance_name}-vnic"
    assign_public_ip = true
    hostname_label   = "forgelink"
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key_path)
    user_data = base64encode(<<-EOF
      #!/bin/bash
      hostnamectl set-hostname forgelink
      echo "forgelink" > /etc/hostname
    EOF
    )
  }

  # Prevent accidental destruction
  lifecycle {
    prevent_destroy = false
  }
}
