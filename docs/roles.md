# Development Team Roles

This document defines the roles and responsibilities for the development team.

## Stakeholder Layer

### Client
- Requirements provider
- Acceptance criteria definition
- Product feedback and validation
- Business domain expertise

## Product & Planning

### Product Manager
- **Core Responsibilities:**
  - Feature roadmap planning
  - Feature prioritization and backlog management
  - User story creation and refinement
  - Market research and competitive analysis
  - User needs gathering and validation
  - Product vision and strategy

### Project Manager
- **Core Responsibilities:**
  - Sprint planning and execution
  - Timeline and milestone tracking
  - Resource allocation and team coordination
  - Risk management and mitigation
  - Stakeholder communication
  - Progress reporting

## Design

### UI/UX Designer
- **Core Responsibilities:**
  - Wireframe creation
  - Interactive prototypes
  - Visual design system
  - User flow design
  - Accessibility compliance (WCAG)
  - Design handoff to engineering
- **Skills:**
  - Figma/Sketch/Adobe XD
  - Design systems (Material, Apple HIG)
  - Responsive design principles
  - User research methods

## Technical Leadership

### Tech Lead
- **Core Responsibilities:**
  - System architecture decisions
  - Code standards and conventions
  - Technical strategy and vision
  - Code review and mentorship
  - Technical debt management
  - Technology stack selection
- **Skills:**
  - System design patterns
  - Performance optimization
  - Security best practices
  - Team leadership

## Engineering

### Software Engineer
- **Core Responsibilities:**
  - Full-stack implementation
  - UI component implementation
  - Client-side state management
  - API design and implementation
  - Database schema design and optimization
  - Authentication and authorization systems
  - Server-side business logic
  - Responsive layout implementation
  - Performance optimization
  - Cross-browser compatibility
- **Skills:**
  - Frontend: React/Vue/Angular expertise
  - Frontend: Component architecture
  - Frontend: State management (Redux, Vuex, Context API)
  - Frontend: CSS frameworks (Tailwind, Bootstrap, CSS Modules)
  - Frontend: Responsive design
  - Frontend: Accessibility (ARIA, semantic HTML)
  - Frontend: Performance optimization (lazy loading, code splitting)
  - Frontend: Build tools (Webpack, Vite, esbuild)
  - Backend: API design (REST, GraphQL, gRPC)
  - Backend: Database systems (PostgreSQL, MySQL, MongoDB, Redis)
  - Backend: Server frameworks (Express, FastAPI, Django, Spring Boot)
  - Backend: Authentication (OAuth2, JWT, SAML)
  - Backend: Caching (Redis, Memcached)
  - Backend: Message queues (RabbitMQ, Kafka)
  - Backend: Containerization (Docker, Kubernetes)

## Quality & Operations

### Testing Engineer
- **Core Responsibilities:**
  - Unit and integration test development
  - Test framework setup and maintenance
  - Test automation implementation
  - TDD (Test-Driven Development) practices
  - Test coverage analysis
- **Skills:**
  - Testing frameworks (Jest, Pytest, JUnit)
  - Mocking and stubbing
  - Test-driven development
  - CI/CD test integration
  - Performance testing

### QA Engineer
- **Core Responsibilities:**
  - Manual testing execution
  - Test case creation and maintenance
  - Bug tracking and validation
  - User acceptance testing (UAT)
  - Release readiness verification
  - Test planning and strategy
- **Skills:**
  - Test case design
  - Bug tracking tools (Jira, Bugzilla)
  - Exploratory testing
  - Regression testing
  - Cross-platform testing

### DevOps Engineer
- **Core Responsibilities:**
  - CI/CD pipeline design and implementation
  - Container orchestration
  - Cloud infrastructure management
  - Monitoring and alerting setup
  - Deployment automation
  - Infrastructure as Code
