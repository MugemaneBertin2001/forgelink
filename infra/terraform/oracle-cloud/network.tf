# ─── VCN ──────────────────────────────────────────────────────────────
resource "oci_core_vcn" "forgelink" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = [var.vcn_cidr]
  display_name   = "${var.instance_name}-vcn"
  dns_label      = "forgelink"
}

# ─── Internet Gateway ────────────────────────────────────────────────
resource "oci_core_internet_gateway" "forgelink" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.forgelink.id
  display_name   = "${var.instance_name}-igw"
  enabled        = true
}

# ─── Route Table ─────────────────────────────────────────────────────
resource "oci_core_route_table" "forgelink" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.forgelink.id
  display_name   = "${var.instance_name}-rt"

  route_rules {
    network_entity_id = oci_core_internet_gateway.forgelink.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
}

# ─── Security List ───────────────────────────────────────────────────
resource "oci_core_security_list" "forgelink" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.forgelink.id
  display_name   = "${var.instance_name}-sl"

  # Allow all egress
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }

  # SSH
  ingress_security_rules {
    protocol = "6" # TCP
    source   = var.admin_ssh_cidr
    tcp_options {
      min = 22
      max = 22
    }
  }

  # HTTP
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  # HTTPS
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }

  # ForgeLink API (NodePort)
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 30080
      max = 30080
    }
  }

  # ForgeLink IDP (NodePort)
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 30081
      max = 30081
    }
  }

  # ArgoCD (NodePort)
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 30443
      max = 30443
    }
  }

  # MQTT (EMQX)
  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 1883
      max = 1883
    }
  }

  # ICMP (ping)
  ingress_security_rules {
    protocol = 1 # ICMP
    source   = "0.0.0.0/0"
    icmp_options {
      type = 3
      code = 4
    }
  }

  ingress_security_rules {
    protocol = 1
    source   = var.vcn_cidr
    icmp_options {
      type = 3
    }
  }
}

# ─── Subnet ──────────────────────────────────────────────────────────
resource "oci_core_subnet" "forgelink" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.forgelink.id
  cidr_block        = var.subnet_cidr
  display_name      = "${var.instance_name}-subnet"
  dns_label         = "forgelink"
  route_table_id    = oci_core_route_table.forgelink.id
  security_list_ids = [oci_core_security_list.forgelink.id]
}
