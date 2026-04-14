output "instance_public_ip" {
  description = "Public IP of the ForgeLink server"
  value       = oci_core_instance.forgelink.public_ip
}

output "instance_id" {
  description = "OCID of the instance"
  value       = oci_core_instance.forgelink.id
}

output "ssh_command" {
  description = "SSH into the server"
  value       = "ssh ubuntu@${oci_core_instance.forgelink.public_ip}"
}

output "forgelink_api_url" {
  description = "ForgeLink API URL"
  value       = "http://${oci_core_instance.forgelink.public_ip}:30080"
}

output "forgelink_idp_url" {
  description = "ForgeLink IDP URL"
  value       = "http://${oci_core_instance.forgelink.public_ip}:30081"
}

output "argocd_url" {
  description = "ArgoCD dashboard URL"
  value       = "https://${oci_core_instance.forgelink.public_ip}:30443"
}

output "ansible_command" {
  description = "Deploy ForgeLink with Ansible"
  value       = "cd ../ansible && ansible-playbook playbooks/site.yml --limit cloud -e ansible_host=${oci_core_instance.forgelink.public_ip}"
}
