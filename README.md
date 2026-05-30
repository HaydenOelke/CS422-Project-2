# CS422-Project-2
CS 422 Project 2 - Rayna Fisher, Hayden Oelke, Kobe Pane, Caeleb Renner


## System Overview

MealTrack is a web-based meal points tracking and budgeting system for University of Oregon students. It allows users to:

- Select their residential meal plan and set a weekly points budget
- Track meal purchases and see total points spent
- View remaining points and average points to use per day
- Get tips and tricks for staying within budget
- Upload meal options via CSV (admin/teammate feature)
- View purchase history and manage past purchases

The backend is built with Flask and MongoDB, and the frontend uses Jinja2 templates for a modern, responsive UI. The system is containerized with Docker for easy deployment and development.


## Installation & Setup

### Prerequisites
- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/) installed
- (Optional for local run) Python 3.11 and pip

### Running with Docker (Recommended)
1. Ensure the Docker daemon or Docker Desktop is running
2. Open a terminal in the project root ('CS422-Project-2') directory.
3. Build and start the containers:
Execute the 'run.sh' script. For example:
	```sh
	bash run.sh
	```

Or manually:
	```sh
	docker-compose up --build
	```

3. Open a web browser application and enter the following url:

[http://127.0.0.1:8080/](http://127.0.0.1:8080/)

or alternatively:

[http://localhost:8080](http://localhost:8080)

### Running Locally (Without Docker)
1. Open a terminal in the project root ('CS422-Project-2') directory.
2. Install Python dependencies:
	```sh
	pip install -r app/requirements.txt
	```
3. Make sure MongoDB is running locally (default: `mongodb://localhost:27017/mealtrack`).
4. Start the Flask app:
	```sh
	python app/app.py
	```
5. Open a web browser application and enter the following url:

[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

or alternatively:

[http://localhost:5000](http://localhost:5000)

---
For any issues, check your Python, Docker, and MongoDB installations.

