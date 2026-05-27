# Migration Copilot - Frontend

React-based UI for the Migration Copilot POC, built with IBM Carbon Design System.

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **IBM Carbon Design System** - UI components and design language
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **SCSS** - Styling with Carbon themes

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`
- Redis and Qdrant containers running (for backend)

## Installation

```bash
# Install dependencies
npm install
```

## Development

```bash
# Start development server
npm run dev

# The app will be available at http://localhost:3000
```

The dev server includes:
- Hot module replacement (HMR)
- Proxy to backend API (`/api` and `/mcp` routes)
- Fast refresh for React components

## Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── AppHeader.jsx    # Main navigation header
│   ├── pages/               # Page components
│   │   ├── Dashboard.jsx    # Main dashboard
│   │   ├── DocumentUpload.jsx    # File upload interface
│   │   ├── WorkflowExecution.jsx # Workflow orchestration
│   │   └── ExtractedFacts.jsx    # Facts viewer
│   ├── services/            # API service layer
│   │   └── api.js           # Backend API client
│   ├── App.jsx              # Root component with routing
│   ├── App.scss             # Global styles
│   ├── main.jsx             # Application entry point
│   └── index.scss           # Carbon theme imports
├── index.html               # HTML template
├── vite.config.js           # Vite configuration
└── package.json             # Dependencies and scripts
```

## Features

### 1. Dashboard
- System health status
- Quick access to main features
- MCP Gateway connection status

### 2. Document Upload
- Multi-file upload support
- Supported formats: PDF, DOCX, TXT, MD, XML, Properties, Excel
- Real-time upload progress
- Detailed upload results with:
  - Document ID
  - Parser used
  - Chunks created
  - Storage location

### 3. Workflow Execution
- Start new workflows
- Execute workflow steps
- Visual progress indicator
- Real-time state updates
- Expandable state details
- View extracted facts and questions

### 4. Extracted Facts Viewer
- Tabbed interface for fact categories:
  - Technical Stack
  - Dependencies
  - Runtime Configuration
  - Deployment Strategy
  - Architectural Decisions
  - Security & Compliance
  - Risks
- Data table with confidence scores
- Source tracking

## API Integration

The frontend communicates with the backend through these endpoints:

### Document APIs
- `POST /api/documents/upload` - Upload documents
- `POST /api/documents/search` - Semantic search
- `GET /api/documents/list/{project_id}` - List documents
- `DELETE /api/documents/{document_id}` - Delete document

### Workflow APIs
- `POST /api/orchestration/start` - Start workflow
- `POST /api/orchestration/execute` - Execute workflow
- `GET /api/orchestration/state/{project_id}` - Get state
- `POST /api/orchestration/resume` - Resume workflow

### MCP APIs
- `GET /mcp/health` - Health check
- `POST /mcp/retrieve` - Retrieve context

## Testing the Application

### End-to-End Testing Flow

1. **Start Backend Services**
   ```bash
   cd backend
   # Start Redis and Qdrant
   podman-compose up -d
   
   # Start FastAPI
   python -m uvicorn app.main:app --reload
   ```

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Test Document Upload**
   - Navigate to "Upload Documents"
   - Enter project ID: `test-project`
   - Select test files (PDF, DOCX, TXT, etc.)
   - Click "Upload Files"
   - Verify upload results show:
     - Success status
     - Document ID
     - Parser used
     - Chunks created

4. **Test Workflow Execution**
   - Navigate to "Start Workflow" from dashboard
   - Or go directly to `/workflow/test-project`
   - Click "Start Workflow" to initialize
   - Click "Execute Next Step" to run workflow
   - Watch progress indicator advance
   - Expand accordions to view:
     - Workflow state
     - Context pack
     - Extracted facts
     - Questionnaire gaps

5. **View Extracted Facts**
   - Navigate to "View Results" from dashboard
   - Or go to `/facts/test-project`
   - Browse tabs for different fact categories
   - Verify facts are displayed with:
     - Name
     - Value
     - Confidence score
     - Source reference

### Sample Test Files

Create test files to upload:

**test-config.properties**
```properties
app.name=MyApplication
app.version=1.0.0
server.port=8080
database.url=jdbc:postgresql://localhost:5432/mydb
```

**test-readme.md**
```markdown
# My Application

Java Spring Boot application with PostgreSQL database.

## Tech Stack
- Java 11
- Spring Boot 2.7
- PostgreSQL 13
- Maven 3.8
```

**test-pom.xml**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <groupId>com.example</groupId>
    <artifactId>my-app</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>2.7.0</version>
        </dependency>
    </dependencies>
</project>
```

## Troubleshooting

### Backend Connection Issues
- Verify backend is running on `http://localhost:8000`
- Check browser console for CORS errors
- Verify proxy configuration in `vite.config.js`

### Upload Failures
- Check file size (max 50MB)
- Verify file format is supported
- Check backend logs for parser errors
- Ensure Qdrant is running

### Workflow Execution Issues
- Verify Redis is running (state storage)
- Check backend logs for agent errors
- Ensure OpenAI/Gemini API keys are configured
- Verify MCP Gateway is accessible

### Styling Issues
- Clear browser cache
- Verify Carbon CSS is loading
- Check for SCSS compilation errors

## Environment Variables

Create `.env` file in frontend directory:

```env
VITE_API_URL=http://localhost:8000
```

## Carbon Design System

This app uses IBM Carbon Design System v11 with the g100 (dark) theme.

Key components used:
- Header & Navigation
- Buttons & Forms
- Tiles & Cards
- Data Tables
- Progress Indicators
- Accordions
- Notifications
- Loading states

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance

- Code splitting with React.lazy (future enhancement)
- Optimized Carbon imports
- Vite's fast HMR
- Production build with minification

## Future Enhancements

- [ ] Real-time workflow updates via WebSocket
- [ ] Advanced search and filtering
- [ ] Export functionality (PDF, JSON)
- [ ] User authentication
- [ ] Project management
- [ ] Collaborative review features
- [ ] LangSmith trace viewer integration
- [ ] Dark/light theme toggle
- [ ] Responsive mobile layout

## License

Internal POC - Not for distribution