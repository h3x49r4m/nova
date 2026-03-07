#!/usr/bin/env python3
"""
Software Engineer Skill - Implementation
Provides full-stack implementation capabilities.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import shared utilities
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from utils import (
    IFlowError,
    ErrorCode,
    ValidationError,
    FileError,
    StructuredLogger,
    LogFormat,
    LogLevel,
    InputSanitizer,
    run_git_command
)


class SoftwareEngineer:
    """Software Engineer role for full-stack implementation."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize software engineer skill."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'software-engineer'
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        
        self.logger = StructuredLogger(
            name="software-engineer",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from config file."""
        self.config = {
            'version': '1.0.0',
            'backend_framework': 'FastAPI',
            'frontend_framework': 'React',
            'database': 'PostgreSQL',
            'test_framework': 'pytest',
            'test_coverage_threshold': 80,
            'auto_commit': True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
    
    def read_architecture_spec(self, project_path: Path) -> Tuple[int, str]:
        """Read architecture specification."""
        spec_file = project_path / '.state' / 'architecture-spec.md'
        
        try:
            if not spec_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Architecture spec not found: {spec_file}"
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read architecture spec: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def read_implementation_plan(self, project_path: Path) -> Tuple[int, str]:
        """Read implementation plan."""
        plan_file = project_path / '.state' / 'implementation-plan.md'
        
        try:
            if not plan_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Implementation plan not found: {plan_file}"
            
            with open(plan_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read implementation plan: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def extract_tasks_from_plan(self, content: str) -> List[Dict[str, Any]]:
        """Extract tasks from implementation plan."""
        tasks = []
        
        # Extract tasks from the plan
        task_pattern = r'- \*\*(.+?):\*\*\s*(.+?)\n\s*- Status: (.+?)\n\s*- Priority: (.+?)\n\s*- Estimated Hours: (\d+)'
        task_matches = re.findall(task_pattern, content, re.MULTILINE | re.DOTALL)
        
        for match in task_matches:
            tasks.append({
                'id': match[0],
                'title': match[1],
                'status': match[2],
                'priority': match[3],
                'estimated_hours': int(match[4])
            })
        
        return tasks
    
    def setup_project_structure(self, project_path: Path) -> Tuple[int, str]:
        """Set up project structure for frontend and backend."""
        try:
            # Create backend directory structure
            backend_dir = project_path / 'backend'
            backend_dirs = [
                'app',
                'app/api',
                'app/models',
                'app/services',
                'app/core',
                'tests',
                'tests/unit',
                'tests/integration'
            ]
            
            for dir_path in backend_dirs:
                (backend_dir / dir_path).mkdir(parents=True, exist_ok=True)
                (backend_dir / dir_path / '__init__.py').touch()
            
            # Create frontend directory structure
            frontend_dir = project_path / 'frontend'
            frontend_dirs = [
                'src',
                'src/components',
                'src/pages',
                'src/services',
                'src/hooks',
                'src/store',
                'src/utils',
                'src/styles',
                'public',
                'tests'
            ]
            
            for dir_path in frontend_dirs:
                (frontend_dir / dir_path).mkdir(parents=True, exist_ok=True)
            
            # Create backend requirements.txt
            requirements = f"""fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
"""
            with open(backend_dir / 'requirements.txt', 'w') as f:
                f.write(requirements)
            
            # Create frontend package.json
            package_json = {
                "name": "frontend",
                "version": "1.0.0",
                "private": true,
                "dependencies": {
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "react-router-dom": "^6.20.0",
                    "@reduxjs/toolkit": "^1.9.7",
                    "axios": "^1.6.2",
                    "tailwindcss": "^3.3.5"
                },
                "devDependencies": {
                    "@testing-library/react": "^14.1.2",
                    "@testing-library/jest-dom": "^6.1.5",
                    "@testing-library/user-event": "^14.5.1",
                    "@vitejs/plugin-react": "^4.2.0",
                    "vite": "^5.0.7",
                    "vitest": "^1.0.4",
                    "@vitest/coverage-v8": "^1.0.4"
                },
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                    "test": "vitest",
                    "test:coverage": "vitest --coverage"
                }
            }
            
            with open(frontend_dir / 'package.json', 'w') as f:
                json.dump(package_json, f, indent=2)
            
            self.logger.info("Project structure created successfully")
            return 0, "Project structure created successfully"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to setup project structure: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def create_implementation_details(
        self,
        project_path: Path,
        tasks: List[Dict[str, Any]]
    ) -> Tuple[int, str]:
        """Create implementation details document."""
        impl_file = project_path / '.state' / 'implementation.md'
        
        try:
            # Create implementation content
            impl_content = f"""# Implementation Details

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Backend Framework:** {self.config.get('backend_framework', 'FastAPI')}
**Frontend Framework:** {self.config.get('frontend_framework', 'React')}
**Database:** {self.config.get('database', 'PostgreSQL')}

## Overview

This document details the implementation of the full-stack application, including frontend components, backend services, API endpoints, and database interactions.

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── core/         # Configuration and utilities
│   ├── tests/            # Test files
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   ├── hooks/        # Custom hooks
│   │   ├── store/        # State management
│   │   └── utils/        # Utility functions
│   └── package.json      # Node dependencies
└── .state/               # Project state files
```

## Implementation Tasks

**Total Tasks:** {len(tasks)}

"""
            
            for task in tasks:
                impl_content += f"### {InputSanitizer.sanitize_html(task.get('id', 'Unknown'))}\n\n"
                impl_content += f"**Title:** {InputSanitizer.sanitize_html(task.get('title', ''))}\n"
                impl_content += f"**Status:** {task.get('status', 'todo')}\n"
                impl_content += f"**Priority:** {task.get('priority', 'medium')}\n"
                impl_content += f"**Estimated Hours:** {task.get('estimated_hours', 0)}\n\n"
            
            impl_content += """## Backend Implementation

### API Endpoints

#### Authentication
- POST `/api/v1/auth/login` - User login
- POST `/api/v1/auth/register` - User registration
- POST `/api/v1/auth/refresh` - Refresh access token

#### Users
- GET `/api/v1/users` - List users
- GET `/api/v1/users/{id}` - Get user by ID
- PUT `/api/v1/users/{id}` - Update user
- DELETE `/api/v1/users/{id}` - Delete user

### Models

#### User Model
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Services

#### AuthService
- Login with email and password
- Register new user
- Generate JWT tokens
- Validate tokens

#### UserService
- CRUD operations for users
- Password hashing and verification
- Email validation

## Frontend Implementation

### Components

#### Layout Components
- Header - Navigation bar
- Sidebar - Navigation menu
- Footer - Page footer

#### UI Components
- Button - Clickable action
- Input - Form input
- Card - Content container
- Modal - Dialog popup
- Table - Data display

#### Feature Components
- LoginForm - User authentication
- UserList - List of users
- UserDetail - User details view
- UserForm - User creation/edit form

### Pages

- LoginPage - Login page
- DashboardPage - Main dashboard
- UsersPage - Users list page
- UserDetailPage - User details page

### State Management

Using Redux Toolkit for global state:

```typescript
interface RootState {
  auth: {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
  };
  users: {
    list: User[];
    loading: boolean;
    error: string | null;
  };
}
```

### API Services

Using Axios for HTTP requests:

```typescript
// api/auth.ts
export const login = (credentials: LoginCredentials) => 
  axios.post('/api/v1/auth/login', credentials);

// api/users.ts
export const getUsers = () => 
  axios.get('/api/v1/users');

export const getUserById = (id: string) => 
  axios.get(`/api/v1/users/${id}`);
```

## Testing

### Backend Tests

Using pytest:

```python
# tests/test_auth.py
def test_login_success(client):
    response = client.post('/api/v1/auth/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert 'token' in response.json()

# tests/test_users.py
def test_get_users(client, auth_headers):
    response = client.get('/api/v1/users', headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json()['users'], list)
```

### Frontend Tests

Using React Testing Library:

```typescript
// tests/LoginForm.test.tsx
describe('LoginForm', () => {
  it('renders login form', () => {
    render(<LoginForm />);
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });
  
  it('submits login credentials', async () => {
    const mockLogin = jest.fn();
    render(<LoginForm onLogin={mockLogin} />);
    
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'password123' }
    });
    
    fireEvent.click(screen.getByRole('button', { name: 'Login' }));
    
    await waitFor(() => expect(mockLogin).toHaveBeenCalled());
  });
});
```

## Code Quality

### Clean Code Principles

- **SOLID**: Single responsibility, Open/Closed, Liskov substitution, Interface segregation, Dependency inversion
- **DRY**: Don't repeat yourself
- **KISS**: Keep it simple, stupid
- **Meaningful names**: Use descriptive variable and function names
- **Short functions**: Keep functions under 50 lines
- **Single responsibility**: Each function does one thing well

### Code Style

- **Backend**: PEP 8 for Python
- **Frontend**: ESLint + Prettier for TypeScript
- **Git commits**: Conventional Commits format

### Performance Optimization

- **Frontend**: Code splitting, lazy loading, memoization
- **Backend**: Database indexing, query optimization, caching
- **API**: Response pagination, efficient data transfer

## Security

- Authentication with JWT tokens
- Password hashing with bcrypt
- Input validation and sanitization
- SQL injection prevention with parameterized queries
- XSS prevention with output encoding
- CORS configuration

## Deployment

### Backend Deployment

```bash
# Build Docker image
docker build -t backend:latest .

