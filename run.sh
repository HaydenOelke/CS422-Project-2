# Run Script - run.sh
# Purpose: This script is used to execute and start the MealTrack application using Docker Compose.
# Authors: Kobe Pane
# Date Created: 05/26/26

echo "Starting MongoDB in the background..."
docker compose up --build -d mongo

echo "Starting Flask (logs below)..."
docker compose up --build flask
docker compose logs -f flask