- **Skills:**
  - CI/CD tools (GitHub Actions, GitLab CI, Jenkins)
  - Containerization (Docker, Kubernetes)
  - Cloud platforms (AWS, GCP, Azure)
  - Infrastructure as Code (Terraform, CloudFormation)
  - Monitoring (Prometheus, Grafana, ELK Stack)
  - Configuration management (Ansible, Chef)

### Security Engineer
- **Core Responsibilities:**
  - Code security reviews
  - Vulnerability scanning and analysis
  - Security best practices enforcement
  - Penetration testing coordination
  - Security incident response
  - Compliance and auditing
- **Skills:**
  - Security frameworks (OWASP, NIST)
  - Static analysis tools (SonarQube, Snyk)
  - Penetration testing tools
  - Encryption and secure protocols
  - Identity and access management

### Documentation Specialist
- **Core Responsibilities:**
  - API documentation
  - User guides and tutorials
  - Technical documentation
  - Architecture documentation
  - Onboarding materials
- **Skills:**
  - Technical writing
  - Documentation tools (Swagger/OpenAPI, MkDocs, Docusaurus)
  - API documentation standards
  - Diagramming tools (Mermaid, Draw.io)
  - Version control for documentation

## Team Collaboration

### Workflow Integration
- **Product Manager** → Defines features → **UI/UX Designer** creates designs → **Tech Lead** reviews architecture → **Software Engineer** implements → **Testing Engineer** writes automated tests → **QA Engineer** validates → **DevOps Engineer** deploys → **Security Engineer** validates security → **Documentation Specialist** documents

### Cross-Functional Handoffs
- **Design → Engineering**: Design handoff with component specifications
- **Engineering → Testing**: Feature delivery with test requirements
- **Testing → QA**: Automated test results and manual testing scope
- **QA → DevOps**: Release package with deployment checklist
- **All → Documentation**: Continuous documentation updates

## State Contracts

Each role has defined READ and WRITE contracts for state documents in `.shared-state/`.

### Client
- **READ:** None (provides initial requirements)
- **WRITE:** `project-spec.md`
- **Outputs:** Feature requests, requirements, acceptance criteria

### Product Manager
- **READ:** `project-spec.md`, `pipeline-status.md`
- **WRITE:** `project-spec.md`, `implementation-plan.md`
- **Outputs:** Feature priorities, user stories, backlog

### Project Manager
- **READ:** `project-spec.md`, `implementation-plan.md`, `pipeline-status.md`
- **WRITE:** `implementation-plan.md`, `pipeline-status.md`
- **Outputs:** Sprint plans, timelines, resource allocation

### UI/UX Designer
- **READ:** `project-spec.md`, `implementation-plan.md`
- **WRITE:** `design-spec.md`
- **Outputs:** Wireframes, prototypes, visual designs

### Tech Lead
- **READ:** `project-spec.md`, `design-spec.md`, `implementation-plan.md`
- **WRITE:** `architecture-spec.md`, `implementation.md`
- **Outputs:** System architecture, tech stack, code standards

### Software Engineer
- **READ:** `architecture-spec.md`, `design-spec.md`, `implementation.md`
- **WRITE:** `implementation.md`, `api-docs.md`
- **Outputs:** Source code, API implementations, database schemas

### Testing Engineer
- **READ:** `implementation.md`, `architecture-spec.md`
- **WRITE:** `test-plan.md`, `test-results.md`
- **Outputs:** Automated tests, test coverage reports

### QA Engineer
- **READ:** `test-plan.md`, `test-results.md`, `implementation.md`
- **WRITE:** `quality-report.md`, `test-results.md`
- **Outputs:** Bug reports, validation results, UAT results

### DevOps Engineer
- **READ:** `implementation.md`, `architecture-spec.md`, `pipeline-status.md`
- **WRITE:** `deployment-status.md`
- **Outputs:** CI/CD pipelines, infrastructure, deployments

### Security Engineer
- **READ:** `implementation.md`, `architecture-spec.md`
- **WRITE:** `security-report.md`
- **Outputs:** Security scans, vulnerability reports, security recommendations