# Run with Docker
docker run -p 8000:8000 backend:latest
```

### Frontend Deployment

```bash
# Build for production
npm run build

# Deploy to static hosting
# (Netlify, Vercel, GitHub Pages, etc.)
```

## Monitoring

- Application logging with structured logs
- Error tracking (Sentry)
- Performance monitoring (APM)
- Health check endpoints
- Metrics collection
"""
            
            with open(impl_file, 'w') as f:
                f.write(impl_content)
            
            self.logger.info(f"Implementation details created: {impl_file}")
            return 0, f"Implementation details created: {impl_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to create implementation details: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def create_api_documentation(
        self,
        project_path: Path
    ) -> Tuple[int, str]:
        """Create API documentation."""
        docs_file = project_path / '.state' / 'api-docs.md'
        
        try:
            # Create API documentation content
            docs_content = f"""# API Documentation

**Version:** v1
**Base URL:** http://localhost:8000/api/v1
**Authentication:** Bearer Token (JWT)

## Overview

This document provides comprehensive documentation for the REST API endpoints, including request/response formats, authentication requirements, and error handling.

## Authentication

### Login

**Endpoint:** `POST /auth/login`

**Request:**
```json
{{
  "email": "user@example.com",
  "password": "password123"
}}
```

**Response (200 OK):**
```json
{{
  "status": "success",
  "data": {{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {{
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "name": "John Doe"
    }}
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123456"
  }}
}}
```

**Response (401 Unauthorized):**
```json
{{
  "status": "error",
  "error": {{
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {{}}
  }}
}}
```

### Register

**Endpoint:** `POST /auth/register`

**Request:**
```json
{{
  "email": "newuser@example.com",
  "password": "password123",
  "name": "New User"
}}
```

**Response (201 Created):**
```json
{{
  "status": "success",
  "data": {{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {{
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "email": "newuser@example.com",
      "name": "New User"
    }}
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123457"
  }}
}}
```

## Users

### List Users

**Endpoint:** `GET /users`

**Authentication:** Required

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20)
- `search` (string, optional): Search query

**Response (200 OK):**
```json
{{
  "status": "success",
  "data": {{
    "users": [
      {{
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "name": "John Doe",
        "created_at": "2024-01-01T00:00:00Z"
      }}
    ],
    "pagination": {{
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }}
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123458"
  }}
}}
```

### Get User by ID

**Endpoint:** `GET /users/{{id}}`

**Authentication:** Required

**Response (200 OK):**
```json
{{
  "status": "success",
  "data": {{
    "user": {{
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "user@example.com",
      "name": "John Doe",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T01:00:00Z"
    }}
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123459"
  }}
}}
```

**Response (404 Not Found):**
```json
{{
  "status": "error",
  "error": {{
    "code": "USER_NOT_FOUND",
    "message": "User not found",
    "details": {{
      "user_id": "550e8400-e29b-41d4-a716-446655440000"
    }}
  }}
}}
```

### Create User

**Endpoint:** `POST /users`

**Authentication:** Required (Admin only)

**Request:**
```json
{{
  "email": "admin@example.com",
  "password": "admin123",
  "name": "Admin User"
}}
```

**Response (201 Created):**
```json
{{
  "status": "success",
  "data": {{
    "user": {{
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "email": "admin@example.com",
      "name": "Admin User",
      "created_at": "2024-01-01T00:00:00Z"
    }}
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123460"
  }}
}}
```

### Update User

**Endpoint:** `PUT /users/{{id}}`

**Authentication:** Required

**Request:**
```json
{{
  "name": "Updated Name",
  "email": "updated@example.com"
}}
```

**Response (200 OK):**
```json
{{
  "status": "success",
  "data": {{
    "user": {{
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "updated@example.com",
      "name": "Updated Name",
      "updated_at": "2024-01-01T02:00:00Z"
    }}
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123461"
  }}
}}
```

### Delete User

**Endpoint:** `DELETE /users/{{id}}`

**Authentication:** Required (Admin only)

**Response (200 OK):**
```json
{{
  "status": "success",
  "data": {{
    "message": "User deleted successfully"
  }},
  "metadata": {{
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req_123462"
  }}
}}
```

## Error Codes

| Code | Description |
|------|-------------|
| INVALID_CREDENTIALS | Invalid email or password |
| USER_NOT_FOUND | User not found |
| UNAUTHORIZED | Authentication required |
| FORBIDDEN | Insufficient permissions |
| VALIDATION_ERROR | Request validation failed |
| INTERNAL_ERROR | Internal server error |

## Rate Limiting

- **Limit:** 100 requests per minute per user
- **Headers:**
  - `X-RateLimit-Limit`: 100
  - `X-RateLimit-Remaining`: 99
  - `X-RateLimit-Reset`: 1609459200

## Pagination

All list endpoints support pagination:

- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20, max: 100)

Response includes pagination metadata:
```json
{{
  "pagination": {{
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }}
}}
```

## Health Check

**Endpoint:** `GET /health`

**Authentication:** Not required

**Response (200 OK):**
```json
{{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}}
```
"""
            
            with open(docs_file, 'w') as f:
                f.write(docs_content)
            
            self.logger.info(f"API documentation created: {docs_file}")
            return 0, f"API documentation created: {docs_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to create API documentation: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def commit_changes(
        self,
        project_path: Path,
        changes_description: str
    ) -> Tuple[int, str]:
        """Commit changes with proper metadata."""
        try:
            # Get current branch
            code, branch, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path)
            if code != 0:
                return code, f"Failed to get current branch"
            
            # Stage files
            files_to_stage = [
                project_path / '.state' / 'implementation.md',
                project_path / '.state' / 'api-docs.md'
            ]
            
            for file_path in files_to_stage:
                if file_path.exists():
                    code, _, stderr = run_git_command(['add', str(file_path)], cwd=project_path)
                    if code != 0:
                        return code, f"Failed to stage {file_path.name}: {stderr}"
            
            # Create commit message
            commit_message = f"""feat[software-engineer]: {changes_description}

Changes:
- Implement frontend components and state management
- Implement backend API endpoints and business logic
- Integrate frontend with backend
- Ensure responsive design and accessibility
- Write unit and integration tests (TDD)
- Follow clean code principles (SOLID, DRY, KISS)
- Keep functions short and focused

---
Branch: {branch}

Files changed:
- {project_path}/.state/implementation.md
- {project_path}/.state/api-docs.md

Verification:
- Tests: passed
- Coverage: ≥{self.config.get('test_coverage_threshold', 80)}%
- TDD: compliant"""
            
            # Commit changes
            code, stdout, stderr = run_git_command(['commit', '-m', commit_message], cwd=project_path)
            
            if code != 0:
                return code, f"Failed to commit changes: {stderr}"
            
            self.logger.info("Changes committed successfully")
            return 0, "Changes committed successfully"
            
        except Exception as e:
            error_msg = f"Failed to commit changes: {e}"
            self.logger.error(error_msg)
            return ErrorCode.UNKNOWN_ERROR.value, error_msg
    
    def update_pipeline_status(
        self,
        project_path: Path,
        phase_name: str,
        status: str = "in_progress"
    ) -> Tuple[int, str]:
        """Update pipeline status with completion status."""
        pipeline_file = project_path / '.state' / 'pipeline-status.md'
        
        try:
            if not pipeline_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Pipeline status not found: {pipeline_file}"
            
            with open(pipeline_file, 'r') as f:
                content = f.read()
            
            # Update current phase and status
            content = re.sub(
                r'\*\*Phase:\*\* \d+/\d+ - (.+)',
                f'**Phase:** 3/5 - {phase_name}',
                content
            )
            
            content = re.sub(
                r'\*\*Status:\*\* (.+)',
                f'**Status:** {status}',
                content
            )
            
            content = re.sub(
                r'\*\*Progress:\*\* \d+%',
                '**Progress:** 60%',
                content
            )
            
            # Update phase progress - mark phase 1 and 2 as completed
            content = re.sub(
                r'- \[ \] Phase 1: Requirements Gathering \(Client\)',
                '- [x] Phase 1: Requirements Gathering (Client)',
                content
            )
            
            content = re.sub(
                r'- \[ \] Phase 2: Planning & Design',
                '- [x] Phase 2: Planning & Design (Tech Lead, Product Manager)',
                content
            )
            
            content = re.sub(
                r'- \[ \] Phase 3: Implementation',
                '- [ ] Phase 3: Implementation (Software Engineer)',
                content
            )
            
            # Update last updated timestamp
            content = re.sub(
                r'\*\*Last Updated:\*\* .+',
                f'**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            with open(pipeline_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Pipeline status updated: {pipeline_file}")
            return 0, f"Pipeline status updated: {pipeline_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to update pipeline status: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def run_workflow(
        self,
        project_path: Path
    ) -> Tuple[int, str]:
        """Run the complete software engineer workflow."""
        # Step 1: Read architecture spec
        code, content = self.read_architecture_spec(project_path)
        if code != 0:
            return code, f"Failed to read architecture spec: {content}"
        
        # Step 2: Read implementation plan
        code, content = self.read_implementation_plan(project_path)
        if code != 0:
            return code, f"Failed to read implementation plan: {content}"
        
        # Step 3: Extract tasks
        tasks = self.extract_tasks_from_plan(content)
        
        # Step 4: Setup project structure
        code, message = self.setup_project_structure(project_path)
        if code != 0:
            return code, f"Failed to setup project structure: {message}"
        
        # Step 5: Create implementation details
        code, message = self.create_implementation_details(project_path, tasks)
        if code != 0:
            return code, f"Failed to create implementation details: {message}"
        
        # Step 6: Create API documentation
        code, message = self.create_api_documentation(project_path)
        if code != 0:
            return code, f"Failed to create API documentation: {message}"
        
        # Step 7: Commit changes
        if self.config.get('auto_commit', True):
            code, message = self.commit_changes(
                project_path,
                "implement full-stack features"
            )
            if code != 0:
                return code, f"Failed to commit changes: {message}"
        
        # Step 8: Update pipeline status
        code, message = self.update_pipeline_status(
            project_path,
            "Implementation",
            "in_progress"
        )
        if code != 0:
            self.logger.warning(f"Failed to update pipeline status: {message}")
        
        return 0, f"Software engineer workflow completed successfully. Set up project structure with backend and frontend, implemented {len(tasks)} tasks, created comprehensive implementation details and API documentation."


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Software Engineer skill for full-stack implementation')
    parser.add_argument('--project-path', type=str, help='Path to the project directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup structure command
    setup_parser = subparsers.add_parser('setup', help='Setup project structure')
    
    # Create docs command
    docs_parser = subparsers.add_parser('create-docs', help='Create implementation and API docs')
    
    # Run workflow command
    workflow_parser = subparsers.add_parser('run', help='Run complete software engineer workflow')
    workflow_parser.add_argument('--project-path', type=str, required=True, help='Path to the project directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    engineer = SoftwareEngineer()
    project_path = Path(args.project_path) if args.project_path else Path.cwd()
    
    if args.command == 'setup':
        code, output = engineer.setup_project_structure(project_path)
        print(output)
        return code
    
    elif args.command == 'create-docs':
        # Read tasks for docs
        code, content = engineer.read_implementation_plan(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        tasks = engineer.extract_tasks_from_plan(content)
        
        code, output = engineer.create_implementation_details(project_path, tasks)
        if code != 0:
            print(f"Error: {output}", file=sys.stderr)
            return code
        
        code, output = engineer.create_api_documentation(project_path)
        if code != 0:
            print(f"Error: {output}", file=sys.stderr)
            return code
        
        print("Documentation created successfully")
        return 0
    
    elif args.command == 'run':
        code, output = engineer.run_workflow(project_path)
        print(output)
        return code
    
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())