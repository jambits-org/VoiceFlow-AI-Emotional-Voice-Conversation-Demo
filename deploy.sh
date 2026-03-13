#!/bin/bash
# VoiceFlow AI — Amazon Linux 2 setup with PM2
# Run after SSH: bash deploy.sh

set -e

echo "=== Updating system ==="
sudo yum update -y

echo "=== Installing Python 3.11 + Node.js (for PM2) ==="
sudo amazon-linux-extras install python3.8 -y || true
sudo yum install -y python3 python3-pip gcc python3-devel git
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

echo "=== Installing PM2 ==="
sudo npm install -g pm2

echo "=== Cloning repo ==="
cd /home/ec2-user
git clone https://github.com/jambits-org/VoiceFlow-AI-Emotional-Voice-Conversation-Demo.git app
cd app

echo "=== Setting up Python venv ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Creating .env ==="
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-key-here
OTP_CODE=8472
MAX_ATTEMPTS=10
EOF

echo "=== Creating PM2 ecosystem file ==="
cat > ecosystem.config.js << 'PMEOF'
module.exports = {
  apps: [{
    name: "voiceflow",
    script: "/home/ec2-user/app/venv/bin/uvicorn",
    args: "main:app --host 0.0.0.0 --port 80",
    cwd: "/home/ec2-user/app",
    interpreter: "none",
    env: {
      PATH: "/home/ec2-user/app/venv/bin:" + process.env.PATH
    }
  }]
};
PMEOF

echo "=== Starting with PM2 ==="
sudo env PATH=$PATH:/usr/bin pm2 start ecosystem.config.js
sudo env PATH=$PATH:/usr/bin pm2 save
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ec2-user --hp /home/ec2-user

echo ""
echo "=== DONE ==="
echo "App running on http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "OTP: 8472"
echo ""
echo "Useful commands:"
echo "  sudo pm2 logs voiceflow"
echo "  sudo pm2 restart voiceflow"
echo "  sudo pm2 stop voiceflow"
