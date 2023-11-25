FROM ghcr.io/railwayapp/nixpacks:ubuntu-1699920194@sha256:c861ec45a7401768f59183a4a51056daf7dd26ab9a5215836c81b09725b9cbb6

# Install Python 3
RUN apt-get update && apt-get install -y python3

WORKDIR /app/

COPY . /app/.

RUN python3 server.py
