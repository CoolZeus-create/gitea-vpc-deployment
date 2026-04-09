Assignment 4: Deploy Gitea in a Custom VPC with Multiple EC2 Instances
# gitea-vpc-deployment
Gitea deployment in a custom AWS VPC with nginx reverse proxy, private subnets, NAT gateway, and FastAPI audit API
Architecture Summary
This deployment builds a multi-instance architecture inside a custom AWS VPC. A public-facing nginx reverse proxy instance receives all inbound internet traffic on port 80 and forwards requests to two private backend instances based on URL path. The Gitea instance (port 3000) and the FastAPI audit/event API instance (port 5000) both reside in a private subnet with no public IP addresses, making them unreachable directly from the internet. The private instances use a NAT gateway in the public subnet to reach the internet for package installation and updates. All traffic from external users flows through the nginx reverse proxy, enforcing a clear trust boundary between public and private tiers.
---
Network Configuration Summary
VPC
VPC Name: gitea-vpc
VPC ID: vpc-049d28ea608bb75b5
CIDR Block: 10.0.0.0/16
Subnets
Name	CIDR	Type	Subnet ID
gitea-public-subnet	10.0.1.0/24	Public	subnet-06692ebb9763ccf69
gitea-private-subnet	10.0.2.0/24	Private	subnet-0dfe5fde1e5e69f9a
Internet Gateway
Name: gitea-igw
ID: igw-0d6e09c4dd2e69c7c
Attached to: gitea-vpc
NAT Gateway
Name: gitea-nat
ID: nat-06384adcd709ef93
Location: gitea-public-subnet
Public IP: 23.23.254.234
Route Tables
Name	Subnet	Destination	Target
gitea-public-rt	gitea-public-subnet	0.0.0.0/0	igw-0d6e09c4dd2e69c7c
gitea-private-rt	gitea-private-subnet	0.0.0.0/0	nat-06384adcd709ef93
Security Groups
gitea-public-sg (nginx reverse proxy)
Port	Protocol	Source	Purpose
80	TCP	0.0.0.0/0	HTTP web traffic
22	TCP	My IP only	SSH admin access
gitea-private-sg (Gitea + API backends)
Port	Protocol	Source	Purpose
3000	TCP	gitea-public-sg	Gitea web traffic from proxy
5000	TCP	gitea-public-sg	API traffic from proxy
22	TCP	gitea-public-sg	SSH via jump host only
EC2 Instances
Name	Private IP	Public IP	Subnet
gitea-nginx-proxy	10.0.1.101	13.223.85.24	gitea-public-subnet
gitea-backend	10.0.2.216	None	gitea-private-subnet
gitea-api	10.0.2.218	None	gitea-private-subnet
---
URL Path Routing Design (nginx)
Path	Backend	Port
/	Gitea (10.0.2.216)	3000
/api/	Audit/Event API (10.0.2.218)	5000
---
Deployment Instructions
Part 1: Network Setup
Create custom VPC (`10.0.0.0/16`) using VPC only workflow
Create public subnet (`10.0.1.0/24`) and private subnet (`10.0.2.0/24`)
Create and attach Internet Gateway to VPC
Create NAT Gateway in public subnet with Elastic IP
Create public route table: `0.0.0.0/0 → IGW`, associate with public subnet
Create private route table: `0.0.0.0/0 → NAT`, associate with private subnet
Part 2: Security Groups
Create `gitea-public-sg`: allow TCP 80 from anywhere, TCP 22 from My IP
Create `gitea-private-sg`: allow TCP 3000, 5000, 22 from `gitea-public-sg`
Part 3: EC2 Instances
Launch `gitea-nginx-proxy` in public subnet with public IP, using `gitea-public-sg`
Launch `gitea-backend` in private subnet, no public IP, using `gitea-private-sg`
Launch `gitea-api` in private subnet, no public IP, using `gitea-private-sg`
Part 4: Software Installation
On nginx proxy (13.223.85.24):
```bash
sudo apt update
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```
On gitea-backend (10.0.2.216) via jump host:
```bash
sudo apt update
sudo apt install docker.io -y
sudo systemctl enable docker
sudo docker run -d --name gitea -p 3000:3000 -v \~/data:/data --restart always gitea/gitea:latest
```
On gitea-api (10.0.2.218) via jump host:
```bash
sudo apt update
sudo apt install python3-pip python3-venv -y
mkdir \~/audit-api \&\& cd \~/audit-api
python3 -m venv venv \&\& source venv/bin/activate
pip install fastapi uvicorn
# Create main.py (see main.py in this repo)
sudo systemctl enable audit-api
sudo systemctl start audit-api
```
Configure nginx reverse proxy:
```bash
sudo nano /etc/nginx/sites-available/gitea-proxy
sudo ln -s /etc/nginx/sites-available/gitea-proxy /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```
Backend Access (Jump Host Pattern)
Private instances have no public IP. Access them via the nginx proxy as a jump host:
```bash
# From local machine, SSH to proxy
ssh -i gitea-key.pem ubuntu@13.223.85.24

# From proxy, SSH to private instances
ssh -i \~/.ssh/gitea-key.pem ubuntu@10.0.2.216  # gitea-backend
ssh -i \~/.ssh/gitea-key.pem ubuntu@10.0.2.218  # gitea-api
```
---
Connectivity Verification
```bash
# From nginx proxy to Gitea backend
curl -I http://10.0.2.216:3000

# From nginx proxy to API backend
curl http://10.0.2.218:5000/api/health

# POST event through proxy
curl -X POST http://localhost/api/events \\
  -H "Content-Type: application/json" \\
  -d '{"event\_type": "push", "repo": "team1/project", "user": "alice"}'

# Verify events stored
curl http://localhost/api/events

# Direct backend access from internet - BLOCKED (ERR\_CONNECTION\_TIMED\_OUT)
# http://10.0.2.216:3000 - not reachable
# http://10.0.2.218:5000 - not reachable
```