### Documentation Specialist
- **READ:** All state documents
- **WRITE:** `user-guide.md`, `api-docs.md`, `changelog.md`
- **Outputs:** Documentation, guides, tutorials

## Role-Specific Workflows

### New Feature Workflow

1. **Product Manager**: Define feature in `project-spec.md`
2. **UI/UX Designer**: Create designs in `design-spec.md`
3. **Tech Lead**: Review and update `architecture-spec.md`
4. **Software Engineer**: Implement feature, update `implementation.md`
5. **Testing Engineer**: Write tests, update `test-plan.md`
6. **QA Engineer**: Validate, update `quality-report.md`
7. **DevOps Engineer**: Deploy, update `deployment-status.md`
8. **Security Engineer**: Validate security, update `security-report.md`
9. **Documentation Specialist**: Document, update `user-guide.md`

### Bug Fix Workflow

1. **QA Engineer**: Report bug in `quality-report.md`
2. **Tech Lead**: Triage and assign, update `pipeline-status.md`
3. **Software Engineer**: Fix bug, update `implementation.md`
4. **Testing Engineer**: Verify fix, update `test-results.md`
5. **QA Engineer**: Validate fix, update `quality-report.md`
6. **DevOps Engineer**: Deploy hotfix, update `deployment-status.md`

### Code Review Workflow

1. **Software Engineer**: Submit PR with implementation
2. **Tech Lead**: Review architecture and code quality
3. **Security Engineer**: Review security implications
4. **Testing Engineer**: Review test coverage
5. **Documentation Specialist**: Review documentation updates
6. **Approval**: Merge if all reviews pass

### Deployment Workflow

1. **QA Engineer**: Complete UAT, update `quality-report.md`
2. **Security Engineer**: Final security scan, update `security-report.md`
3. **DevOps Engineer**: Prepare deployment package
4. **DevOps Engineer**: Deploy to staging, update `deployment-status.md`
5. **All Roles**: Validate staging deployment
6. **DevOps Engineer**: Deploy to production, update `deployment-status.md`
7. **Documentation Specialist**: Update `changelog.md`

## Role Dependencies

### Critical Path Dependencies
- **Software Engineer** depends on **Tech Lead** (architecture)
- **Testing Engineer** depends on **Software Engineer** (implementation)
- **QA Engineer** depends on **Testing Engineer** (tests)
- **DevOps Engineer** depends on **QA Engineer** (validation)
- **Documentation Specialist** depends on **All Roles** (information)

### Parallel Execution Opportunities
- **Testing Engineer** can write tests in parallel with **Software Engineer** implementation
- **Security Engineer** can review code in parallel with **Tech Lead** review
- **Documentation Specialist** can draft docs in parallel with development

## Communication Protocols

### Handoff Protocol
1. Initiator updates relevant state document
2. Initiator creates handoff record in `handoff-protocol.md`
3. Receiver validates handoff
4. Receiver acknowledges and updates `pipeline-status.md`

### Blocking Issues
- **Critical**: Blocks all downstream work
- **High**: Blocks immediate next role
- **Medium**: Delays but doesn't block
- **Low**: Cosmetic or documentation issue

### Escalation Path
1. **Role** → **Project Manager** → **Tech Lead** → **Product Manager** → **Client**

## Success Metrics

### Role-Specific Metrics
- **Product Manager**: Feature delivery rate, backlog health
- **Project Manager**: Sprint completion rate, timeline accuracy
- **Software Engineer**: Code quality, test coverage
- **Testing Engineer**: Test coverage, automated test pass rate
- **QA Engineer**: Bug detection rate, release readiness
- **DevOps Engineer**: Deployment success rate, uptime
- **Security Engineer**: Vulnerability count, remediation time

### Team Metrics
- Overall cycle time
- Defect escape rate
- Deployment frequency
- Mean time to recovery (MTTR)
- Customer satisfaction