output "ec2_public_ip" {
  description = "EC2 public IP (for SSH)"
  value       = aws_instance.app.public_ip
}

output "ec2_public_dns" {
  description = "EC2 public DNS"
  value       = aws_instance.app.public_dns
}

output "cloudfront_url" {
  description = "HTTPS URL — use this for the submission"
  value       = "https://${aws_cloudfront_distribution.app.domain_name}"
}

output "app_direct_url" {
  description = "Direct HTTP (backup)"
  value       = "http://${aws_instance.app.public_ip}"
}
