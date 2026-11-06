# Networking

- Shared VPC: host project owns networks/subnets; service projects consume. Subnet IDs and secondary range names are inputs, never constructed from strings that embed environment names.
- Subnets: `private_ip_google_access = true`; flow logs on (sampling from a variable); secondary ranges named for pods/services and passed to GKE by name.
- Firewall: no `0.0.0.0/0` ingress except via load balancer health-check ranges, which come from a variable/local list. Prefer target service accounts over network tags. Log config on for deny rules.
- Egress: Cloud NAT per region with logging on errors; explicit egress deny + allow rules where the org requires them.
- Private access to managed services through Private Service Connect or Private Service Access ranges declared as inputs.
- DNS: private zones bound to the right networks; record TTLs from variables; no hard-coded IPs.
- Changes to `google_compute_network`, subnet CIDRs, or secondary ranges usually force replacement: always check the plan for replace before merging.
