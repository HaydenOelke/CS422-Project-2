echo "Starting MongoDB in the background..."
docker compose up --build -d mongo

echo "Starting Flask (logs below)..."
docker compose up --build flask
docker compose logs -f flask