# PakVel

PakVel is a mobile app that connects travelers with local brokers across Pakistan to plan and book trips. Travelers can browse broker itineraries, book self-guided trips, chat directly with brokers in real time, check the weather for their destination, and get suggestions from a built-in AI travel assistant. Brokers get their own dashboard to manage listings, respond to booking requests, and track their trips.

---

## Repository structure

```
pakvel/
├── pakvel_backend/     # FastAPI backend, MongoDB, AI assistant
└── pakvel_frontend/    # React Native (Expo) mobile app
```

---

## What it does

- Travelers can search for brokers, view their itineraries, and book trips either through a broker or on their own.
- Brokers manage a marketplace of itineraries, verify their profile, and respond to incoming booking requests from a dedicated dashboard.
- Travelers and brokers chat directly inside the app once a trip is booked, using CometChat for real-time messaging.
- A weather module shows current conditions for a trip's destination.
- Reviews let travelers rate brokers after a trip.
- An AI assistant, built on a retrieval pipeline over a curated dataset of travel spots in Pakistan, answers travel questions and suggests places based on budget and timing.
- A background scheduler automatically updates trip statuses (e.g. marking trips as completed) without manual input.

---

## Tech stack

**Backend**
- FastAPI (Python)
- MongoDB (via Motor, async driver)
- Groq + LangChain for the AI travel assistant
- FAISS for vector search over the travel dataset
- APScheduler for background jobs
- CometChat for messaging
- JWT-based authentication

**Frontend**
- React Native with Expo Router
- TypeScript
- React Navigation
- CometChat SDK for in-app chat
- Axios for API calls

---

## Getting started

### Backend

```bash
cd pakvel_backend
pip install -r requirements.txt
```

Create a `.env` file in `pakvel_backend/` with your own values:

```
MONGO_URI=your_mongodb_connection_string
GROQ_API_KEY=your_groq_api_key
JWT_SECRET=your_jwt_secret
COMETCHAT_APP_ID=your_cometchat_app_id
COMETCHAT_API_KEY=your_cometchat_api_key
WEATHER_API_KEY=your_weather_api_key
```

Run the server:

```bash
python -m app.run
```

The API will be available at `http://localhost:8000`. You can check `http://localhost:8000/ping` to confirm it's running.

### Frontend

```bash
cd pakvel_frontend
npm install
npx expo start
```

Update the API base URL in `app/api/axiosInstance.ts` to point to wherever your backend is running.

---

## Project layout

**Backend**
```
pakvel_backend/
└── app/
    ├── routes/         # auth, broker, traveler, trip, review, weather, chat endpoints
    ├── models/         # user and broker data models
    ├── db/              # MongoDB connection and indexing
    ├── core/            # security (auth/JWT) and the trip status scheduler
    ├── services/        # CometChat integration, notifications, weather monitoring
    ├── LLM/             # AI travel assistant (retrieval + generation pipeline)
    └── run.py           # app entry point
```

**Frontend**
```
pakvel_frontend/
└── app/
    ├── (tabs)/              # traveler-facing tabs
    ├── (broker-tabs)/       # broker dashboard tabs
    ├── ai/                  # AI assistant screen
    ├── chat/                # trip chat screen
    ├── api/                 # axios setup
    ├── login.tsx, register.tsx
    ├── createTrip.tsx, selfbook.tsx
    └── broker*.tsx          # broker itinerary and profile screens
```

---

## Notes

Both `.env` files and any generated files (vector index, virtual environments, build artifacts) are excluded from version control. You'll need to supply your own API keys and connection strings to run the project locally.

## Author

**Ayesha Ahmed**
