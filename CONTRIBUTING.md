# Contributing to Athena

Thank you for your interest in contributing to Athena! 🏛️

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yelikour/athena-agent.git
cd athena-agent
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Run tests:
```bash
pytest tests/ -v
```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public functions
- Keep functions focused and small

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Run the test suite
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Reporting Issues

- Use the GitHub issue tracker
- Include steps to reproduce
- Include Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
