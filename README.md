# Finance Backend API & AI Predictor

Backend FastAPI + SQLite + JWT for database/API integration. 
The system integrates the **AI Prophet** model (Time-Series Forecasting) to predict spending and assess financial risks. Notably, the system is equipped with a "Plan B" (Graceful Degradation) - automatically falling back to a Moving Average algorithm if the AI encounters environmental errors, ensuring the App never crashes.

## 📂 Project Structure
- `main.py`: Core FastAPI server, routing, and Endpoint management.
- `ai_predictor.py`: OOP "Blackbox" Class dedicated to data processing and running the AI forecasting algorithm.
- `database.py` & `models.py`: SQLite connection configuration and ORM Models.
- `lich_su_chi_tieu.csv`: Sample raw data for AI training.

---

## ⚙️ Setup & Installation

**Step 1: Initialize and activate the Virtual Environment**
```bash
cd backend
python -m venv venv

# If your venv has Scripts (Windows CMD/PowerShell):
venv\Scripts\activate

# If your venv has bin (Mac/Linux):
source venv/bin/activate
```

**Step 2: Install dependencies**
```bash
pip install -r requirements.txt
```
*(Ensure your `requirements.txt` file includes: `fastapi`, `uvicorn`, `sqlalchemy`, `pandas`, `prophet`, `tbb`).*

**Step 3: Install C++ core for AI Prophet (MANDATORY ON WINDOWS)**
AI Prophet requires a C++ compiler for computation. Ensure you are inside the `(venv)` and run the following command:
```bash
python -c "import cmdstanpy; cmdstanpy.install_cmdstan(compiler=True)"
```
*(This process takes about 2-5 minutes. If your Windows does not have the Visual C++ library, please download and install [VC Redist x64](https://aka.ms/vs/17/release/vc_redist.x64.exe) then restart your Terminal).*

---

## 🚀 Running the Server

Start the server using the command:
```bash
uvicorn main:app --reload
```

Automatic API documentation (Swagger UI) is available at:
👉 **http://127.0.0.1:8000/docs**

---

## 📖 Main Endpoints

### 🤖 AI Prediction
```txt
GET   /api/predict-spending
```

### 🔐 Authentication & Users
```txt
POST  /register
POST  /login
POST  /token
GET   /me
```

### 🏷️ Categories
```txt
POST  /categories
GET   /categories
```

### 💳 Transactions
```txt
POST   /transactions
GET    /transactions
GET    /transactions/summary
DELETE /transactions/{transaction_id}
```

### 📊 Predictions & Warnings (Database Records)
```txt
POST  /predictions
GET   /predictions

POST  /warnings
GET   /warnings
PATCH /warnings/{warning_id}/read
```

### ⚙️ Internal Integrations
```txt
POST  /integrations/users/{user_id}/predictions
POST  /integrations/users/{user_id}/warnings
```

---

## 🔑 Authentication Guide

For APIs requiring login, use the `access_token` returned from the `/login` API and attach it to the Header:
```txt
Authorization: Bearer <token>
```

For internal services wanting to write AI data into the system:
```txt
X-API-Key: <INTERNAL_API_KEY>
```

---


