# Contributing to Local AI Agent

Thank you for your interest in contributing to the Local AI Agent project! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect privacy and security principles of the project

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature/fix
4. Make your changes following the guidelines below
5. Test your changes thoroughly
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running
- Git

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/MeshkatShB/Agentic-AI.git
cd local-ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Set up environment
cp env.example .env
# Edit .env with your configuration

# Initialize database
python backend/init_db.py

# Run tests
pytest tests/
```

## Project Structure

```
local-ai-agent/
├── backend/           # FastAPI backend
│   ├── agent/        # ReAct agent implementation
│   ├── api/          # API endpoints
│   ├── auth/         # Authentication
│   ├── llm/          # LLM client & adapters
│   ├── models/       # Database models
│   ├── storage/      # Vector storage
│   └── tools/        # Tool implementations
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── stores/
│   └── public/
└── tests/            # Test suite
```

## Contribution Guidelines

### Code Style

#### Python (Backend)

- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use Black for formatting: `black backend/`
- Use flake8 for linting: `flake8 backend/`

#### JavaScript/React (Frontend)

- Use ES6+ features
- Functional components with hooks
- Props validation with PropTypes or TypeScript
- Consistent naming: PascalCase for components, camelCase for functions
- Format with Prettier

### Adding New Features

#### Adding a New Tool

1. Create tool implementation in `backend/tools/implementations/`
2. Inherit from `BaseTool`
3. Define required permissions
4. Add tests in `tests/tools/`
5. Update documentation

Example:

```python
class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_new_tool"

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.SAFE

    async def execute(self, **kwargs) -> ToolResult:
        # Implementation
        pass
```

#### Adding a New Model Adapter

1. Create adapter in `backend/llm/model_adapter.py`
2. Inherit from `ModelAdapter`
3. Implement required methods
4. Register in `ModelAdapterFactory`

### Testing

#### Backend Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=backend tests/
```

#### Frontend Tests

```bash
cd frontend
npm test
```

#### Testing Guidelines

- Write tests for new features
- Maintain > 80% code coverage
- Test edge cases and error conditions
- Use mocks for external services

### Security Considerations

- **No telemetry**: Never add tracking or analytics
- **Local-first**: All processing must be local by default
- **Permission gates**: Tools must require explicit user permission
- **Input validation**: Validate and sanitize all user inputs
- **Path restrictions**: Respect file access boundaries
- **Secret management**: Never commit secrets or API keys

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions/classes
- Include usage examples for new features
- Update API documentation for endpoint changes

### Commit Messages

Follow conventional commits format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:

```
feat(tools): add PDF parsing tool
fix(auth): resolve token expiration issue
docs(readme): update installation instructions
```

## Pull Request Process

1. **Create PR**: Use a descriptive title and fill out the PR template
2. **Description**: Clearly describe what changes you made and why
3. **Testing**: Confirm all tests pass
4. **Screenshots**: Include screenshots for UI changes
5. **Review**: Address review feedback promptly
6. **Squash**: Squash commits before merging if requested

## Reporting Issues

### Bug Reports

Include:

- Environment details (OS, Python version, Node version)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/logs
- Screenshots if applicable

### Feature Requests

Include:

- Use case description
- Proposed solution
- Alternative solutions considered
- Impact on existing features

## Community

- **Discussions**: Use GitHub Discussions for questions and ideas
- **Issues**: Report bugs and request features via GitHub Issues
- **Security**: Report security issues privately to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue or discussion if you have questions about contributing!
