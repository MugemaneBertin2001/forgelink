# ─── OCI Authentication ───────────────────────────────────────────────
variable "tenancy_ocid" {
  description = "OCID of your OCI tenancy"
  type        = string
  sensitive   = true
}

variable "user_ocid" {
  description = "OCID of the OCI user"
  type        = string
  sensitive   = true
}

variable "fingerprint" {
  description = "Fingerprint of the OCI API signing key"
  type        = string
}

variable "private_key_path" {
  description = "Path to the OCI API private key"
  type        = string
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  description = "OCI region (pick one close to your audience)"
  type        = string
  default     = "eu-frankfurt-1"
}

variable "compartment_ocid" {
  description = "OCID of the compartment to create resources in"
  type        = string
}

# ─── Instance Configuration ──────────────────────────────────────────
variable "instance_name" {
  description = "Display name for the VM"
  type        = string
  default     = "forgelink"
}

variable "instance_shape" {
  description = "VM shape (ARM64 free tier)"
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "instance_ocpus" {
  description = "Number of OCPUs (max 4 for free tier)"
  type        = number
  default     = 4
}

variable "instance_memory_gb" {
  description = "Memory in GB (max 24 for free tier)"
  type        = number
  default     = 24
}

variable "boot_volume_size_gb" {
  description = "Boot volume size in GB (max 200 free)"
  type        = number
  default     = 100
}

# ─── SSH ─────────────────────────────────────────────────────────────
variable "ssh_public_key_path" {
  description = "Path to SSH public key for instance access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

# ─── Network ─────────────────────────────────────────────────────────
variable "vcn_cidr" {
  description = "CIDR block for the VCN"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "admin_ssh_cidr" {
  description = "CIDR to allow SSH from (0.0.0.0/0 for anywhere, or your IP/32)"
  type        = string
  default     = "0.0.0.0/0"
}
