echo "Starting MongoDB in the background..."
docker compose up -d mongo

echo "Starting Flask (logs below)..."
docker compose up flask
docker compose logs -f flask