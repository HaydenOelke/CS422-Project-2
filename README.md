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

### Running with Docker
1. Open a terminal in the project directory.
2. Build and start the containers:
	```sh
	docker-compose up --build
	```
3. Visit [http://localhost:8080](http://localhost:8080) in your browser.

### Running Locally (Without Docker)
1. Install Python dependencies:
	```sh
	pip install -r app/requirements.txt
	```
2. Make sure MongoDB is running locally (default: `mongodb://localhost:27017/mealtrack`).
3. Start the Flask app:
	```sh
	python app/app.py
	```
4. Visit [http://localhost:5000](http://localhost:5000) in your browser.

---
For any issues, check your Python, Docker, and MongoDB installations.

