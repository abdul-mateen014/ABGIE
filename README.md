# ABGIE - AI-Powered Business Growth Intelligence Engine

ABGIE is an intelligent, multi-agent system designed to analyze business scenarios, financial data, and market conditions to provide strategic insights, growth recommendations, and automated reports. It combines LangChain orchestration with a React-based frontend to deliver a seamless user experience.

## 📋 Features

### 🏗️ Core Architecture
- **Multi-Agent System**: Composed of **14 specialized agents** working together to achieve complex goals.
- **Orchestration**: Managed by a central `OrchestratorAgent` that coordinates tasks and routes results.
- **LangChain Integration**: Built on the LangChain framework for robust agent management and tool usage.
- **Service Layer**: Modular `services/` directory for business logic, database interactions, and file handling.

### 🚀 Key Capabilities
- **Business Analysis**: Deep dives into business models, strengths, weaknesses, opportunities, and threats (SWOT).
- **Financial Modeling**: Automated calculation of ROI, Payback Period, NPV, and IRR.
- **Data Processing**: Extraction of text from documents (PDF, TXT) and structured data generation.
- **Report Generation**: Creation of high-quality, formatted business reports and presentations.
- **Strategic Insights**: Identification of growth strategies, market positioning, and operational improvements.

### 🖥️ User Interface
- **Modern Web Interface**: Built with React and TypeScript.
- **Interactive Forms**: Clean, guided data entry for various business scenarios.
- **Dynamic Results Display**: Markdown and structured data rendering for easy consumption.
- **Multi-Scenario Support**: Ability to run and compare multiple analyses side-by-side.

## 📂 Project Structure

```
abgie/
├── app/                       # Core Application Logic (LangChain/FastAPI)
│   ├── agents/                # All 14 specialized agents
│   ├── orchestrator/          # Orchestration logic and state management
│   ├── services/              # Business logic, database, utilities
│   ├── utils/                 # Helper functions and configurations
│   └── api/                   # FastAPI endpoint definitions
│
├── frontend/                  # React Web Application
│   ├── src/
│   │   ├── pages/             # Pages (ReportForm, ReportResult)
│   │   ├── components/        # UI Components
│   │   ├── api/               # API client
│   │   └── store/             # State management (Zustand)
│   └── public/
│
├── tests/                     # Automated tests
├── README.md                  # This file
├── requirements.txt           # Python dependencies
└── Dockerfile                 # Containerization (if applicable)
```

## ⚙️ Agents Overview

The system features 14 specialized agents, each with a specific role:

| Agent Name | Role |
| :--- | :--- |
| **OrchestratorAgent** | Main coordinator, manages workflow execution |
| **ContentExtractorAgent** | Extracts and structures text from documents |
| **FinancialAnalysisAgent** | Calculates ROI, Payback, NPV, IRR |
| **SWOTAnalysisAgent** | Conducts Strengths, Weaknesses, Opportunities, Threats analysis |
| **GrowthStrategyAgent** | Identifies business growth opportunities |
| **MarketPositioningAgent** | Analyzes market fit and competitive positioning |
| **ProductManagerAgent** | Strategic product and feature planning |
| **SalesProcessAgent** | Designs sales funnels and strategies |
| **MarketingAgent** | Develops marketing and outreach campaigns |
| **ContentCreatorAgent** | Writes and formats reports and content |
| **PresentationAgent** | Creates slides and presentation materials |
| **DataProcessorAgent** | Handles data cleaning and transformation |
| **PersonaGeneratorAgent** | Creates detailed user personas |
| **CompetitorAnalysisAgent** | Researches and analyzes competitors |

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+ (for frontend)

### Installation

**1. Backend Setup**
```bash
cd app
pip install -r requirements.txt
```

**2. Frontend Setup**
```bash
cd frontend
npm install
```

### Development

**Run Backend**
```bash
cd app
uvicorn main:app --reload
```

**Run Frontend**
```bash
cd frontend
npm run dev
```

## 📋 Usage

### Running Analysis
1. Open the **Frontend** at `http://localhost:5173`.
2. Fill in the **Business Scenario Form** with relevant details.
3. Submit the form to start the analysis.
4. The **Orchestrator** will activate the necessary agents to process your request.
5. View the generated **Report** with detailed insights and visualizations.

### API Endpoints
- `POST /api/analyze`: Start a new business analysis.
- `GET /api/reports`: List all generated reports.
- `GET /api/reports/{id}`: Retrieve a specific report.
- `POST /api/content/extract`: Extract text from documents.

## 🧪 Testing

Run the test suite to ensure system stability:
```bash
cd tests
python -m unittest discover
```

## 🤝 Contributing

1. Create a feature branch (`git checkout -b feature/AmazingFeature`).
2. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
3. Push to the branch (`git push origin feature/AmazingFeature`).
4. Open a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
