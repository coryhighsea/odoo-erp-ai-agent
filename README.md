#setup and install
#It runs in WSL with docker-compose

sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable --now docker

#initially docker in wsl didn't work but after these commands it worked
getent group docker
sudo usermod -aG docker $USER
newgrp docker

# start server
docker-compose up -d

# to shutdown the server
docker-compose down

#also did
docker-compose build ai_agent

# start and stopping, less hard start and stop than down and up -d
docker-compose stop
docker-compose start

# shutdown and delete the database for a bigger restart
docker-compose down -v



#need to provide own anthropic api key or use what llm api service you have and implement in the app.py